"""Built-in CJK fonts (no font files needed) so Japanese glyphs render in the PDFs."""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
MINCHO = 'HeiseiMin-W3'
GOTHIC = 'HeiseiKakuGo-W5'


def font_for(lang):
    """Serif for the Japanese statements, sans for English (also covers Japanese names in English PDFs)."""
    return MINCHO if lang == 'ja' else GOTHIC
