"""Compute everything needed for the full filing package in one dict."""
from . import consumption_tax, corporate_tax, local_tax, schedules
from .statements import compute_statements


def _profile(user):
    return getattr(user, 'company_profile', None)


def compute_package(user, fy):
    data = compute_statements(user, fy)
    profile = _profile(user)
    data['profile'] = profile
    data['_fy'] = fy
    data['consumption'] = consumption_tax.compute(user, fy, data)
    corp = corporate_tax.compute(user, fy, data, profile)
    local = local_tax.compute(user, fy, data, corp, profile)
    corporate_tax.finish_schedule5(data, corp, local)
    data['corporate'], data['local'] = corp, local
    data['schedules'] = schedules.compute(user, fy, data, corp, local, data['consumption'], profile)

    notes = []
    if corp['estimated_taxes'] != data['pl']['income_taxes']:
        notes.append(f"計算上の法人税等 {corp['estimated_taxes']:,} と損益計算書の法人税・住民税及び事業税 "
                     f"{data['pl']['income_taxes']:,} が異なります。")
    if corp['form5_1']['difference']:
        notes.append(f"別表五(一)の差引合計と繰越利益剰余金に {corp['form5_1']['difference']:,} の差があります。"
                     '未納税額を入力してください。')
    data['tax_notes'] = notes + corp['warnings'] + local['warnings'] + data['consumption']['warnings']
    return data


def public_view(data):
    """JSON-safe subset for the preview API: drops private (_) keys and model objects."""
    out = {k: v for k, v in data.items() if not k.startswith('_') and k != 'profile'}
    out['schedules'] = {k: v for k, v in data['schedules'].items() if k in ('monthly', 'refund_reasons')}
    out['local'] = {k: v for k, v in data['local'].items() if k != 'offices'}
    out['corporate'] = {k: v for k, v in data['corporate'].items() if not k.startswith('form')}
    out['corporate']['carry_total'] = data['corporate']['form7']['carry_total']
    return out
