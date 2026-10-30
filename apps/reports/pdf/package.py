"""Assemble the selected report parts into one PDF or Excel file (one language, one style per file)."""
from . import kessan
from .i18n import LANGS
from .writer import Writer
from .xlsx import XlsxWriter

MODES = ('full', 'simple')
FORMATS = {'pdf': Writer, 'xlsx': XlsxWriter}

# part key -> render(writer). Registered below as each document module is imported.
PARTS = {'kessan': kessan.render}


def _register():
    from . import chihozei, genka, hojinzei, other, shohizei, uchiwake
    PARTS.update({
        'shohizei': shohizei.render,
        'hojinzei': hojinzei.render,
        'schedules': lambda w: (uchiwake.render(w), genka.render(w)),
        'chihozei': chihozei.render,
        'other': other.render,
    })


_register()


class UnknownPart(ValueError):
    pass


def build_package(data, parts=('kessan',), lang='ja', mode='full', output='pdf'):
    """Return a BytesIO with the requested parts rendered in order (``output``: 'pdf' or 'xlsx')."""
    unknown = [p for p in parts if p not in PARTS]
    if unknown:
        raise UnknownPart(', '.join(unknown))
    if lang not in LANGS:
        raise ValueError(f'lang must be one of {LANGS}')
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES}')
    if output not in FORMATS:
        raise ValueError(f'output must be one of {tuple(FORMATS)}')
    w = FORMATS[output](data, lang, mode)
    w.c.setTitle(w.t(('決算報告書・申告書類', 'Financial Statements & Tax Filing Package')))
    for part in parts:
        PARTS[part](w)
    return w.finish()
