"""Cliente de Google Sheets multi-edificio.

Cada **pestaña** del spreadsheet representa un edificio. El nombre de la
pestaña se usa como el nombre del edificio (ej: "La Joya", "Torre Sol").

Cada pestaña tiene la misma estructura general:
- Fila 1-2: títulos / subtítulo
- Fila 3: cabeceras agrupadas (Servicios Básicos, Mantenimientos, etc.)
- Fila 4: cabeceras finas (Total Consumo de Agua, Administración, etc.)
- Fila 5+: datos por departamento. Columna A = número de depto.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from rapidfuzz import fuzz, process
from unidecode import unidecode

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

GROUP_ROW = 3
HEADER_ROW = 4

BUILDING_FUZZY_THRESHOLD = 70


class SheetClient:
    """Lee la planilla de cuotas. Cachea con TTL configurable."""

    def __init__(self, cache_ttl: float = 60.0) -> None:
        self._cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._cached_at: float = 0.0
        # building_title -> { depto -> { header -> value } }
        self._by_building: dict[str, dict[str, dict[str, Any]]] = {}

    def _client(self) -> gspread.Client:
        settings = get_settings()
        if not settings.sheet_id:
            raise RuntimeError("SHEET_ID no configurado")

        # En producción (EasyPanel, etc.) la service account viaja como JSON
        # en una env var. En dev local, como archivo en disco. Soportamos
        # ambos modos — JSON env var tiene prioridad si está presente.
        if settings.google_service_account_json:
            info = json.loads(settings.google_service_account_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        elif settings.google_service_account_file:
            creds = Credentials.from_service_account_file(
                settings.google_service_account_file, scopes=SCOPES
            )
        else:
            raise RuntimeError(
                "Configurá GOOGLE_SERVICE_ACCOUNT_JSON (contenido) o "
                "GOOGLE_SERVICE_ACCOUNT_FILE (path al .json)"
            )
        return gspread.authorize(creds)

    def _parse_worksheet(self, ws: gspread.Worksheet) -> dict[str, dict[str, Any]]:
        """Devuelve { depto: { header: value } } para una pestaña."""
        block = ws.get(f"A{GROUP_ROW}:BZ1000")
        if not block or len(block) < 3:
            return {}

        group_row = [h.strip() for h in block[0]]
        fine_row = [h.strip() for h in block[1]]
        max_cols = max(len(group_row), len(fine_row))
        headers: list[str] = []
        for i in range(max_cols):
            fine = fine_row[i] if i < len(fine_row) else ""
            group = group_row[i] if i < len(group_row) else ""
            headers.append(fine or group or f"col{i + 1}")

        rows: dict[str, dict[str, Any]] = {}
        for raw_row in block[2:]:
            if not raw_row or not raw_row[0].strip():
                continue
            depto = raw_row[0].strip()
            if not depto.isdigit():
                # Saltamos filas tipo "Total"
                continue
            row = list(raw_row) + [""] * (len(headers) - len(raw_row))
            rows[depto] = {headers[i]: row[i] for i in range(len(headers))}
        return rows

    def _load(self) -> None:
        client = self._client()
        settings = get_settings()
        sheet = client.open_by_key(settings.sheet_id)  # type: ignore[arg-type]

        by_building: dict[str, dict[str, dict[str, Any]]] = {}
        for ws in sheet.worksheets():
            rows = self._parse_worksheet(ws)
            if rows:
                by_building[ws.title] = rows

        self._by_building = by_building
        self._cached_at = time.monotonic()
        logger.info(
            "Sheet cargada: %d edificios (%s)",
            len(by_building),
            ", ".join(by_building.keys()),
        )

    def _ensure_fresh(self) -> None:
        with self._lock:
            if time.monotonic() - self._cached_at > self._cache_ttl:
                self._load()

    # ----- API pública --------------------------------------------------

    def list_buildings(self) -> list[str]:
        self._ensure_fresh()
        return sorted(self._by_building.keys())

    def list_deptos(self, building: str) -> list[str]:
        self._ensure_fresh()
        return sorted(self._by_building.get(building, {}).keys())

    def get_row(self, building: str, depto: str) -> dict[str, Any] | None:
        self._ensure_fresh()
        return self._by_building.get(building, {}).get(str(depto).strip())

    def find_building(self, name: str) -> str | None:
        """Resuelve el nombre dado por el cliente al título exacto de la pestaña.

        Hace fuzzy match (case-insensitive, ignora tildes) contra los nombres
        de las pestañas. Devuelve el título canónico (como aparece en la
        pestaña) o None si no hay match suficiente.
        """
        self._ensure_fresh()
        if not name:
            return None
        candidates = list(self._by_building.keys())
        if not candidates:
            return None

        normalized_input = unidecode(name).lower().strip()
        normalized_map = {unidecode(c).lower().strip(): c for c in candidates}

        result = process.extractOne(
            normalized_input,
            list(normalized_map.keys()),
            scorer=fuzz.partial_ratio,
        )
        if result is None:
            return None
        match, score, _ = result
        if score < BUILDING_FUZZY_THRESHOLD:
            return None
        return normalized_map[match]


_client: SheetClient | None = None


def get_sheet_client() -> SheetClient:
    global _client
    if _client is None:
        _client = SheetClient()
    return _client
