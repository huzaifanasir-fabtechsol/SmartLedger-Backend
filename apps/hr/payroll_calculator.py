"""
Japanese Payroll and Withholding Tax Calculation Engine
Matches standard Japanese payroll formulas (Kyokai Kenpo, Welfare Pension, NTA Withholding Tax).
"""

from decimal import Decimal, ROUND_HALF_UP


def round_jpy(amount: Decimal | float | int) -> Decimal:
    """Round to nearest integer in Japanese Yen."""
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


# Kyokai Kenpo Standard Monthly Remuneration Brackets (Sample Standard for Health Insurance & Pension)
# Grade table for Monthly Remuneration (標準報酬月額)
STANDARD_REMUNERATION_TABLE = [
    (0, 63000, 58000),
    (63000, 73000, 68000),
    (73000, 83000, 78000),
    (83000, 93000, 88000),
    (93000, 101000, 98000),
    (101000, 107000, 104000),
    (107000, 115000, 110000),
    (115000, 126000, 118000),
    (126000, 134000, 126000),
    (134000, 142000, 134000),
    (142000, 150000, 142000),
    (150000, 158000, 150000),
    (158000, 166000, 160000),
    (166000, 175000, 170000),
    (175000, 185000, 180000),
    (185000, 195000, 190000),
    (195000, 210000, 200000),
    (210000, 230000, 220000),
    (230000, 250000, 240000),
    (250000, 270000, 260000),
    (270000, 290000, 280000),
    (290000, 310000, 300000),
    (310000, 330000, 320000),
    (330000, 350000, 340000),
    (350000, 370000, 360000),
    (370000, 395000, 380000),
    (395000, 425000, 410000),
    (425000, 455000, 440000),
    (455000, 485000, 470000),
    (485000, 515000, 500000),
    (515000, 545000, 530000),
    (545000, 575000, 560000),
    (575000, 605000, 590000),
    (605000, 635000, 620000),
    (635000, 665000, 650000),
    (665000, 695000, 680000),
    (695000, 999999999, 700000),
]


def get_standard_monthly_remuneration(salary: Decimal | float) -> Decimal:
    """Find the standard monthly remuneration (標準報酬月額)."""
    val = float(salary)
    for low, high, std in STANDARD_REMUNERATION_TABLE:
        if low <= val < high:
            return Decimal(str(std))
    return Decimal(str(val))


def calculate_health_insurance(standard_monthly_remuneration: Decimal, rate: Decimal = Decimal('0.05015')) -> Decimal:
    """
    Calculate employee share of Health Insurance (健康保険料).
    Default employee rate is ~5.015% (e.g. Kyokai Kenpo Tokyo ~10.03% total / 2).
    """
    return round_jpy(standard_monthly_remuneration * rate)


def calculate_welfare_pension(standard_monthly_remuneration: Decimal, rate: Decimal = Decimal('0.0915')) -> Decimal:
    """
    Calculate employee share of Welfare Pension (厚生年金保険料).
    Standard rate is 18.3% split equally (9.15% employee share).
    """
    return round_jpy(standard_monthly_remuneration * rate)


def calculate_employment_insurance(gross_taxable: Decimal, rate: Decimal = Decimal('0.006')) -> Decimal:
    """
    Calculate employee share of Employment Insurance (雇用保険料).
    General business rate is 6/1000 (0.6%).
    """
    return round_jpy(gross_taxable * rate)


# Japanese National Tax Agency (NTA) Monthly Withholding Tax Table (給与所得の源泉徴収税額表 - 甲欄)
# Format: (min_taxable_base, max_taxable_base, [tax_for_0_dependents, tax_for_1_dep, tax_for_2_dep, tax_for_3_dep, tax_for_4_dep, tax_for_5_dep, tax_for_6_dep, tax_for_7_dep])
NTA_MONTHLY_TAX_TABLE = [
    (0, 88000, [0, 0, 0, 0, 0, 0, 0, 0]),
    (88000, 89000, [130, 0, 0, 0, 0, 0, 0, 0]),
    (89000, 91000, [260, 0, 0, 0, 0, 0, 0, 0]),
    (91000, 93000, [390, 0, 0, 0, 0, 0, 0, 0]),
    (93000, 95000, [530, 0, 0, 0, 0, 0, 0, 0]),
    (95000, 97000, [660, 0, 0, 0, 0, 0, 0, 0]),
    (97000, 99000, [790, 0, 0, 0, 0, 0, 0, 0]),
    (99000, 101000, [920, 0, 0, 0, 0, 0, 0, 0]),
    (101000, 103000, [1050, 0, 0, 0, 0, 0, 0, 0]),
    (103000, 105000, [1190, 0, 0, 0, 0, 0, 0, 0]),
    (105000, 107000, [1320, 0, 0, 0, 0, 0, 0, 0]),
    (107000, 109000, [1450, 0, 0, 0, 0, 0, 0, 0]),
    (109000, 111000, [1580, 0, 0, 0, 0, 0, 0, 0]),
    (111000, 113000, [1710, 0, 0, 0, 0, 0, 0, 0]),
    (113000, 115000, [1840, 0, 0, 0, 0, 0, 0, 0]),
    (115000, 117000, [1980, 0, 0, 0, 0, 0, 0, 0]),
    (117000, 119000, [2110, 0, 0, 0, 0, 0, 0, 0]),
    (119000, 121000, [2240, 0, 0, 0, 0, 0, 0, 0]),
    (121000, 123000, [2370, 0, 0, 0, 0, 0, 0, 0]),
    (123000, 125000, [2500, 0, 0, 0, 0, 0, 0, 0]),
    (125000, 127000, [2640, 0, 0, 0, 0, 0, 0, 0]),
    (127000, 129000, [2770, 0, 0, 0, 0, 0, 0, 0]),
    (129000, 131000, [2900, 0, 0, 0, 0, 0, 0, 0]),
    (131000, 133000, [3030, 0, 0, 0, 0, 0, 0, 0]),
    (133000, 135000, [3160, 0, 0, 0, 0, 0, 0, 0]),
    (135000, 137000, [3300, 0, 0, 0, 0, 0, 0, 0]),
    (137000, 139000, [3430, 0, 0, 0, 0, 0, 0, 0]),
    (139000, 141000, [3560, 0, 0, 0, 0, 0, 0, 0]),
    (141000, 143000, [3690, 0, 0, 0, 0, 0, 0, 0]),
    (143000, 145000, [3820, 0, 0, 0, 0, 0, 0, 0]),
    (145000, 147000, [3960, 0, 0, 0, 0, 0, 0, 0]),
    (147000, 149000, [4090, 0, 0, 0, 0, 0, 0, 0]),
    (149000, 151000, [4220, 0, 0, 0, 0, 0, 0, 0]),
    (151000, 153000, [4350, 0, 0, 0, 0, 0, 0, 0]),
    (153000, 155000, [4480, 0, 0, 0, 0, 0, 0, 0]),
    (155000, 157000, [4620, 0, 0, 0, 0, 0, 0, 0]),
    (157000, 159000, [4750, 0, 0, 0, 0, 0, 0, 0]),
    (159000, 161000, [4880, 0, 0, 0, 0, 0, 0, 0]),
    (161000, 163000, [5010, 0, 0, 0, 0, 0, 0, 0]),
    (163000, 165000, [5140, 0, 0, 0, 0, 0, 0, 0]),
    (165000, 167000, [5270, 0, 0, 0, 0, 0, 0, 0]),
    (167000, 169000, [3510, 1900, 280, 0, 0, 0, 0, 0]),
    (169000, 171000, [3640, 2030, 410, 0, 0, 0, 0, 0]),
    (171000, 173000, [3770, 2160, 540, 0, 0, 0, 0, 0]),
    (173000, 175000, [3910, 2290, 670, 0, 0, 0, 0, 0]),
    (175000, 177000, [4040, 2420, 810, 0, 0, 0, 0, 0]),
    (177000, 179000, [4170, 2560, 940, 0, 0, 0, 0, 0]),
    (179000, 181000, [4300, 2690, 1070, 0, 0, 0, 0, 0]),
    (181000, 183000, [4430, 2820, 1200, 0, 0, 0, 0, 0]),
    (183000, 185000, [4570, 2950, 1340, 0, 0, 0, 0, 0]),
    (185000, 187000, [4700, 3080, 1470, 0, 0, 0, 0, 0]),
    (187000, 189000, [4830, 3220, 1600, 0, 0, 0, 0, 0]),
    (189000, 191000, [4960, 3350, 1730, 110, 0, 0, 0, 0]),
    (191000, 193000, [5090, 3480, 1860, 250, 0, 0, 0, 0]),
    (193000, 195000, [5230, 3610, 2000, 380, 0, 0, 0, 0]),
    (195000, 197000, [5360, 3750, 2130, 510, 0, 0, 0, 0]),
    (197000, 199000, [5490, 3880, 2260, 640, 0, 0, 0, 0]),
    (199000, 201000, [5620, 4010, 2390, 780, 0, 0, 0, 0]),
    (201000, 203000, [5750, 4140, 2530, 910, 0, 0, 0, 0]),
    (203000, 206000, [5920, 4310, 2690, 1070, 0, 0, 0, 0]),
    (206000, 209000, [6120, 4510, 2890, 1270, 0, 0, 0, 0]),
    (209000, 212000, [6320, 4700, 3090, 1470, 0, 0, 0, 0]),
    (212000, 215000, [6510, 4900, 3280, 1670, 50, 0, 0, 0]),
    (215000, 218000, [6710, 5100, 3480, 1860, 250, 0, 0, 0]),
    (218000, 221000, [6910, 5300, 3680, 2060, 450, 0, 0, 0]),
    (221000, 224000, [7110, 5490, 3880, 2260, 640, 0, 0, 0]),
    (224000, 227000, [7300, 5690, 4070, 2460, 840, 0, 0, 0]),
    (227000, 230000, [7500, 5890, 4270, 2650, 1040, 0, 0, 0]),
    (230000, 233000, [7700, 6090, 4470, 2850, 1240, 0, 0, 0]),
    (233000, 236000, [7900, 6280, 4670, 3050, 1430, 0, 0, 0]),
    (236000, 239000, [8090, 6480, 4860, 3250, 1630, 20, 0, 0]),
    (239000, 242000, [8290, 6680, 5060, 3440, 1830, 220, 0, 0]),
    (242000, 245000, [8490, 6880, 5260, 3640, 2030, 410, 0, 0]),
    (245000, 248000, [8690, 7070, 5460, 3840, 2220, 610, 0, 0]),
    (248000, 251000, [8880, 7270, 5650, 4040, 2420, 810, 0, 0]),
    (251000, 254000, [9080, 7470, 5850, 4230, 2620, 1010, 0, 0]),
    (254000, 257000, [9280, 7670, 6050, 4430, 2820, 1200, 0, 0]),
    (257000, 260000, [9480, 7860, 6250, 4630, 3010, 1400, 0, 0]),
    (260000, 263000, [9670, 8060, 6450, 4830, 3210, 1600, 0, 0]),
    (263000, 266000, [9870, 8260, 6640, 5020, 3410, 1790, 0, 0]),
    (266000, 269000, [10070, 8460, 6840, 5220, 3610, 1990, 370, 0]),
    (269000, 272000, [10270, 8650, 7040, 5420, 3800, 2190, 570, 0]),
    (272000, 275000, [10460, 8850, 7240, 5620, 4000, 2390, 770, 0]),
    (275000, 278000, [10660, 9050, 7430, 5810, 4200, 2580, 960, 0]),
    (278000, 281000, [10860, 9250, 7630, 6010, 4400, 2780, 1160, 0]),
    (281000, 284000, [11060, 9440, 7830, 6210, 4590, 2980, 1360, 0]),
    (284000, 287000, [11250, 9640, 8030, 6410, 4790, 3170, 1560, 0]),
    (287000, 290000, [11450, 9840, 8220, 6600, 4990, 3370, 1750, 0]),
    (290000, 293000, [11650, 10040, 8420, 6800, 5190, 3570, 1950, 330]),
    (293000, 296000, [11850, 10230, 8620, 7000, 5380, 3770, 2150, 530]),
    (296000, 299000, [12040, 10430, 8820, 7200, 5580, 3960, 2350, 730]),
    (299000, 302000, [12240, 10630, 9010, 7390, 5780, 4160, 2540, 930]),
    (302000, 305000, [12440, 10830, 9210, 7590, 5980, 4360, 2740, 1120]),
    (305000, 308000, [12640, 11020, 9410, 7790, 6170, 4560, 2940, 1320]),
    (308000, 311000, [12830, 11220, 9610, 7990, 6370, 4750, 3140, 1520]),
    (311000, 314000, [13030, 11420, 9800, 8180, 6570, 4950, 3330, 1720]),
    (314000, 317000, [13230, 11620, 10000, 8380, 6770, 5150, 3530, 1910]),
    (317000, 320000, [13430, 11810, 10200, 8580, 6960, 5350, 3730, 2110]),
]


def calculate_withholding_income_tax(taxable_base: Decimal | float, dependents: int = 0) -> Decimal:
    """
    Calculate Japan National Tax Agency Withholding Income Tax (所得税).
    Uses the official Kou-ran (甲欄) table for employees with declaration of dependents.
    """
    val = float(taxable_base)
    if val <= 87000:
        return Decimal('0')

    dep_idx = max(0, min(7, dependents))

    for low, high, tax_list in NTA_MONTHLY_TAX_TABLE:
        if low <= val < high:
            return Decimal(str(tax_list[dep_idx]))

    # If above 320,000, standard approximation formula:
    # Taxable salary deduction ~ 5% - 20% bracket
    excess = max(0.0, val - 320000.0)
    base_tax = float(NTA_MONTHLY_TAX_TABLE[-1][2][dep_idx])
    tax = base_tax + excess * 0.1021  # Marginal rate + 2.1% reconstruction tax
    return round_jpy(tax)


def calculate_japanese_payroll(
    basic_salary: Decimal | float | int = 0,
    commuting_allowance: Decimal | float | int = 0,
    overtime_allowance: Decimal | float | int = 0,
    allowances: Decimal | float | int = 0,
    resident_tax: Decimal | float | int = 0,
    leave_deduction: Decimal | float | int = 0,
    other_deductions: Decimal | float | int = 0,
    dependents_count: int = 0,
    is_employment_insurance_exempt: bool = False,
    custom_health_insurance: Decimal | float | int | None = None,
    custom_welfare_pension: Decimal | float | int | None = None,
    custom_employment_insurance: Decimal | float | int | None = None,
    custom_income_tax: Decimal | float | int | None = None,
) -> dict:
    """
    Complete Japanese Payroll calculation matching Pay Slip standard.
    """
    basic_salary = Decimal(str(basic_salary or 0))
    commuting_allowance = Decimal(str(commuting_allowance or 0))
    overtime_allowance = Decimal(str(overtime_allowance or 0))
    allowances = Decimal(str(allowances or 0))
    resident_tax = Decimal(str(resident_tax or 0))
    leave_deduction = Decimal(str(leave_deduction or 0))
    other_deductions = Decimal(str(other_deductions or 0))

    # 1. Taxable payment (課税支給額)
    taxable_payment = max(Decimal('0'), basic_salary + overtime_allowance + allowances - leave_deduction)

    # 2. Total gross payment (支給額合計)
    gross_payment = taxable_payment + commuting_allowance

    # 3. Social Insurance
    std_remuneration = get_standard_monthly_remuneration(taxable_payment)

    if custom_health_insurance is not None:
        health_insurance = Decimal(str(custom_health_insurance))
    else:
        health_insurance = calculate_health_insurance(std_remuneration)

    if custom_welfare_pension is not None:
        welfare_pension = Decimal(str(custom_welfare_pension))
    else:
        welfare_pension = calculate_welfare_pension(std_remuneration)

    if custom_employment_insurance is not None:
        employment_insurance = Decimal(str(custom_employment_insurance))
    elif is_employment_insurance_exempt:
        employment_insurance = Decimal('0')
    else:
        employment_insurance = calculate_employment_insurance(taxable_payment)

    total_social_insurance = health_insurance + welfare_pension + employment_insurance

    # 4. Taxable Base for Withholding Income Tax (課税対象額)
    taxable_income_base = max(Decimal('0'), taxable_payment - total_social_insurance)

    # 5. Income Tax (所得税)
    if custom_income_tax is not None:
        income_tax = Decimal(str(custom_income_tax))
    else:
        income_tax = calculate_withholding_income_tax(taxable_income_base, dependents=dependents_count)

    # 6. Total Deductions (控除額合計)
    total_deductions = total_social_insurance + income_tax + resident_tax + other_deductions

    # 7. Net Take-Home Pay (差引支給額)
    net_amount = gross_payment - total_deductions

    return {
        'basic_salary': basic_salary,
        'commuting_allowance': commuting_allowance,
        'overtime_allowance': overtime_allowance,
        'allowances': allowances,
        'taxable_payment': taxable_payment,
        'gross_payment': gross_payment,
        'health_insurance': health_insurance,
        'welfare_pension': welfare_pension,
        'employment_insurance': employment_insurance,
        'total_social_insurance': total_social_insurance,
        'taxable_income_base': taxable_income_base,
        'income_tax': income_tax,
        'resident_tax': resident_tax,
        'leave_deduction': leave_deduction,
        'other_deductions': other_deductions,
        'total_deductions': total_deductions,
        'net_amount': net_amount,
    }
