"""CLI-Skript: befüllt die Datenbank mit synthetischen Testfällen
(Prompt 29).

Verwendung:
    python scripts/seed_synthetic_data.py --count 20
    python scripts/seed_synthetic_data.py --count 20 --seed 42  # reproduzierbar

Erzeugt AUSSCHLIESSLICH fiktive Daten (siehe app/synthetic_data/) - ruft
KEINE Claude API auf, verursacht keine Kosten. Legt zusätzlich einmalig
die gemeinsame Rechtsquellen-/Kanzlei-Wissensbasis an (nur beim ersten
Aufruf sinnvoll - führt bei mehrfachem Aufruf zu doppelten Einträgen,
daher NICHT automatisch bei jedem Lauf, siehe --with-knowledge-base).
"""

from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.synthetic_data import SyntheticDataGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count", type=int, default=20, help="Anzahl zu erzeugender Fälle (Standard: 20)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Zufalls-Seed für reproduzierbare Fälle (Standard: zufällig)",
    )
    parser.add_argument(
        "--with-knowledge-base",
        action="store_true",
        help="Zusätzlich eine gemeinsame Rechtsquellen-/Wissensbasis anlegen "
        "(nur beim ersten Aufruf sinnvoll, sonst doppelte Einträge)",
    )
    args = parser.parse_args()

    if args.count <= 0:
        print("FEHLER: --count muss positiv sein", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        generator = SyntheticDataGenerator(seed=args.seed)

        if args.with_knowledge_base:
            sources, knowledge_items = generator.generate_shared_knowledge_base(db)
            print(
                f"{len(sources)} Rechtsquellen, {len(knowledge_items)} "
                "Wissenselemente angelegt."
            )

        cases = generator.generate_many(db, args.count)
        print(f"{len(cases)} synthetische Fälle erzeugt:")
        for case in cases:
            print(
                f"  - [{case.scenario_key}] {case.matter.title} "
                f"({case.matter.reference_number})"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
