"""Einmaliges Setup-Skript: legt den ERSTEN Admin-Nutzer an (Prompt 26).

Wird manuell ausgeführt (kein automatischer Aufruf beim App-Start):

    python scripts/create_admin.py

Liest E-Mail und (optional) Passwort aus Umgebungsvariablen:
- ADMIN_EMAIL (Pflicht, keine Vorgabe im Code)
- ADMIN_INITIAL_PASSWORD (optional - wenn nicht gesetzt, wird ein
  kryptografisch sicheres Zufallspasswort erzeugt und EINMALIG auf der
  Konsole ausgegeben, nirgendwo sonst gespeichert oder geloggt)

Das initiale Passwort landet NIE im Quellcode oder in einer Konfigurations-
datei, die versehentlich eingecheckt werden könnte - siehe .env.example
(dort nur als auskommentierter Hinweis, nicht als tatsächlicher Wert).
`must_change_password=True` wird immer gesetzt: der erste Login MUSS mit
einer Passwortänderung enden, bevor das Dashboard nutzbar ist.

Idempotent: wenn bereits ein Nutzer mit der Rolle "Admin" existiert,
bricht das Skript ohne Änderung ab (kein versehentliches Zurücksetzen
eines bestehenden Admin-Passworts durch erneutes Ausführen).
"""

from __future__ import annotations

import os
import secrets
import sys

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, User


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL")
    if not email:
        print(
            "FEHLER: Umgebungsvariable ADMIN_EMAIL ist nicht gesetzt.\n"
            "Beispiel: ADMIN_EMAIL=admin@kanzlei.test python scripts/create_admin.py",
            file=sys.stderr,
        )
        return 1

    password = os.environ.get("ADMIN_INITIAL_PASSWORD")
    generated = password is None
    if generated:
        password = secrets.token_urlsafe(18)

    db = SessionLocal()
    try:
        existing_admin = (
            db.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "Admin")
            .first()
        )
        if existing_admin is not None:
            print(
                f"Es existiert bereits ein Admin-Nutzer ({existing_admin.email}). "
                "Kein neuer Admin angelegt (idempotent - kein Zurücksetzen bestehender "
                "Passwörter durch dieses Skript).",
                file=sys.stderr,
            )
            return 1

        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None:
            print(
                "FEHLER: Rolle 'Admin' existiert nicht in der Datenbank - wurde die "
                "Migration '..._seed_default_roles...' bereits ausgeführt? "
                "(alembic upgrade head)",
                file=sys.stderr,
            )
            return 1

        normalized_email = email.strip().lower()
        user = User(
            email=normalized_email,
            role_id=admin_role.id,
            is_active=True,
            password_hash=hash_password(password),
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        print(f"Admin-Nutzer angelegt: {normalized_email}")
        if generated:
            print("Generiertes initiales Passwort (wird NUR JETZT angezeigt):")
            print(f"  {password}")
        print(
            "Beim ersten Login wird eine Passwortänderung erzwungen "
            "(must_change_password=True)."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
