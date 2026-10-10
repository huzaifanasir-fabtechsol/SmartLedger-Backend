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

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'description', 'date', 'category', 'category_name',
            'transaction', 'restaurant', 'restaurant_name', 'spare_part', 'spare_part_name',
            'is_cash', 'tax_percent_used', 'tax_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        category = attrs.get('category')
        if not category and self.instance:
            category = self.instance.category

        spare_part = attrs.get('spare_part')
        if spare_part is None and self.instance:
            spare_part = self.instance.spare_part

        is_spare_parts = bool(category and category.name and category.name.strip().upper() == 'SPARE PARTS')
        # if is_spare_parts and not spare_part:
        #     raise serializers.ValidationError({'spare_part': 'Shop is required when category is SPARE PARTS.'})
        if not is_spare_parts:
            attrs['spare_part'] = None
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
