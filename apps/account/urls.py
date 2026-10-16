from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.account.views import LoginView, LogoutView, UserProfileView, LockPinView, TaxRateViewSet, LetterheadViewSet

router = DefaultRouter()
router.register('tax-rates', TaxRateViewSet, basename='tax-rate')
router.register('letterheads', LetterheadViewSet, basename='letterhead')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('lock-pin/', LockPinView.as_view(), name='lock-pin'),
    path('', include(router.urls)),
]
