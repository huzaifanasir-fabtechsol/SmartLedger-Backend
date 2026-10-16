from rest_framework import serializers
from apps.expense.models import Expense, ExpenseCategory, Restaurant, SparePart

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'location', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SparePartSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePart
        fields = ['id', 'name', 'address', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    spare_part_name = serializers.CharField(source='spare_part.name', read_only=True)
    tax_percent_used = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    tax_category = serializers.CharField(required=False, default='exclusive')
    number_of_taxes = serializers.IntegerField(required=False, default=0)
    number_of_exclusive = serializers.IntegerField(required=False, default=0)
    number_of_inclusive_tax = serializers.IntegerField(required=False, default=0)
    exclusive_tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    inclusive_tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    taxes = serializers.JSONField(required=False, default=list)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'description', 'date', 'category', 'category_name',
            'transaction', 'restaurant', 'restaurant_name', 'spare_part', 'spare_part_name',
            'is_cash', 'is_highlighted', 'tax_category', 'tax_percent_used', 'tax_amount',
            'number_of_taxes', 'number_of_exclusive', 'number_of_inclusive_tax',
            'exclusive_tax_amount', 'inclusive_tax_amount', 'taxes',
            'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_amount']

    def validate(self, attrs):
        from decimal import Decimal, InvalidOperation
        category = attrs.get('category')
        if not category and self.instance:
            category = self.instance.category

        spare_part = attrs.get('spare_part')
        if spare_part is None and self.instance:
            spare_part = self.instance.spare_part

        is_spare_parts = bool(category and category.name and category.name.strip().upper() == 'SPARE PARTS')
        if not is_spare_parts:
            attrs['spare_part'] = None

        # Amount to work with
        amount = attrs.get('amount')
        if amount is None and self.instance:
            amount = self.instance.amount

        # Check taxes input
        taxes_input = attrs.get('taxes')
        if taxes_input is None and self.instance and self.instance.taxes:
            taxes_input = self.instance.taxes

        # If taxes list not provided or empty, fallback to legacy tax_percent_used / tax_category
        if not taxes_input:
            tax_category = attrs.get('tax_category')
            if not tax_category and self.instance:
                tax_category = self.instance.tax_category
            if not tax_category:
                tax_category = 'exclusive'

            tax_percent = attrs.get('tax_percent_used')
            if tax_percent is None and self.instance:
                tax_percent = self.instance.tax_percent_used

            if tax_percent is not None and tax_percent > Decimal('0'):
                taxes_input = [{
                    'id': 1,
                    'name': f"{tax_percent}% {'Incl' if tax_category == 'inclusive' else 'Excl'}",
                    'rate': float(tax_percent),
                    'category': tax_category,
                }]

        if taxes_input and isinstance(taxes_input, list) and amount is not None:
            clean_taxes = []
            inclusive_taxes = []
            exclusive_taxes = []
            total_inc_rate = Decimal('0')
            total_exc_rate = Decimal('0')

            for idx, t in enumerate(taxes_input, 1):
                if not isinstance(t, dict):
                    continue
                try:
                    rate = Decimal(str(t.get('rate', 0)))
                except (InvalidOperation, TypeError, ValueError):
                    rate = Decimal('0')
                if rate <= Decimal('0'):
                    continue

                cat = str(t.get('category') or 'exclusive').strip().lower()
                if cat not in ('inclusive', 'exclusive'):
                    cat = 'exclusive'

                name = str(t.get('name') or '').strip()
                tax_entry = {
                    'id': t.get('id') or idx,
                    'name': name or f"{rate}% {'Incl' if cat == 'inclusive' else 'Excl'}",
                    'rate': float(rate),
                    'category': cat,
                }
                clean_taxes.append(tax_entry)
                if cat == 'inclusive':
                    inclusive_taxes.append((tax_entry, rate))
                    total_inc_rate += rate
                else:
                    exclusive_taxes.append((tax_entry, rate))
                    total_exc_rate += rate

            if clean_taxes:
                # Settle base amount and tax amounts
                if total_inc_rate > Decimal('0'):
                    base_amount = (amount / (Decimal('1') + (total_inc_rate / Decimal('100')))).quantize(Decimal('0.01'))
                    total_inclusive_tax = (amount - base_amount).quantize(Decimal('0.01'))

                    # Allocate across inclusive tax items
                    running_inc = Decimal('0')
                    for i, (item, rate) in enumerate(inclusive_taxes):
                        if i == len(inclusive_taxes) - 1:
                            t_amt = total_inclusive_tax - running_inc
                        else:
                            t_amt = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                            running_inc += t_amt
                        item['amount'] = float(t_amt)
                else:
                    base_amount = amount
                    total_inclusive_tax = Decimal('0.00')

                total_exclusive_tax = Decimal('0.00')
                for item, rate in exclusive_taxes:
                    t_amt = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                    item['amount'] = float(t_amt)
                    total_exclusive_tax += t_amt

                total_tax_amount = total_inclusive_tax + total_exclusive_tax

                if len(inclusive_taxes) > 0 and len(exclusive_taxes) > 0:
                    overall_category = 'mixed'
                elif len(inclusive_taxes) > 0:
                    overall_category = 'inclusive'
                else:
                    overall_category = 'exclusive'

                attrs['amount'] = base_amount
                attrs['taxes'] = clean_taxes
                attrs['number_of_taxes'] = len(clean_taxes)
                attrs['number_of_exclusive'] = len(exclusive_taxes)
                attrs['number_of_inclusive_tax'] = len(inclusive_taxes)
                attrs['exclusive_tax_amount'] = total_exclusive_tax
                attrs['inclusive_tax_amount'] = total_inclusive_tax
                attrs['tax_amount'] = total_tax_amount
                attrs['tax_category'] = overall_category
                attrs['tax_percent_used'] = (total_inc_rate + total_exc_rate).quantize(Decimal('0.01'))
            else:
                attrs['taxes'] = []
                attrs['number_of_taxes'] = 0
                attrs['number_of_exclusive'] = 0
                attrs['number_of_inclusive_tax'] = 0
                attrs['exclusive_tax_amount'] = Decimal('0.00')
                attrs['inclusive_tax_amount'] = Decimal('0.00')
                attrs['tax_amount'] = None
                attrs['tax_percent_used'] = None
                attrs['tax_category'] = 'exclusive'
        elif not taxes_input:
            attrs['taxes'] = []
            attrs['number_of_taxes'] = 0
            attrs['number_of_exclusive'] = 0
            attrs['number_of_inclusive_tax'] = 0
            attrs['exclusive_tax_amount'] = Decimal('0.00')
            attrs['inclusive_tax_amount'] = Decimal('0.00')
            attrs['tax_amount'] = None
            attrs['tax_percent_used'] = None

        return attrs
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.transaction:
            data['transaction'] = {
                'id': instance.transaction.id,
                'description': instance.transaction.description,
                'withdraw': instance.transaction.withdraw,
                'deposit': instance.transaction.deposit,
                'company_account': instance.transaction.company_account_id,
                'date': instance.transaction.date
            }
        else:
            data['transaction'] = None
        if instance.spare_part:
            data['spare_part'] = {
                'id': instance.spare_part.id,
                'name': instance.spare_part.name,
                'address': instance.spare_part.address,
            }
        else:
            data['spare_part'] = None
        return data
