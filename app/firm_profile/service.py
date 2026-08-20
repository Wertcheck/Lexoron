"""get_firm_profile – Zugriff auf das kanzleiweite Profil (Singleton).

`FirmProfile` (app/models/firm_profile.py) hat KEINE technische Sperre auf
"genau eine Zeile" (kein Unique-Constraint auf eine Konstante) - das wird
allein dadurch sichergestellt, dass es GENAU EINEN Schreibpfad gibt
(app/web/settings_router.py: die POST-Route lädt IMMER über diese Funktion
und aktualisiert die gefundene/neu angelegte Zeile, legt nie eine zweite
an). Bei fehlender Zeile wird eine leere angelegt UND COMMITTET, damit
Aufrufer (Router, Export-Service) immer ein echtes, persistiertes Objekt
mit `id` erhalten, nie `None`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FirmProfile


def get_firm_profile(db: Session) -> FirmProfile:
    profile = db.query(FirmProfile).first()
    if profile is None:
        profile = FirmProfile(firm_name="")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
