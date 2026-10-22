"""Schema, defaults and validation for StatementInput.data.

All amounts are whole yen (int). List entries are ``{"label": str, "amount": int}`` plus
optional text fields (see ITEM_STR_KEYS). ``None`` for an overridable figure means
"derive it from existing app data".
"""

LIST_KEYS = (
    'other_current_assets',    # 立替金, 未収還付法人税等, 役員貸付金 ... (optional "executive": true)
    'investments',             # 投資その他の資産: 差入保証金 ...
    'current_liabilities',     # 役員借入金, 未払金, 未払法人税等, 預り金 ...
    'fixed_liabilities',
    'extra_sga',               # additional 販管費 lines not tracked as Expenses
    'non_operating_income',    # 受取利息, 雑収入
    'non_operating_expenses',
    'rent_details',            # 地代家賃の内訳: label=usage, counterparty=landlord, note=period
)

# Optional text fields on list entries. ``kind`` classifies a balance for the 内訳書 schedules.
ITEM_STR_KEYS = ('kind', 'counterparty', 'address', 'note', 'registration', 'rate')
KINDS = {'', 'receivable', 'advance', 'loan', 'deposit_paid', 'payable', 'deposit_received',
         'borrowing', 'tax_payable'}

INT_KEYS = (
    'purchase_discounts',
    'opening_inventory',
    'closing_inventory',
    'income_taxes',            # 法人税・住民税及び事業税
    'prior_year_taxes',        # 過年度法人税等
    'capital',
    'opening_retained_earnings',
    'dividends',
)

OVERRIDE_KEYS = ('sales', 'purchases', 'cash')   # int or None (None = derive)

# Settings for the tax returns. Type is taken from the default: None = optional int
# (None means derive), int, str, or list of {"label", "amount"}.
TAX_DEFAULTS = {
    'consumption': {
        'sales_incl_10': None, 'sales_incl_8': None, 'nontaxable_sales': None,
        'purchase_incl_10': None, 'purchase_incl_8': None,
        'purchase_returns_10': 0, 'purchase_returns_8': 0,
        'transitional_incl_10': 0, 'transitional_incl_8': 0,   # 経過措置 80% purchases (tax-included)
        'interim_paid': 0, 'interim_paid_local': 0,
        'refund_note': '',
    },
    'corporate': {
        'prior_losses': [],          # label = period (e.g. "2023-01-01〜2023-12-31"), amount
        'addbacks': [], 'deductions': [],
        'interim_paid': 0, 'withholding_credit': 0,
        'entertainment_expenses': None, 'entertainment_food': 0,
        'opening_provision': 0,
        'unpaid_corporate': None, 'unpaid_pref': None, 'unpaid_city': None,
    },
    'local': {'interim_pref': 0, 'interim_city': 0},
}

DEFAULTS = {
    'sales': None,
    'purchases': None,
    'cash': None,
    'include_salaries': False,
    'notes_extra': [],
    'cash_accounts': None,     # ids of the CompanyAccounts that belong on the balance sheet (None = all)
}
DEFAULTS.update({k: 0 for k in INT_KEYS})
DEFAULTS.update({k: [] for k in LIST_KEYS})


class InputError(ValueError):
    pass


def _as_int(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f'{key} must be a number')
    return int(round(value))


def _normalize_list(value, key):
    if not isinstance(value, list):
        raise InputError(f'{key} must be a list')
    items = []
    for item in value:
        if not isinstance(item, dict) or not str(item.get('label', '')).strip():
            raise InputError(f'{key}: every entry needs a label')
        entry = {'label': str(item['label']).strip(), 'amount': _as_int(item.get('amount', 0), key)}
        if item.get('executive'):
            entry['executive'] = True
        for extra in ITEM_STR_KEYS:
            text = str(item.get(extra) or '').strip()
            if text:
                entry[extra] = text
        if entry.get('kind') and entry['kind'] not in KINDS:
            raise InputError(f"{key}: unknown kind '{entry['kind']}'")
        items.append(entry)
    return items


def _normalize_group(group, data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise InputError(f'tax.{group} must be an object')
    out = {}
    for key, default in TAX_DEFAULTS[group].items():
        value = data.get(key, default)
        path = f'tax.{group}.{key}'
        if isinstance(default, list):
            out[key] = _normalize_list(value, path)
        elif isinstance(default, str):
            out[key] = str(value or '')
        elif default is None:
            out[key] = None if value is None else _as_int(value, path)
        else:
            out[key] = _as_int(value, path)
    return out


def normalize_inputs(data):
    """Return ``data`` merged over DEFAULTS with types validated; raises InputError."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise InputError('data must be an object')
    out = {}
    for key, default in DEFAULTS.items():
        value = data.get(key, default)
        if key in INT_KEYS:
            out[key] = _as_int(value, key)
        elif key in OVERRIDE_KEYS:
            out[key] = None if value is None else _as_int(value, key)
        elif key in LIST_KEYS:
            out[key] = _normalize_list(value, key)
        elif key == 'include_salaries':
            out[key] = bool(value)
        elif key == 'cash_accounts':
            if value is None:
                out[key] = None
            elif isinstance(value, list) and all(isinstance(v, int) and not isinstance(v, bool) for v in value):
                out[key] = sorted(set(value))
            else:
                raise InputError('cash_accounts must be a list of account ids or null')
        elif key == 'notes_extra':
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise InputError('notes_extra must be a list of strings')
            out[key] = value
    tax = data.get('tax') or {}
    if not isinstance(tax, dict):
        raise InputError('tax must be an object')
    out['tax'] = {group: _normalize_group(group, tax.get(group)) for group in TAX_DEFAULTS}
    return out
