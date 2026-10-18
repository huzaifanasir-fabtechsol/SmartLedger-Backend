from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyProfileView, FiscalYearViewSet, FixedAssetViewSet

router = DefaultRouter()
router.register('fiscal-years', FiscalYearViewSet, basename='fiscal-year')
router.register('fixed-assets', FixedAssetViewSet, basename='fixed-asset')

urlpatterns = [
    path('company-profile/', CompanyProfileView.as_view(), name='company-profile'),
    path('', include(router.urls)),
]
