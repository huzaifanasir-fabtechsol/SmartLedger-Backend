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
from .services.package import auto_values, compute_package, public_view, roll_forward

CONTENT_TYPES = {
    'pdf': 'application/pdf',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


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

    @action(detail=True, methods=['post'], url_path='roll-forward')
    def roll_forward(self, request, pk=None):
        """Start the next term from this term's closing balances."""
        try:
            new_year = roll_forward(request.user, self.get_object())
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FiscalYearSerializer(new_year).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='auto-values')
    def auto_values(self, request, pk=None):
        """The calculated value of every overridable field, ignoring any override the user has set."""
        return Response(auto_values(request.user, self.get_object()))

    def _package_file(self, request, output):
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
            buffer = build_package(compute_package(request.user, fiscal_year), parts, lang, mode, output)
        except UnknownPart as exc:
            return Response({'detail': f'Unknown parts: {exc}. Available: {", ".join(PARTS)}'},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(buffer.getvalue(), content_type=CONTENT_TYPES[output])
        filename = f'financial_statements_term{fiscal_year.term_no}_{lang}_{mode}.{output}'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """PDF package. Query: parts (comma list), lang (ja|en), mode (full|simple)."""
        return self._package_file(request, 'pdf')

    @action(detail=True, methods=['get'])
    def xlsx(self, request, pk=None):
        """Same package as an Excel workbook (one sheet per form). Same query as ``pdf``."""
        return self._package_file(request, 'xlsx')


class FixedAssetViewSet(viewsets.ModelViewSet):
    serializer_class = FixedAssetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = FixedAsset.objects.filter(fiscal_year__user=self.request.user)
        fiscal_year = self.request.query_params.get('fiscal_year')
        return qs.filter(fiscal_year_id=fiscal_year) if fiscal_year else qs
