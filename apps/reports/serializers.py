from rest_framework import serializers

from .models import CompanyProfile, FiscalYear, FixedAsset, StatementInput
from .services.inputs import InputError, normalize_inputs


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        exclude = ['user', 'created_at', 'updated_at']

    def validate_corporate_number(self, value):
        if value and not (value.isdigit() and len(value) == 13):
            raise serializers.ValidationError('Corporate number must be 13 digits.')
        return value


class FiscalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalYear
        fields = ['id', 'term_no', 'start_date', 'end_date', 'status']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end <= start:
            raise serializers.ValidationError('end_date must be after start_date.')
        return attrs


class FixedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedAsset
        fields = ['id', 'fiscal_year', 'name', 'category', 'acquired_on', 'cost',
                  'method', 'useful_life', 'opening_book_value']

    def validate_fiscal_year(self, value):
        request = self.context['request']
        if value.user_id != request.user.id:
            raise serializers.ValidationError('Invalid fiscal year.')
        return value

    def validate(self, attrs):
        method = attrs.get('method', getattr(self.instance, 'method', None))
        life = attrs.get('useful_life', getattr(self.instance, 'useful_life', 0))
        if method in ('straight_line', 'declining_200') and not life:
            raise serializers.ValidationError({'useful_life': 'Enter the useful life (years) for this depreciation method.'})
        return attrs


class StatementInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatementInput
        fields = ['data']

    def validate_data(self, value):
        try:
            return normalize_inputs(value)
        except InputError as exc:
            raise serializers.ValidationError(str(exc))
