"""Shared constants/formatters for the report PDFs (A4 portrait)."""
from reportlab.lib.pagesizes import A4

PAGE_W, PAGE_H = A4
MARGIN = 42
CONTENT_W = PAGE_W - 2 * MARGIN


def fmt(n):
    """Whole-yen amount with thousands separators; blank for None."""
    if n is None or n == '':
        return ''
    if isinstance(n, str):
        return n
    return f'{int(n):,}'


def spaced(text):
    """'貸借対照表' -> '貸 借 対 照 表' (the spaced heading style used on Japanese statements)."""
    return ' '.join(text)


def jp_date(d):
    return f'{d.year}年{d.month:02d}月{d.day:02d}日'


def en_date(d):
    return d.strftime('%B %d, %Y').replace(' 0', ' ')


def reiwa(d):
    return f'令和{d.year - 2018}年{d.month}月{d.day}日'
