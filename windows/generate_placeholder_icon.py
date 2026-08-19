"""Erzeugt den Platzhalter `windows/app_icon.ico` (Prompt 47).

Kein echtes Kanzlei-/Firmenlogo existiert im Projekt - dieses Skript baut
stattdessen einen einfachen, aus der bestehenden Weboberfläche abgeleiteten
Platzhalter (Kreissiegel-Motiv, Initialen "KA"), damit PyInstaller/Inno Setup
überhaupt ein Icon einbetten können. Farbe (`--seal-green` #2f6f62,
`--paper-000` #fbfbf9) direkt aus app/web/static/css/app.css übernommen, um
optisch zum Dashboard (Wachssiegel-Ästhetik) zu passen - siehe dortige
`:root`-Variablen.

Ersetzen: sobald ein echtes Kanzlei-/Produktlogo vorliegt, einfach
`windows/app_icon.ico` durch die echte Datei ersetzen - `windows/
kanzlei_ai.spec` und `windows/installer.iss` referenzieren nur den Dateipfad,
nicht dieses Skript. Erneutes Ausführen (aus dem Projekt-Root, aktivierte
venv, "pillow" ist bereits Projektabhängigkeit):

    python windows/generate_placeholder_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_SEAL_GREEN = (47, 111, 98)  # app/web/static/css/app.css: --seal-green
_PAPER = (251, 251, 249)  # app/web/static/css/app.css: --paper-000
_SIZES = (16, 24, 32, 48, 64, 128, 256)
_OUTPUT_PATH = Path(__file__).resolve().parent / "app_icon.ico"


def _render_at(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 16)
    radius = max(2, size // 6)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad], radius=radius, fill=_SEAL_GREEN + (255,)
    )

    margin = size * 0.22
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=_PAPER + (255,),
        width=max(1, size // 24),
    )

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", int(size * 0.34))
    except OSError:
        font = ImageFont.load_default()

    text = "KA"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - text_width) / 2 - bbox[0], (size - text_height) / 2 - bbox[1]),
        text,
        font=font,
        fill=_PAPER + (255,),
    )
    return img


def main() -> None:
    largest = _render_at(max(_SIZES))
    largest.save(str(_OUTPUT_PATH), format="ICO", sizes=[(s, s) for s in _SIZES])
    print(f"Icon geschrieben: {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
