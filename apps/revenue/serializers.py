from rest_framework import serializers
from apps.revenue.models import Car, CarCategory, Order, OrderItem, Customer, Saler, CompanyAccount, Auction, Transaction

class CarCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCategory
        fields = ['id', 'company', 'model', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class CarSerializer(serializers.ModelSerializer):
    category_company = serializers.CharField(source='category.company', read_only=True)
    category_model = serializers.CharField(source='category.model', read_only=True)
    
    class Meta:
        model = Car
        fields = ['id', 'category', 'category_company', 'category_model', 'description', 'chassis_number', 'year', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class OrderItemSerializer(serializers.ModelSerializer):
    car_company = serializers.CharField(source='car.category.company', read_only=True)
    car_model = serializers.CharField(source='car.category.model', read_only=True)
    chassis_number = serializers.CharField(source='car.chassis_number', read_only=True)
    year = serializers.IntegerField(source='car.year', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'car', 'car_company', 'car_model', 'car_category', 'chassis_number', 'year', 'venue', 'notes',
                  'vehicle_price', 'vehicle_price_tax', 'recycle_fee',
                  'listing_fee', 'listing_fee_tax', 'successful_bid', 'successful_bid_tax',
                  'commission_fee', 'commission_fee_tax', 'transport_fee', 'transport_fee_tax',
                  'registration_fee', 'registration_fee_tax', 'canceling_fee',
                  'subtotal']
        read_only_fields = ['subtotal']

class OrderItemCreateSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=200)
    model = serializers.CharField(max_length=100)
    chassis_number = serializers.CharField(max_length=50)
    year = serializers.IntegerField()
    venue = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # New fields - all optional
    vehicle_price = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, required=False)
    vehicle_price_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    recycle_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    listing_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    listing_fee_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    successful_bid = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, required=False)
    successful_bid_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    commission_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    commission_fee_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    transport_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    transport_fee_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    registration_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    registration_fee_tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    canceling_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, required=False)
    
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    auction_name = serializers.CharField(source='auction.name', read_only=True)
    customer_name_obj = serializers.CharField(source='customer.name', read_only=True)
    saler_name_obj = serializers.CharField(source='saler.name', read_only=True)
    company_account_name = serializers.CharField(source='company_account.bank_name', read_only=True)
    transaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'transaction_type', 'transaction_catagory', 'transaction_date', 'payment_status', 'customer_name', 
                  'total_amount', 'notes', 'items', 'other_details', 'auction', 'auction_name', 
                  'customer', 'customer_name_obj', 'saler', 'saler_name_obj', 'company_account', 'company_account_name',
                  'transaction', 'created_at', 'updated_at']
        read_only_fields = ['order_number', 'created_at', 'updated_at']
    
    def get_transaction(self, obj):
        if obj.transaction:
            return {
                'id': obj.transaction.id,
                'description': obj.transaction.description,
                'withdraw': obj.transaction.withdraw,
                'date': obj.transaction.date
            }
        return None


# ----------------- Create Order -----------------
class CreateOrderSerializer(serializers.Serializer):
    transaction_type = serializers.ChoiceField(choices=['purchase', 'sale', 'auction', 'nagare'])
    transaction_catagory = serializers.ChoiceField(choices=['local', 'foreign'])
    payment_status = serializers.ChoiceField(choices=['pending', 'completed', 'failed'])
    transaction_date = serializers.DateField()
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    saler_id = serializers.IntegerField(required=False, allow_null=True)
    company_account_id = serializers.IntegerField(required=False, allow_null=True)
    auction_id = serializers.IntegerField(required=False, allow_null=True)
    transaction = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    saler_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    seller_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    auction_house = serializers.CharField(max_length=200, required=False, allow_blank=True)
    payment_method = serializers.CharField(max_length=100, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemCreateSerializer(many=True)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'address', 'phone', 'account_number', 'branch_code', 'bank_name', 'swift_code', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class SalerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Saler
        fields = ['id', 'name', 'email', 'address', 'phone', 'account_number', 'branch_code', 'bank_name', 'swift_code', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class CompanyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyAccount
        fields = ['id', 'bank_name', 'account_number', 'branch_code', 'account_holder', 'swift_code', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class AuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    company_account_name = serializers.CharField(source='company_account.bank_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'date', 'transaction_id', 'withdraw', 'deposit', 'balance', 'description', 'notes', 'company_account', 'company_account_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'balance']
