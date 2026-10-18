from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CompanyProfile, FiscalYear, FixedAsset, StatementInput
from .pdf.package import PARTS, UnknownPart, build_package
from .serializers import (CompanyProfileSerializer, FiscalYearSerializer, FixedAssetSerializer,
                          StatementInputSerializer)
from .services.inputs import normalize_inputs
from .services.statements import compute_statements


def _get_profile(user):
    """Profile for the user, pre-filled from the account's company fields on first access."""
    profile, created = CompanyProfile.objects.get_or_create(user=user)
    if created:
        profile.legal_name = user.company_name or ''
        profile.address = user.company_address or ''
        profile.phone = user.company_phone or ''
        profile.save()
    return profile


class CompanyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CompanyProfileSerializer(_get_profile(request.user)).data)

    def put(self, request):
        serializer = CompanyProfileSerializer(_get_profile(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FiscalYearViewSet(viewsets.ModelViewSet):
    serializer_class = FiscalYearSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return FiscalYear.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get', 'put'])
    def inputs(self, request, pk=None):
        fiscal_year = self.get_object()
        record, _ = StatementInput.objects.get_or_create(fiscal_year=fiscal_year)
        if request.method == 'PUT':
            serializer = StatementInputSerializer(record, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response({'data': normalize_inputs(record.data)})

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        data = compute_statements(request.user, self.get_object())
        return Response(data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        fiscal_year = self.get_object()
        parts = [p for p in request.query_params.get('parts', 'kessan').split(',') if p]
        if not parts:
            return Response({'detail': 'parts is empty.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            buffer = build_package(compute_statements(request.user, fiscal_year), parts)
        except UnknownPart as exc:
            return Response({'detail': f'Unknown parts: {exc}. Available: {", ".join(PARTS)}'},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="financial_statements_term{fiscal_year.term_no}.pdf"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class FixedAssetViewSet(viewsets.ModelViewSet):
    serializer_class = FixedAssetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = FixedAsset.objects.filter(fiscal_year__user=self.request.user)
        fiscal_year = self.request.query_params.get('fiscal_year')
        return qs.filter(fiscal_year_id=fiscal_year) if fiscal_year else qs
