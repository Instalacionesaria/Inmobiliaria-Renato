from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.storage.db import CONTACTS_TABLE, get_conn


@dataclass
class Contact:
    phone: str
    contact_id: str | None
    edificio: str | None
    depto: str | None
    nombre: str | None
    nombre_sheet: str | None
    verified: bool
    paused_until: datetime | None = None

    def is_paused(self) -> bool:
        if self.paused_until is None:
            return False
        return self.paused_until > datetime.now(timezone.utc)


def normalize_phone(phone: str | None) -> str | None:
    """Normaliza un número a `+<digitos>`. Si viene sin `+`, asumimos que ya es
    el número canónico (de `raw.phone` de HighLevel) y devolvemos los dígitos."""
    if not phone:
        return None
    phone = phone.strip()
    if phone.startswith("+"):
        digits = "".join(c for c in phone[1:] if c.isdigit())
        return f"+{digits}" if digits else None
    digits = "".join(c for c in phone if c.isdigit())
    return digits or None


def get_contact(phone: str) -> Contact | None:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT phone, contact_id, edificio, depto, nombre, nombre_sheet, "
            f"verified, paused_until FROM {CONTACTS_TABLE} WHERE phone = %s",
            (phone,),
        ).fetchone()
    if row is None:
        return None
    return Contact(
        phone=row["phone"],
        contact_id=row["contact_id"],
        edificio=row["edificio"],
        depto=row["depto"],
        nombre=row["nombre"],
        nombre_sheet=row["nombre_sheet"],
        verified=bool(row["verified"]),
        paused_until=row["paused_until"],
    )


def pause_contact(phone: str, hours: float, contact_id: str | None = None) -> datetime:
    """Marca al contacto como pausado por `hours` horas desde ahora.

    Si el contacto no existe (humano respondió antes de que el cliente nos
    escribiera), creamos la fila con sólo phone+contact_id+paused_until.
    Devuelve el timestamp hasta el cual queda pausado.
    """
    paused_until = datetime.now(timezone.utc) + timedelta(hours=hours)
    with get_conn() as conn:
        conn.execute(
            f"""
            INSERT INTO {CONTACTS_TABLE} (phone, contact_id, paused_until)
            VALUES (%s, %s, %s)
            ON CONFLICT (phone) DO UPDATE SET
                contact_id   = COALESCE(EXCLUDED.contact_id, {CONTACTS_TABLE}.contact_id),
                paused_until = EXCLUDED.paused_until,
                updated_at   = NOW()
            """,
            (phone, contact_id, paused_until),
        )
    return paused_until


def upsert_contact(
    phone: str,
    *,
    contact_id: str | None = None,
    edificio: str | None = None,
    depto: str | None = None,
    nombre: str | None = None,
    nombre_sheet: str | None = None,
    verified: bool | None = None,
) -> Contact:
    """Crea o actualiza un contacto por su teléfono. Solo escribe los campos
    no-None; el resto preserva su valor actual."""
    existing = get_contact(phone)

    new_contact_id = contact_id if contact_id is not None else (existing.contact_id if existing else None)
    new_edificio = edificio if edificio is not None else (existing.edificio if existing else None)
    new_depto = depto if depto is not None else (existing.depto if existing else None)
    new_nombre = nombre if nombre is not None else (existing.nombre if existing else None)
    new_nombre_sheet = (
        nombre_sheet if nombre_sheet is not None
        else (existing.nombre_sheet if existing else None)
    )
    new_verified = (
        verified if verified is not None
        else (existing.verified if existing else False)
    )

    with get_conn() as conn:
        conn.execute(
            f"""
            INSERT INTO {CONTACTS_TABLE}
                (phone, contact_id, edificio, depto, nombre, nombre_sheet, verified)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (phone) DO UPDATE SET
                contact_id   = EXCLUDED.contact_id,
                edificio     = EXCLUDED.edificio,
                depto        = EXCLUDED.depto,
                nombre       = EXCLUDED.nombre,
                nombre_sheet = EXCLUDED.nombre_sheet,
                verified     = EXCLUDED.verified,
                updated_at   = NOW()
            """,
            (phone, new_contact_id, new_edificio, new_depto, new_nombre, new_nombre_sheet, new_verified),
        )

    return Contact(
        phone=phone,
        contact_id=new_contact_id,
        edificio=new_edificio,
        depto=new_depto,
        nombre=new_nombre,
        nombre_sheet=new_nombre_sheet,
        verified=bool(new_verified),
    )
