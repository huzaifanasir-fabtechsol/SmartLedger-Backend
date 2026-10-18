"""地方税 / Local Taxes: allocation sheets, 第六号様式 (prefecture), 別表九, 第二十号様式 (municipality), 委任状."""
from reportlab.lib import colors

from .common import cols, jp_name, power_of_attorney
from .layout import CONTENT_W, fmt
from .writer import H, R, T

GRAY = (0.93, 0.93, 0.93)


def _by_prefecture(offices):
    groups = {}
    for o in offices:
        g = groups.setdefault(o['prefecture'] or '-', {'name': o['prefecture'] or '-', 'office': o['prefecture_office'],
                                                      'offices': []})
        g['offices'].append(o)
    return list(groups.values())


def _sum(items, key):
    return sum(o[key] for o in items)


def draw_basis(w, c, l):
    w.begin_form(('地方税分割基礎確認表', 'Local Tax Allocation Basis Check Sheet'), jp_name('地方税分割基礎確認表'), filer=True)
    w.kv_table([
        (('資本金等の額', 'Capital'), fmt(c['capital'])),
        (('分割基準', 'Allocation basis'), ('従業者数', 'Number of employees')),
        (('従業者数の合計', 'Total employees'), str(l['total_employees'])),
        (('事務所・事業所数', 'Number of offices'), str(len(l['offices']))),
        (('課税標準(所得)', 'Taxable income'), fmt(c['taxable_income'])),
        (('課税標準(法人税額)', 'Taxable corporate tax'), fmt(c['local_base'])),
    ])
    data = [[w.t(h) for h in (('都道府県', 'Prefecture'), ('市区町村', 'Municipality'), ('従業者数', 'Employees'),
                                ('均等割月数', 'Months'), ('分割割合', 'Share'))]]
    for o in l['offices']:
        data.append([w.para(o['prefecture'], 7.5), w.para(o['municipality'], 7.5), str(o['employees']), str(o['months']),
                     f"{o['share'] * 100:.1f}%"])
    w.table(data, [CONTENT_W - 4 * 80, 80, 80, 80, 80],
            [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
             ('ALIGN', (2, 1), (-1, -1), 'RIGHT')], size=7.5)


def draw_split_amounts(w, c, l):
    w.begin_form(('地方税の分割税額明細書', 'Local Tax Allocation by Authority'), jp_name('地方税の分割税額明細書'), filer=True)
    data = [[w.t(h) for h in (('納付先', 'Authority'), ('税目', 'Tax'), ('法人税割・所得割(円)', 'Income-based (JPY)'),
                                ('均等割(円)', 'Per-capita (JPY)'), ('計(円)', 'Total (JPY)'))]]
    total = 0
    for g in _by_prefecture(l['offices']):
        income = _sum(g['offices'], 'pref_corp_tax') + _sum(g['offices'], 'business_tax') + _sum(g['offices'], 'special_tax')
        levy = _sum(g['offices'], 'pref_levy')
        if not w.full and not (income or levy):
            continue
        data.append([w.para(g['office'] or g['name'], 7.5), w.para(('道府県民税・事業税', 'Prefectural + enterprise tax'), 7.5),
                     fmt(income), fmt(levy), fmt(income + levy)])
        total += income + levy
    for o in l['offices']:
        income, levy = o['city_corp_tax'], o['city_levy']
        if not w.full and not (income or levy):
            continue
        data.append([w.para(o['municipality'] or o['prefecture'], 7.5), w.para(('市町村民税', 'Municipal inhabitant tax'), 7.5),
                     fmt(income), fmt(levy), fmt(income + levy)])
        total += income + levy
    data.append([w.t(('合計', 'Total')), '', '', '', fmt(total)])
    w.table(data, [CONTENT_W - 120 - 270, 120, 90, 90, 90],
            [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
             ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)], size=7.5)


def draw_tax_base_split(w, c, l):
    w.begin_form(('課税標準の分割に関する明細書 (道府県)', 'Allocation of Tax Base (Prefectures)'),
                 jp_name('第十号様式 課税標準の分割に関する明細書'), filer=True)
    data = [[w.t(h) for h in (('都道府県', 'Prefecture'), ('従業者数', 'Employees'), ('分割割合', 'Share'),
                                ('分割所得(円)', 'Allocated income (JPY)'), ('分割法人税額(円)', 'Allocated corp. tax (JPY)'))]]
    for g in _by_prefecture(l['offices']):
        emp = _sum(g['offices'], 'employees')
        share = emp / l['total_employees'] if l['total_employees'] else 0
        data.append([w.para(g['name'], 7.5), str(emp), f'{share * 100:.1f}%', fmt(_sum(g['offices'], 'income_base')),
                     fmt(_sum(g['offices'], 'corp_tax_base'))])
    data.append([w.t(('合計', 'Total')), str(l['total_employees']), '100.0%', fmt(_sum(l['offices'], 'income_base')),
                 fmt(_sum(l['offices'], 'corp_tax_base'))])
    w.table(data, [CONTENT_W - 4 * 90 - 10, 90, 90, 100, 100 + 10],
            [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
             ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)], size=7.5)

    w.begin_form(('課税標準の分割に関する明細書 (市町村)', 'Allocation of Tax Base (Municipalities)'),
                 jp_name('第二十二号の二様式 課税標準の分割に関する明細書'), filer=True)
    data = [[w.t(h) for h in (('市区町村', 'Municipality'), ('従業者数', 'Employees'), ('分割割合', 'Share'),
                                ('分割法人税額(円)', 'Allocated corp. tax (JPY)'))]]
    for o in l['offices']:
        data.append([w.para(o['municipality'] or o['prefecture'], 7.5), str(o['employees']), f"{o['share'] * 100:.1f}%",
                     fmt(o['corp_tax_base'])])
    data.append([w.t(('合計', 'Total')), str(l['total_employees']), '100.0%', fmt(_sum(l['offices'], 'corp_tax_base'))])
    w.table(data, [CONTENT_W - 3 * 100, 100, 100, 100],
            [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
             ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)], size=7.5)


def draw_prefecture_return(w, c, l):
    for g in _by_prefecture(l['offices']):
        offs = g['offices']
        income = _sum(offs, 'income_base')
        low = sum(o['income_bracket']['low'] for o in offs)
        mid = sum(o['income_bracket']['mid'] for o in offs)
        high = sum(o['income_bracket']['high'] for o in offs)
        biz = _sum(offs, 'business_tax')
        w.begin_form((f"第六号様式  道府県民税・事業税・特別法人事業税の確定申告書 ({g['name']})",
                      f"Prefectural Inhabitant & Enterprise Tax Return ({g['name']})"),
                     jp_name('第六号様式 法人の道府県民税・事業税・特別法人事業税の確定申告書'), filer=True)
        rows = [
            H(('事業税 (所得割)', 'Enterprise tax (income-based)')),
            R(28, ('所得金額 (分割後)', 'Allocated income'), income, keep=True),
            R(29, ('年400万円以下の金額 (3.5%)', 'Up to ¥4 million (3.5%)'), low),
            R(30, ('年400万円超800万円以下の金額 (5.3%)', '¥4-8 million (5.3%)'), mid),
            R(31, ('年800万円超の金額 (7.0%)', 'Over ¥8 million (7.0%)'), high),
            T(32, ('所得割額', 'Income-based enterprise tax'), biz, keep=True),
            H(('特別法人事業税', 'Special corporate enterprise tax')),
            R(63, ('課税標準となる所得割額', 'Taxable base (income-based tax)'), biz),
            T(64, ('特別法人事業税額 (37%)', 'Special enterprise tax (37%)'), _sum(offs, 'special_tax'), keep=True),
            H(('道府県民税', 'Prefectural inhabitant tax')),
            R('', ('課税標準となる法人税額', 'Taxable corporate tax (allocated)'), _sum(offs, 'corp_tax_base'), keep=True),
            R('', (f"法人税割額 ({offs[0]['pref_rate']}%)", f"Corporate-tax-based amount ({offs[0]['pref_rate']}%)"),
              _sum(offs, 'pref_corp_tax'), keep=True),
            R('', ('均等割額 (年額 × 月数/12)', 'Per-capita levy (annual x months/12)'), _sum(offs, 'pref_levy'), keep=True),
            T('', ('道府県民税額計', 'Total prefectural inhabitant tax'), _sum(offs, 'pref_total'), keep=True),
            H(('納付額', 'Amount payable')),
            R('', ('中間納付額', 'Interim payments'), l['interim_pref']),
            T('', ('この申告により納付すべき税額', 'Payable on this return'),
              max(0, _sum(offs, 'pref_total') + biz + _sum(offs, 'special_tax') - l['interim_pref']), keep=True),
        ]
        w.lines_table(cols(), rows)


def draw_form9(w, c):
    f = c['form7']
    w.begin_form(('第六号様式別表九  欠損金額等及び災害損失金の控除明細書', 'Local Tax Schedule 9: Loss Carry-forward Deduction'),
                 jp_name('第六号様式別表九 欠損金額等及び災害損失金額の控除明細書'), filer=True)
    rows = [H(('控除未済欠損金額', 'Unused prior-year losses'))]
    rows += [R('', r['label'], r['amount'], r['used'], r['carry'], keep=True) for r in f['rows']]
    rows += [T('', ('計', 'Total'), f['prior_total'], f['used_total'], f['prior_carry_total'], keep=True),
             R('', ('当期欠損金額', 'Current-year loss'), f['current_loss'], None, f['current_loss'], keep=True),
             T('', ('翌期繰越額合計', 'Total carried forward'), None, None, f['carry_total'], keep=True)]
    heads = [('控除未済欠損金額', 'Unused loss'), ('当期控除額', 'Deducted'), ('翌期繰越額', 'Carried forward')]
    w.lines_table(cols(3, heads, label=('事業年度', 'Fiscal year'), no=('', ''), value_w=92), rows)


def draw_municipal_returns(w, c, l):
    for o in l['offices']:
        name = o['municipality'] or o['prefecture'] or '-'
        w.begin_form((f'第二十号様式  市町村民税の確定申告書 ({name})', f'Municipal Inhabitant Tax Return ({name})'),
                     jp_name('第二十号様式 法人の市町村民税の確定申告書'), filer=True)
        rows = [
            R('', ('課税標準となる法人税額 (分割後)', 'Taxable corporate tax (allocated)'), o['corp_tax_base'], keep=True),
            R('', (f"法人税割額 ({o['city_rate']}%)", f"Corporate-tax-based amount ({o['city_rate']}%)"), o['city_corp_tax'], keep=True),
            R('', ('均等割額の年額', 'Annual per-capita levy'), o['city_levy_annual'], keep=True),
            R('', ('均等割額の算定月数', 'Months'), o['months'], keep=True),
            R('', ('均等割額 (年額 × 月数/12)', 'Per-capita levy (annual x months/12)'), o['city_levy'], keep=True),
            T('', ('市町村民税額計', 'Total municipal inhabitant tax'), o['city_total'], keep=True),
            R('', ('中間納付額', 'Interim payments'), l['interim_city'] if o is l['offices'][0] else 0),
            T('', ('この申告により納付すべき税額', 'Payable on this return'),
              max(0, o['city_total'] - (l['interim_city'] if o is l['offices'][0] else 0)), keep=True),
        ]
        w.lines_table(cols(label=('項目', 'Item'), no=('', '')), rows)


def render(w):
    c, l = w.data['corporate'], w.data['local']
    draw_basis(w, c, l)
    draw_split_amounts(w, c, l)
    draw_tax_base_split(w, c, l)
    draw_prefecture_return(w, c, l)
    draw_form9(w, c)
    draw_municipal_returns(w, c, l)
    if w.full:
        power_of_attorney(w, ('道府県民税・事業税・特別法人事業税及び市町村民税の確定申告書の作成・提出に関する一切の件',
                              'Preparation and filing of the prefectural, enterprise and municipal tax returns'),
                          ('都道府県税事務所・市町村', 'Prefectural tax office / municipality'))
