"""固定資産減価償却内訳明細 / Fixed Asset Depreciation Schedule."""
from reportlab.lib import colors

from .common import jp_name
from .i18n import CATEGORY, METHOD
from .layout import CONTENT_W, fmt


def render(w):
    dep = w.data['schedules']['depreciation']
    if not dep['rows']:
        return
    w.begin_form(('固定資産減価償却内訳明細', 'Fixed Asset Depreciation Schedule'), jp_name('固定資産減価償却内訳明細'), filer=True)
    w.company_line()
    heads = [('資産名', 'Asset'), ('種類', 'Category'), ('取得日', 'Acquired'), ('償却方法', 'Method'), ('耐用年数', 'Life'),
             ('取得価額', 'Cost'), ('期首帳簿価額', 'Opening'), ('当期償却額', 'Depreciation'), ('償却累計額', 'Accumulated'),
             ('期末帳簿価額', 'Closing')]
    widths = [70, 56, 48, 66, 24, 48, 48, 48, 48, CONTENT_W - 456]
    data = [[w.t(h) for h in heads]]
    for r in dep['rows']:
        data.append([w.para(r['name'], 6.5), w.para(CATEGORY[r['category']], 6.5), r['acquired_on'].strftime('%Y-%m-%d'),
                     w.para(METHOD[r['method']], 6.5), str(r['life'] or ''), fmt(r['cost']), fmt(r['opening']),
                     fmt(r['depreciation']), fmt(r['accumulated']), fmt(r['closing'])])
    t = dep['total']
    data.append([w.t(('合計', 'Total')), '', '', '', '', fmt(t['cost']), fmt(t['opening']), fmt(t['depreciation']),
                 fmt(t['accumulated']), fmt(t['closing'])])
    cmds = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), (0.93, 0.93, 0.93)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'), ('ALIGN', (5, 1), (-1, -1), 'RIGHT'), ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)]
    w.table(data, widths, cmds, size=6.5)

    for caption, store, names in ((('種類別合計', 'Totals by category'), dep['by_category'], CATEGORY),
                                  (('償却方法別合計', 'Totals by depreciation method'), dep['by_method'], METHOD)):
        w.caption(caption, size=8)
        tdata = [[w.t(('区分', 'Group')), w.t(('件数', 'Count')), w.t(('取得価額', 'Cost')), w.t(('当期償却額', 'Depreciation')),
                  w.t(('償却累計額', 'Accumulated')), w.t(('期末帳簿価額', 'Closing'))]]
        for key, g in store.items():
            tdata.append([w.t(names[key]), str(g['count']), fmt(g['cost']), fmt(g['depreciation']), fmt(g['accumulated']),
                          fmt(g['closing'])])
        w.table(tdata, [CONTENT_W - 4 * 70 - 40, 40, 70, 70, 70, 70],
                [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), (0.93, 0.93, 0.93)),
                 ('ALIGN', (1, 1), (-1, -1), 'RIGHT')], size=7)
