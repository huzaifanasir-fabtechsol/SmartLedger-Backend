"""法人税・地方法人税 for a 中小法人 (capital ≤ ¥100m): 別表四, 別表五(一)(二), 別表六(一), 別表七,
別表十五, 別表二, plus the tax itself.

Rates: 15% up to ¥8m of taxable income, 23.2% above; 地方法人税 10.3% of the corporate tax.
Rounding follows the statutory forms (taxable income to ¥1,000, tax to ¥100).

Scope/assumptions:
- Small-company rules only (loss carry-forward limit 100% of income, ¥8m entertainment allowance).
  For capital above ¥100m the result is flagged, not computed under large-company rules.
- Adjustments beyond taxes booked as expense and excess entertainment come from the
  ``tax.corporate.addbacks`` / ``deductions`` inputs (treated as 留保).
"""
SME_CAPITAL_LIMIT = 100_000_000
EIGHT_MILLION = 8_000_000


def _floor(n, unit):
    return n // unit * unit


def corporate_tax_amount(taxable):
    low = min(taxable, EIGHT_MILLION)
    high = max(0, taxable - EIGHT_MILLION)
    return _floor(low * 15 // 100 + high * 232 // 1000, 100)


def _months(fy):
    return (fy.end_date.year - fy.start_date.year) * 12 + fy.end_date.month - fy.start_date.month + 1


def compute(user, fy, data, profile=None):
    inputs, pl = data['_inputs'], data['pl']
    c = inputs['tax']['corporate']
    warnings = []
    capital = inputs['capital'] or (profile.capital if profile else 0)
    sme = capital <= SME_CAPITAL_LIMIT
    if not sme:
        warnings.append('資本金1億円超のため、大法人の取扱い(交際費・欠損金控除の制限等)は計算していません。')

    # ---- 別表十五 entertainment ------------------------------------------------------
    if c['entertainment_expenses'] is not None:
        ent_total = c['entertainment_expenses']
    else:
        ent_total = sum(i['amount'] for i in pl['sga_items']
                        if '交際' in i['label'] or 'entertain' in i['label'].lower())
    months = _months(fy)
    food_half = c['entertainment_food'] * 50 // 100
    limit_fixed = EIGHT_MILLION * months // 12 if sme else 0
    line3 = min(ent_total, limit_fixed)
    line4 = max(food_half, line3)
    ent_excess = max(0, ent_total - line4)
    form15 = {'expenses': ent_total, 'food_half': food_half, 'fixed_limit': limit_fixed,
              1: ent_total, 2: food_half, 3: line3, 4: line4, 5: ent_excess, 'months': months}

    # ---- 別表四 ----------------------------------------------------------------------
    net_income = pl['net_income']
    taxes_booked = pl['taxes_total']
    other_add = sum(i['amount'] for i in c['addbacks'])
    other_ded = sum(i['amount'] for i in c['deductions'])
    add_total = taxes_booked + ent_excess + other_add
    provisional = net_income + add_total - other_ded                      # 23
    withholding = c['withholding_credit']                                 # 25 (tax credit added back)
    income_pre = provisional + withholding                                # 26 = 34
    prior_losses = c['prior_losses']
    prior_total = sum(i['amount'] for i in prior_losses)
    loss_used = min(max(income_pre, 0), prior_total) if sme else 0
    income = income_pre - loss_used                                       # 39 = 52
    current_loss = max(0, -income)
    form4 = {
        'net_income': net_income, 'taxes_booked': taxes_booked, 'entertainment_excess': ent_excess,
        'other_add': other_add, 'add_total': add_total, 'other_ded': other_ded,
        'provisional': provisional, 'withholding': withholding, 'income_pre': income_pre,
        'loss_used': loss_used, 'income': income,
    }

    # ---- Tax -------------------------------------------------------------------------
    taxable = _floor(max(0, income), 1000)
    corp_tax = corporate_tax_amount(taxable)
    credit = min(withholding, corp_tax)
    corp_net = corp_tax - credit
    corp_interim = c['interim_paid']
    corp_payable = max(0, corp_net - corp_interim)
    corp_refund = max(0, corp_interim - corp_net) + max(0, withholding - corp_tax)
    local_base = _floor(corp_tax, 1000)
    local_tax = _floor(local_base * 103 // 1000, 100)

    # ---- 別表七 loss carry-forward ----------------------------------------------------
    remaining = loss_used
    losses = []
    for item in prior_losses:
        used = min(item['amount'], remaining)
        remaining -= used
        losses.append({'label': item['label'], 'amount': item['amount'], 'used': used,
                       'carry': item['amount'] - used})
    carry_total = sum(l['carry'] for l in losses) + current_loss
    form7 = {'rows': losses, 'prior_total': prior_total, 'used_total': loss_used,
             'prior_carry_total': sum(l['carry'] for l in losses), 'current_loss': current_loss,
             'carry_total': carry_total, 'income_for_limit': max(income_pre, 0)}

    # ---- 別表六(一) ---------------------------------------------------------------------
    interest = sum(i['amount'] for i in pl['non_op_income_items']
                   if '利息' in i['label'] or 'interest' in i['label'].lower())
    form6 = {'interest_income': interest, 'withholding': withholding, 'credit': credit}

    # ---- 別表五(一)(二) ------------------------------------------------------------------
    return_data = {
        'sme': sme, 'capital': capital, 'warnings': warnings,
        'form15': form15, 'form4': form4, 'form6': form6, 'form7': form7,
        'taxable_income': taxable, 'income': income, 'income_pre': income_pre,
        'corp_tax': corp_tax, 'corp_credit': credit, 'corp_net': corp_net, 'corp_interim': corp_interim,
        'corp_payable': corp_payable, 'corp_refund': corp_refund,
        'local_base': local_base, 'local_tax': local_tax, 'local_payable': local_tax,
        'form1_split': {'low': min(taxable, EIGHT_MILLION), 'high': max(0, taxable - EIGHT_MILLION)},
    }
    return_data['form2'] = _family_company(profile, capital)
    return return_data


def finish_schedule5(data, corp, local):
    """別表五(一)(二) need the local-tax results, so they are built after local_tax.compute()."""
    inputs, pl, bs = data['_inputs'], data['pl'], data['bs']
    c = inputs['tax']['corporate']

    opening_ret, closing_ret = inputs['opening_retained_earnings'], bs['retained_earnings']
    prov_closing = sum(i['amount'] for i in bs['current_liabilities'] if '未払法人税' in i['label'])
    prov_opening = c['opening_provision']
    prov_increase = pl['taxes_total']
    prov_decrease = prov_opening + prov_increase - prov_closing

    unpaid_corp = c['unpaid_corporate'] if c['unpaid_corporate'] is not None else corp['corp_payable'] + corp['local_payable']
    unpaid_pref = c['unpaid_pref'] if c['unpaid_pref'] is not None else local['pref_total_payable']
    unpaid_city = c['unpaid_city'] if c['unpaid_city'] is not None else local['city_total_payable']

    rows = [  # (code, label, opening, decrease, increase, closing)
        (25, ('繰越損益金', 'Retained earnings (P&L carry-forward)'), opening_ret, opening_ret, closing_ret, closing_ret),
        (26, ('納税充当金', 'Provision for taxes'), prov_opening, prov_decrease, prov_increase, prov_closing),
        (27, ('未納法人税及び未納地方法人税', 'Unpaid corporate tax & local corporate tax'), 0, 0, -unpaid_corp, -unpaid_corp),
        (29, ('未納道府県民税', 'Unpaid prefectural inhabitant tax'), 0, 0, -unpaid_pref, -unpaid_pref),
        (30, ('未納市町村民税', 'Unpaid municipal inhabitant tax'), 0, 0, -unpaid_city, -unpaid_city),
    ]
    closing_sum = sum(r[5] for r in rows)
    corp['form5_1'] = {'rows': rows, 'closing_total': closing_sum,
                       'opening_total': sum(r[2] for r in rows),
                       'decrease_total': sum(r[3] for r in rows),
                       'increase_total': sum(r[4] for r in rows),
                       'difference': closing_sum - closing_ret}

    def tax_row(code, label, accrued):
        return (code, label, 0, accrued, 0, accrued)   # opening, accrued, paid, closing
    corp['form5_2'] = {
        'rows': [
            tax_row(1, ('法人税', 'Corporate tax'), corp['corp_payable']),
            tax_row(2, ('地方法人税', 'Local corporate tax'), corp['local_payable']),
            tax_row(6, ('道府県民税 (均等割・法人税割)', 'Prefectural inhabitant tax'), local['pref_inhabitant_total']),
            tax_row(11, ('市町村民税 (均等割・法人税割)', 'Municipal inhabitant tax'), local['city_total']),
            tax_row(16, ('事業税・特別法人事業税', 'Enterprise tax & special enterprise tax'),
                    local['business_total'] + local['special_total']),
        ],
        'provision': {30: prov_opening, 31: prov_increase, 32: 0, 33: prov_opening + prov_increase,
                      34: prov_decrease, 40: prov_decrease, 41: prov_closing},
    }
    corp['estimated_taxes'] = (corp['corp_net'] + corp['local_tax'] + local['levy_total']
                               + local['corp_based_total'] + local['business_total'] + local['special_total'])


def _family_company(profile, capital):
    holders = list(profile.shareholders) if profile and profile.shareholders else []
    total = sum(int(h.get('shares') or 0) for h in holders) or capital
    groups = {}
    for h in holders:
        key = h.get('group') or h.get('name') or '?'
        g = groups.setdefault(key, {'name': h.get('name', ''), 'address': h.get('address', ''),
                                    'relationship': h.get('relationship', ''), 'shares': 0, 'members': 0})
        g['shares'] += int(h.get('shares') or 0)
        g['members'] += 1
    ranked = sorted(groups.values(), key=lambda g: g['shares'], reverse=True)
    top3 = ranked[:3]
    top3_shares = sum(g['shares'] for g in top3)
    ratio = (top3_shares * 100 / total) if total else 0
    members_total = sum(g['members'] for g in ranked) or 0
    members_top3 = sum(g['members'] for g in top3)
    members_ratio = (members_top3 * 100 / members_total) if members_total else 0
    judge = max(ratio, members_ratio) if holders else 0   # 別表二 line 10 = max of (3), (6), (9)
    return {'total_shares': total, 'top3_shares': top3_shares, 'ratio': ratio,
            'members_total': members_total, 'members_top3': members_top3, 'members_ratio': members_ratio,
            'judgement_ratio': judge, 'is_family': judge > 50, 'ranked': ranked}
