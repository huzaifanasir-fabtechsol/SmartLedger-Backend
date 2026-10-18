"""Depreciation (減価償却) for the fixed-asset register.

Supported: 定額法, 200%定率法, 一時償却 (full write-off), none.

Known limitation: the 200%定率法 does not switch to the 改定償却率 once the
償却保証額 is reached (that needs the statutory 保証率/改定償却率 tables). This only
matters from roughly the 3rd year onward, so it is not applied here yet.
"""
import math
from decimal import Decimal, ROUND_HALF_UP

TANGIBLE = ('building', 'equipment', 'vehicle', 'other_tangible')


def straight_line_rate(useful_life):
    """Statutory 償却率 for 定額法: 1/n rounded UP to 3 decimals (e.g. 10y -> 0.100, 3y -> 0.334)."""
    return math.ceil(1000 / useful_life) / 1000


def declining_200_rate(useful_life):
    """Statutory 償却率 for 200%定率法: 2/n rounded to 3 decimals (e.g. 4y -> 0.500, 6y -> 0.333)."""
    return float((Decimal(2) / Decimal(useful_life)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))


def months_in_year(acquired_on, start_date, end_date):
    """Months of use in the fiscal year, counting the acquisition month (capped at the year length)."""
    begin = max(acquired_on, start_date)
    months = (end_date.year - begin.year) * 12 + end_date.month - begin.month + 1
    year_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    return max(0, min(months, year_months))


def depreciate(asset, start_date, end_date):
    """Return a dict for one FixedAsset: opening, depreciation, closing, accumulated, months, rate."""
    acquired_this_year = asset.acquired_on >= start_date
    opening = asset.cost if acquired_this_year else asset.opening_book_value
    months = months_in_year(asset.acquired_on, start_date, end_date)
    year_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    rate = 0.0
    amount = 0

    if asset.method == 'lump_sum':
        amount = opening
    elif asset.method in ('straight_line', 'declining_200') and asset.useful_life > 0:
        if asset.method == 'straight_line':
            rate = straight_line_rate(asset.useful_life)
            base = asset.cost
        else:
            rate = declining_200_rate(asset.useful_life)
            base = opening
        # Decimal avoids float error (e.g. 49999.99999 flooring to 49999)
        exact = Decimal(base) * Decimal(str(rate)) * months / year_months
        amount = int(exact.to_integral_value(rounding='ROUND_FLOOR'))
        amount = max(0, min(amount, opening - 1))  # keep 備忘価額 of 1 yen

    closing = opening - amount
    return {
        'asset': asset,
        'opening': opening,
        'depreciation': amount,
        'closing': closing,
        'accumulated': asset.cost - closing,
        'months': months,
        'rate': rate,
    }
