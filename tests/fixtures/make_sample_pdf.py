"""Regenerate tests/fixtures/sample-report.pdf.

Run from the repository root: python tests/fixtures/make_sample_pdf.py
Needs reportlab (a dev dependency) and a TrueType font with Romanian letters.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]

PAGES = [
    [
        "Raportul anual 2025 al companiei Exemplu S.A.",
        "Profitul net al exercițiului financiar a fost de 120 milioane lei.",
        "Cifra de afaceri a crescut cu 15% față de anul anterior, datorită con-",
        "tractelor noi semnate în trimestrul al patrulea.",
        "Compania a investit în digitalizare și în eficiența energetică.",
    ],
    [],  # an empty page, like a scanned image or a full-page chart
    [
        "Politica de dividende",
        "Consiliul propune distribuirea a 60% din profitul net ca dividende.",
        "Data plății propusă este 25 iunie 2026.",
    ],
]


def main() -> None:
    font_path = next(p for p in FONT_CANDIDATES if Path(p).exists())
    pdfmetrics.registerFont(TTFont("Body", font_path))
    out = Path(__file__).with_name("sample-report.pdf")
    pdf = canvas.Canvas(str(out), pagesize=A4, invariant=1)
    for lines in PAGES:
        pdf.setFont("Body", 11)
        y = 800
        for line in lines:
            pdf.drawString(60, y, line)
            y -= 18
        pdf.showPage()
    pdf.save()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
