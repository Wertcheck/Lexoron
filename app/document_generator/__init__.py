"""Dokumenten- und Schriftsatz-Generator (Block 3, 20.08.).

Füllt Platzhalter EINER `DocumentTemplate` (app/models/document_template.py)
mit den echten Falldaten EINER `Matter` (Aktenisolation) - rein lokale,
deterministische Textverarbeitung (Regex-Ersetzung fest definierter
Platzhalter, siehe app/document_generator/placeholders.py), KEIN KI-/
Cloud-Aufruf. Damit ist die DSGVO-Anforderung "Generierung findet lokal
statt, keine Mandantendaten an externe LLMs/Cloud-Anbieter" durch die
Architektur selbst erzwungen, nicht nur durch eine Konfiguration - es
gibt in diesem Modul schlicht keinen Netzwerk-Client.

Siehe:
- app/document_generator/service.py - Generierung/Platzhalter-Auflösung.
- app/document_generator/template_service.py - CRUD für Vorlagen.
- app/document_generator/docx_export.py / pdf_export.py - Dateiexport.
- app/web/document_templates_router.py - Vorlagenverwaltung
  (/dashboard/library/mustertexte).
- app/web/document_generator_router.py - Generieren/Vorschau/Export
  (/dashboard/tools/dokumentgenerator).
"""
