"""PolicyService – versionierte Kanzleiregeln.

Nur eine Version pro `name` ist gleichzeitig `is_active` - eine neue
Version deaktiviert automatisch die vorherige (kein Löschen, volle
Historie bleibt in der Datenbank erhalten, analog zur Source-
"Rechtsaktualität"-Regel aus Prompt 14).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent, Policy


class PolicyService:
    def create_version(
        self, name: str, content: str, db: Session, *, actor: str
    ) -> Policy:
        if not content or not content.strip():
            raise ValueError("content darf nicht leer sein")

        previous = (
            db.query(Policy)
            .filter_by(name=name, is_active=True)
            .first()
        )
        new_version_number = (previous.version + 1) if previous else 1

        if previous is not None:
            previous.is_active = False

        policy = Policy(
            name=name,
            version=new_version_number,
            content=content,
            is_active=True,
        )
        db.add(policy)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="Policy",
                entity_id=policy.id,
                event_type="policy_version_created",
                actor=actor,
                details=f"'{name}' Version {new_version_number} aktiviert",
            )
        )
        db.commit()
        db.refresh(policy)
        return policy

    def get_active_policy(self, name: str, db: Session) -> Policy | None:
        return db.query(Policy).filter_by(name=name, is_active=True).first()
