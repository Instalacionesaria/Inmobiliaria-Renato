"""Explora la estructura del Google Sheet configurado en .env.

Uso:
    uv run python scripts/explore_sheet.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permitir ejecutar el script directamente desde la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def main() -> int:
    settings = get_settings()

    if not settings.google_service_account_file:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_FILE no está en .env")
        return 1
    if not settings.sheet_id:
        print("ERROR: SHEET_ID no está en .env")
        return 1

    creds = Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    client = gspread.authorize(creds)

    try:
        sheet = client.open_by_key(settings.sheet_id)
    except gspread.exceptions.APIError as exc:
        print(f"ERROR abriendo el sheet: {exc}")
        print("Comprueba: (1) SHEET_ID correcto; (2) compartiste el sheet con la service account.")
        return 2

    print(f"📄 Spreadsheet: {sheet.title}")
    print(f"🔗 URL: {sheet.url}")
    print(f"📑 Pestañas: {len(sheet.worksheets())}\n")

    for idx, ws in enumerate(sheet.worksheets(), start=1):
        print(f"=== [{idx}] {ws.title}  ({ws.row_count}×{ws.col_count}) ===")
        try:
            block = ws.get("A1:BZ40")
        except Exception as exc:
            print(f"  (no pude leer: {exc})")
            continue

        if not block:
            print("  (pestaña vacía)")
            continue

        # Cabeceras agrupadas (row 3) y cabeceras finas (row 4)
        if len(block) >= 4:
            print("\n--- Headers (fila 4) ---")
            for col_idx, header in enumerate(block[3], start=1):
                if header:
                    print(f"  col{col_idx}: {header}")

        # Volcado de filas de datos
        print("\n--- Filas de datos (5-40) ---")
        for row_idx, row in enumerate(block[4:], start=5):
            if not any(cell.strip() for cell in row if isinstance(cell, str)):
                continue
            preview = " | ".join(str(c) for c in row[:6])  # primeras 6 columnas (id, nombre, ...)
            print(f"  row{row_idx}: {preview}")

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
