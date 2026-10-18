from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CompanyProfile, FiscalYear, FixedAsset, StatementInput
from .pdf.i18n import LANGS
from .pdf.package import MODES, PARTS, UnknownPart, build_package
from .serializers import (CompanyProfileSerializer, FiscalYearSerializer, FixedAssetSerializer,
                          StatementInputSerializer)
from .services.inputs import normalize_inputs
from .services.package import auto_values, compute_package, public_view


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
        return Response(public_view(compute_package(request.user, self.get_object())))

    @action(detail=True, methods=['get'], url_path='auto-values')
    def auto_values(self, request, pk=None):
        """The calculated value of every overridable field, ignoring any override the user has set."""
        return Response(auto_values(request.user, self.get_object()))

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """PDF package. Query: parts (comma list), lang (ja|en), mode (full|simple)."""
        fiscal_year = self.get_object()
        parts = [p for p in request.query_params.get('parts', 'kessan').split(',') if p]
        lang = request.query_params.get('lang', 'ja')
        mode = request.query_params.get('mode', 'full')
        if not parts:
            return Response({'detail': 'parts is empty.'}, status=status.HTTP_400_BAD_REQUEST)
        if lang not in LANGS or mode not in MODES:
            return Response({'detail': f'lang must be one of {LANGS} and mode one of {MODES}.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            buffer = build_package(compute_package(request.user, fiscal_year), parts, lang, mode)
        except UnknownPart as exc:
            return Response({'detail': f'Unknown parts: {exc}. Available: {", ".join(PARTS)}'},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f'financial_statements_term{fiscal_year.term_no}_{lang}_{mode}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
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
