from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.account.models import User, TaxRate
from django.contrib.auth.password_validation import validate_password

class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = ['id', 'name', 'rate', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Tax rate cannot be negative.")
        if value > 100:
            raise serializers.ValidationError("Tax rate cannot exceed 100%.")
        return value

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'tax_rate']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=False)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'company_email', 'company_name', 'business_registration',
            'company_phone', 'company_website', 'company_address', 'tax_rate', 'password', 'password2'
        ]
        read_only_fields = ['id']

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if 'tax_rate' in data and (data['tax_rate'] == '' or data['tax_rate'] is None):
            data['tax_rate'] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        if 'tax_rate' in attrs and attrs['tax_rate'] is not None and attrs['tax_rate'] < 0:
            raise serializers.ValidationError({"tax_rate": "Tax rate cannot be negative."})
        if 'password' in attrs or 'password2' in attrs:
            if attrs.get('password') != attrs.get('password2'):
                raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('password2', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance