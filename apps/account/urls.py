from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.account.views import LoginView, LogoutView, UserProfileView, TaxRateViewSet

router = DefaultRouter()
router.register('tax-rates', TaxRateViewSet, basename='tax-rate')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('', include(router.urls)),
]
