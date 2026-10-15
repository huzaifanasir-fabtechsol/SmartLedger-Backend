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
    tax_percent_used = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    tax_category = serializers.CharField(required=False, default='exclusive')
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'description', 'date', 'category', 'category_name',
            'transaction', 'restaurant', 'restaurant_name', 'spare_part', 'spare_part_name',
            'is_cash', 'is_highlighted', 'tax_category', 'tax_percent_used', 'tax_amount', 'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_amount']

    def validate(self, attrs):
        from decimal import Decimal
        category = attrs.get('category')
        if not category and self.instance:
            category = self.instance.category

        spare_part = attrs.get('spare_part')
        if spare_part is None and self.instance:
            spare_part = self.instance.spare_part

        is_spare_parts = bool(category and category.name and category.name.strip().upper() == 'SPARE PARTS')
        if not is_spare_parts:
            attrs['spare_part'] = None

        # Settle tax and base amount if tax_amount not explicitly provided but tax percent is present
        tax_category = attrs.get('tax_category')
        if not tax_category and self.instance:
            tax_category = self.instance.tax_category
        if not tax_category:
            tax_category = 'exclusive'

        tax_percent = attrs.get('tax_percent_used')
        if tax_percent is None and self.instance:
            tax_percent = self.instance.tax_percent_used

        amount = attrs.get('amount')
        if amount is None and self.instance:
            amount = self.instance.amount

        # If tax_amount was not pre-calculated and tax_percent is set > 0
        if attrs.get('tax_amount') is None and tax_percent is not None and tax_percent > Decimal('0') and amount is not None:
            if tax_category == 'inclusive':
                base_amount = (amount / (Decimal('1') + (tax_percent / Decimal('100')))).quantize(Decimal('0.01'))
                tax_amount = (amount - base_amount).quantize(Decimal('0.01'))
                attrs['amount'] = base_amount
                attrs['tax_amount'] = tax_amount
            else:
                tax_amount = (amount * (tax_percent / Decimal('100'))).quantize(Decimal('0.01'))
                attrs['tax_amount'] = tax_amount
        elif tax_percent is None or tax_percent == Decimal('0'):
            # If no tax rate applied
            if 'tax_amount' not in attrs or attrs['tax_amount'] is None:
                attrs['tax_amount'] = None

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
