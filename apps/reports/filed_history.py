"""ILYAS SONS 合同会社: the five filed fiscal years (第1期-第5期), transcribed from the tax filings.

Every figure below comes from the filed 決算報告書 / 申告書 / 別表 / 内訳書 of the term it sits in:
  第1期 2021-08-20..2021-12-31   第2期 2022   第3期 2023   第4期 2024   第5期 2025
The terms are loaded as *closed* years: SG&A comes only from the accountant's lines (``app_expenses`` is off),
sales / purchases / cash are typed in, so the app's own (incomplete) records never change a filed number.
``load()`` then rolls term 5 forward into 第6期 (2026), which stays open and live-derived from the app.

Run it with ``manage.py load_filed_history --email <user>`` (add ``--replace`` to rebuild existing terms).
"""
import datetime

from django.db import transaction

from .models import CompanyProfile, FiscalYear, FixedAsset, StatementInput
from .services.inputs import normalize_inputs
from .services.package import roll_forward

D = datetime.date

PROFILE = {
    'legal_name': 'ILYAS SONS 合同会社', 'legal_name_en': 'ILYAS SONS LLC',
    'legal_name_kana': 'イリヤズサンズゴウドウガイシャ',
    'representative_name': 'ハムザ・ムハマッド', 'representative_name_kana': 'ハムザ ムハマッド',
    'representative_name_en': 'Hamza Muhammad',
    'corporate_number': '8120003020083', 'capital': 5_000_000,
    'address': '愛知県大府市共栄町二丁目366番', 'phone': '090-9239-0422',
    'tax_office': '半田税務署', 'business_description': '中古車仕入販売',
    'accountant_name': '税理士法人 滝川会計事務所', 'accountant_address': '愛知県新城市字札木32番地2',
    'accountant_phone': '0536-22-1723',
}
# Current (2026) offices. Past terms carry their own offices in their inputs.
PROFILE_OFFICES = [
    {'prefecture': '愛知県', 'prefecture_office': '知多県税事務所', 'municipality': '大府市',
     'employees': 1, 'months': 12, 'pref_levy': 21000, 'city_levy': 50000},
]
PROFILE_SHAREHOLDERS = [
    {'name': 'アリ シカンダー', 'address': '東海市加木屋町小家ノ脇5-345', 'relationship': '本人',
     'shares': 5_000_000, 'group': ''},
]

ZERO_CONSUMPTION = {'sales_incl_10': 0, 'sales_incl_8': 0, 'nontaxable_sales': 0,
                    'purchase_incl_10': 0, 'purchase_incl_8': 0}      # not a taxable business before 2025


def _office(prefecture, tax_office, municipality, employees, **extra):
    return {'prefecture': prefecture, 'prefecture_office': tax_office, 'municipality': municipality,
            'employees': employees, **extra}


OSAKA_CHUO = _office('大阪府', '大阪中央府税事務所', '大阪市', 0, pref_levy=0, city_levy=0)   # dormant: no levy
FIRST_TERMS_TAX = {'consumption': ZERO_CONSUMPTION, 'corporate': {'entertainment_expenses': 0}}

# ---------------------------------------------------------------------------------------------- 第1期
TERM1 = {
    'term_no': 1, 'start': D(2021, 8, 20), 'end': D(2021, 12, 31),
    'inputs': {
        'app_expenses': False, 'sales': 0, 'purchases': 0, 'cash': 4_666_683, 'capital': 5_000_000,
        'other_current_assets': [{'label': '前払費用', 'amount': 27_500, 'kind': 'advance', 'note': '1月分家賃'}],
        'offices': [OSAKA_CHUO], 'tax': FIRST_TERMS_TAX,
    },
    'assets': [('創立費', 'deferred', D(2021, 8, 10), 184_700, 'none', 0, 184_700),   # paid before incorporation
               ('開業費', 'deferred', D(2021, 12, 31), 121_117, 'none', 0, 0)],
    'expect': {'assets_total': 5_000_000, 'net_income': 0, 'income': 0, 'levy_total': 0},
}

# ---------------------------------------------------------------------------------------------- 第2期
TERM2 = {
    'term_no': 2, 'start': D(2022, 1, 1), 'end': D(2022, 12, 31),
    'inputs': {
        'app_expenses': False, 'sales': 0, 'purchases': 0, 'cash': 4_493_428, 'capital': 5_000_000,
        'offices': [OSAKA_CHUO], 'tax': FIRST_TERMS_TAX,
    },
    # the 2022 start-up costs (¥200,755) were capitalised too, so 開業費 grows from 121,117 to 321,872
    'assets': [('創立費', 'deferred', D(2021, 8, 10), 184_700, 'none', 0, 184_700),
               ('開業費', 'deferred', D(2021, 12, 31), 321_872, 'none', 0, 321_872)],
    'expect': {'assets_total': 5_000_000, 'net_income': 0, 'income': 0, 'levy_total': 0},
}

# ---------------------------------------------------------------------------------------------- 第3期
TERM3 = {
    'term_no': 3, 'start': D(2023, 1, 1), 'end': D(2023, 12, 31),
    'inputs': {
        'app_expenses': False, 'sales': 0, 'purchases': 0, 'cash': 1_435_528, 'capital': 5_000_000,
        'current_liabilities': [{'label': '預り金', 'amount': 78_600, 'kind': 'deposit_received'}],
        'extra_sga': [{'label': '役員報酬', 'amount': 2_000_000}, {'label': '給料手当', 'amount': 1_000_000},
                      {'label': '賃借料', 'amount': 136_500}],
        'rent_details': [{'label': '事務所', 'amount': 136_500, 'counterparty': '友田 治文',
                          'address': '枚方市北中振2-2-26', 'note': '令5.7.26〜令5.12.31 寝屋川市日之出町5-10 メゾンサンライズ205号'}],
        # moved from 大阪市中央区 to 寝屋川市 in July; the prefectural levy is owed once for the whole year
        'offices': [
            _office('大阪府', '大阪中央府税事務所', '大阪市', 1, months=6, pref_months=12, pref_levy=20000, city_levy=50000),
            _office('大阪府', '大阪北河内府税事務所', '寝屋川市', 1, months=5, pref_months=0, pref_levy=20000, city_levy=60000),
        ],
        'tax': {
            'consumption': ZERO_CONSUMPTION,
            'corporate': {'entertainment_expenses': 0, 'addbacks': [
                {'label': '役員給与の損金不算入額', 'amount': 2_000_000},
                {'label': '使用人給与の損金不算入額', 'amount': 1_000_000}]},
        },
    },
    'assets': [('創立費', 'deferred', D(2021, 8, 10), 184_700, 'none', 0, 184_700),
               ('開業費', 'deferred', D(2021, 12, 31), 321_872, 'none', 0, 321_872)],
    'expect': {'assets_total': 1_942_100, 'net_income': -3_136_500, 'income': -136_500, 'carry_total': 136_500,
               'levy_total': 70_000, 'unpaid_pref': 20_000, 'unpaid_city': 50_000},
}

# ---------------------------------------------------------------------------------------------- 第4期
TERM4 = {
    'term_no': 4, 'start': D(2024, 1, 1), 'end': D(2024, 12, 31),
    'inputs': {
        'app_expenses': False, 'sales': 0, 'purchases': 0, 'cash': 507_928, 'capital': 5_000_000,
        'opening_retained_earnings': -3_136_500,
        'current_liabilities': [{'label': '預り金', 'amount': 78_600, 'kind': 'deposit_received'}],
        'extra_sga': [{'label': '役員報酬', 'amount': 600_000}, {'label': '賃借料', 'amount': 327_600}],
        'rent_details': [{'label': '事務所', 'amount': 327_600, 'counterparty': '友田 治文',
                          'address': '枚方市北中振2-2-26', 'note': '令6.1.1〜令6.12.31 寝屋川市日之出町5-10 メゾンサンライズ205号'}],
        # head office registered in 綾部市 with no staff; the only working office is 寝屋川市
        'offices': [
            _office('京都府', '', '綾部市', 0, pref_levy=0, city_levy=0),
            _office('大阪府', '大阪北河内府税事務所', '寝屋川市', 1, pref_levy=20000, city_levy=60000),
        ],
        'tax': {
            'consumption': ZERO_CONSUMPTION,
            'corporate': {
                'entertainment_expenses': 0,
                'addbacks': [{'label': '役員給与の損金不算入額', 'amount': 600_000}],
                'prior_losses': [{'label': '2023-01-01 to 2023-12-31', 'amount': 136_500}],
                'opening_unpaid_pref': 20_000, 'opening_unpaid_city': 50_000,   # 2023 levies were never paid
            },
        },
    },
    'assets': [('創立費', 'deferred', D(2021, 8, 10), 184_700, 'none', 0, 184_700),
               ('開業費', 'deferred', D(2021, 12, 31), 321_872, 'none', 0, 321_872)],
    'expect': {'assets_total': 1_014_500, 'net_income': -927_600, 'income': -327_600, 'carry_total': 464_100,
               'levy_total': 80_000, 'unpaid_pref': 40_000, 'unpaid_city': 110_000},
}

# ---------------------------------------------------------------------------------------------- 第5期
SGA_2025 = [
    ('役員報酬', 2_400_000), ('法定福利費', 116_200), ('接待交際費', 268_420), ('会議費', 392_813),
    ('旅費交通費', 606_261), ('通信費', 156_816), ('消耗品費', 707_399), ('事務用消耗品費', 19_323),
    ('支払手数料', 781_136), ('車両費', 2_686_506), ('燃料費', 800_087), ('地代家賃', 1_201_547),
    ('保険料', 21_200), ('租税公課', 232_510), ('支払報酬料', 60_000), ('雑費', 239_696),
]
TERM5 = {
    'term_no': 5, 'start': D(2025, 1, 1), 'end': D(2025, 12, 31),
    'inputs': {
        'app_expenses': False, 'cash_accounts': [2],            # only the GMO あおぞらネット account is on the books
        'sales': 28_680_691, 'purchases': 26_895_932, 'purchase_discounts': 11_980,
        'closing_inventory': 2_377_190, 'cash': 84_973, 'capital': 5_000_000,
        'opening_retained_earnings': -4_064_100, 'income_taxes': 79_100, 'prior_year_taxes': 150_000,
        'other_current_assets': [
            {'label': '立替金', 'amount': 16_820, 'kind': 'advance', 'note': 'リサイクル預託金'},
            {'label': '未収還付法人税等', 'amount': 554_693, 'kind': 'receivable', 'counterparty': '半田税務署',
             'address': '半田市宮路町50-5', 'note': '消費税還付金'},
            {'label': '役員貸付金', 'amount': 266_560, 'executive': True, 'kind': 'loan',
             'counterparty': 'ハムザ・ムハマッド', 'address': '名古屋市緑区清水山2-1809'},
        ],
        'investments': [{'label': '差入保証金', 'amount': 150_000, 'kind': 'deposit_paid',
                         'counterparty': 'CAA / 冨田 鉦', 'note': '保証金 50,000 / ヤード保証金 100,000'}],
        'current_liabilities': [
            {'label': '役員借入金', 'amount': 10_229_024, 'kind': 'borrowing', 'counterparty': 'アリ・シカンダー',
             'address': '東海市加木屋町小家ノ脇5-345'},
            {'label': '未払金', 'amount': 348_494, 'kind': 'payable', 'counterparty': '舞鶴年金事務所 / 楽天カード',
             'address': '京都府舞鶴市南田辺50-8 / 東京都港区南青山2-6-21',
             'note': '社会保険 172,140 / カード 176,354'},
            {'label': '未払法人税等', 'amount': 204_100, 'kind': 'tax_payable'},
            {'label': '預り金', 'amount': 53_240, 'kind': 'deposit_received', 'note': '従業員 源泉所得税'},
        ],
        'extra_sga': [{'label': l, 'amount': a} for l, a in SGA_2025],
        'non_operating_income': [
            {'label': '受取利息', 'amount': 6},
            {'label': '雑収入', 'amount': 594, 'note': 'キャッシュバック 2円(三井住友カード) / 消費税差額 592円(半田税務署)'}],
        'rent_details': [
            {'label': '車両保管ヤード', 'amount': 406_667, 'counterparty': '冨田 鉦', 'address': '大府市共栄町6-84',
             'note': '令7.6.1〜令7.12.31'},
            {'label': '事務所 (寝屋川市日之出町5-10 メゾンサンライズ205号)', 'amount': 186_240, 'counterparty': '友田 治文',
             'address': '枚方市北中振2-2-26', 'note': '令7.1.1〜令7.6.30'},
            {'label': '事務所 (京都府綾部市上野町西ケ窪25-1)', 'amount': 436_370, 'counterparty': 'CJエンターテインメント(株)',
             'address': '京都市上京区大宮通上立売上 西入伊佐町196-3', 'registration': 'T3011101086115',
             'note': '令7.3.28〜令7.12.31'},
            {'label': '住居 (名古屋市緑区清水山2-1809)', 'amount': 172_270, 'counterparty': '大東建託パートナーズ(株)',
             'address': '東京都港区港南2-16-1', 'registration': 'T1010401016618', 'note': '令7.11.1〜令7.12.31'},
        ],
        'offices': [
            _office('愛知県', '知多県税事務所', '大府市', 1, months=1, pref_levy=21000, city_levy=50000),
            _office('大阪府', '大阪北河内府税事務所', '寝屋川市', 1, months=11, pref_levy=20000, city_levy=60000),
        ],
        'tax': {
            'consumption': {
                'sales_incl_10': 31_548_751, 'nontaxable_sales': 6, 'purchase_incl_10': 35_053_275,
                'purchase_incl_8': 27_857, 'purchase_returns_10': 13_178,
                'transitional_incl_10': 3_187_439, 'transitional_incl_8': 56_626,
            },
            'corporate': {
                'prior_losses': [{'label': '2023-01-01 to 2023-12-31', 'amount': 136_500},
                                 {'label': '2024-01-01 to 2024-12-31', 'amount': 327_600}],
                'opening_unpaid_pref': 40_000, 'opening_unpaid_city': 110_000, 'paid_city': 25_000,
            },
        },
    },
    'assets': [('簡易建物', 'building', D(2025, 9, 30), 728_307, 'straight_line', 10, 0),
               ('iPhone', 'equipment', D(2025, 2, 16), 108_630, 'declining_200', 4, 0),
               ('パソコン (ASUS M3604YA)', 'equipment', D(2025, 5, 1), 119_800, 'declining_200', 4, 0),
               ('エアコン', 'equipment', D(2025, 4, 30), 112_728, 'declining_200', 6, 0),
               ('創立費', 'deferred', D(2021, 8, 10), 184_700, 'none', 0, 184_700),
               ('開業費', 'deferred', D(2021, 12, 31), 321_872, 'none', 0, 321_872)],
    'expect': {'assets_total': 4_884_123, 'net_income': -6_886_635, 'income': -6_657_535, 'carry_total': 7_121_635,
               'levy_total': 79_100, 'unpaid_pref': 60_000, 'unpaid_city': 144_100, 'consumption_refund': 554_693},
}

TERMS = [TERM1, TERM2, TERM3, TERM4, TERM5]


def _blank(fy):
    """A placeholder year that never held anything (e.g. a mis-numbered term created by hand)."""
    data = getattr(getattr(fy, 'inputs', None), 'data', None)
    return not data and not fy.fixed_assets.exists()


def _fill_profile(user):
    profile, _ = CompanyProfile.objects.get_or_create(user=user)
    for field, value in PROFILE.items():
        if not getattr(profile, field):
            setattr(profile, field, value)
    if not profile.offices:
        profile.offices = PROFILE_OFFICES
    if not profile.shareholders:
        profile.shareholders = PROFILE_SHAREHOLDERS
    profile.save()
    return profile


def _create_term(user, term):
    fy = FiscalYear.objects.create(user=user, term_no=term['term_no'], start_date=term['start'],
                                   end_date=term['end'], status='final')
    StatementInput.objects.create(fiscal_year=fy, data=normalize_inputs(term['inputs']))
    for name, category, acquired, cost, method, life, opening in term['assets']:
        FixedAsset.objects.create(fiscal_year=fy, name=name, category=category, acquired_on=acquired, cost=cost,
                                  method=method, useful_life=life, opening_book_value=opening)
    return fy


@transaction.atomic
def load(user, replace=False, roll=True, log=print):
    """Create the company profile and terms 1-5 (and term 6 by roll-forward). Returns the created years."""
    _fill_profile(user)
    created = []
    for term in TERMS:
        existing = FiscalYear.objects.filter(user=user, term_no=term['term_no']).first()
        if existing:
            if not (replace or _blank(existing)):
                log(f"term {term['term_no']}: already exists, kept (use --replace to rebuild)")
                continue
            existing.delete()
        created.append(_create_term(user, term))
        log(f"term {term['term_no']}: loaded {term['start']} to {term['end']}")
    if roll and not FiscalYear.objects.filter(user=user, term_no=6).exists():
        prev = FiscalYear.objects.get(user=user, term_no=5)
        created.append(_open_term6(user, prev))
        log('term 6: opened by roll-forward from term 5')
    return created


def _open_term6(user, prev):
    fy = roll_forward(user, prev)
    record = fy.inputs
    data = dict(record.data)
    # 未収還付法人税等 (the ¥554,693 consumption-tax refund) was received on 2026-04-10 (GMO account), so it is no
    # longer an asset; cash for 2026 comes from the bank ledger.
    data['other_current_assets'] = [i for i in data['other_current_assets'] if i['label'] != '未収還付法人税等']
    data['cash_accounts'] = [2]
    record.data = normalize_inputs(data)
    record.save()
    return fy
