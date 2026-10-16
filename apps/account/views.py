import re
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import action
from apps.account.serializers import LoginSerializer, UserSerializer, TaxRateSerializer, LetterheadSerializer
from apps.account.models import TaxRate, Letterhead
from apps.account.letterhead_generator import generate_letterhead_docx
from rest_framework import generics, permissions, viewsets
from django.contrib.auth.hashers import make_password, check_password
from .serializers import UserProfileSerializer

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })

class LogoutView(APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Return the current logged-in user
        return self.request.user

class LockPinView(APIView):
    """Set/remove (PUT/DELETE, both need the account password) or verify (POST) the screen-lock PIN."""
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        pin = str(request.data.get('pin', ''))
        if not (pin.isascii() and pin.isdigit() and len(pin) == 6):
            return Response({'error': 'PIN must be exactly 6 digits.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(str(request.data.get('password', ''))):
            return Response({'error': 'Password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.lock_pin = make_password(pin)
        request.user.save(update_fields=['lock_pin'])
        return Response({'has_lock_pin': True})

    def delete(self, request):
        if not request.user.check_password(str(request.data.get('password', ''))):
            return Response({'error': 'Password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.lock_pin = ''
        request.user.save(update_fields=['lock_pin'])
        return Response({'has_lock_pin': False})

    def post(self, request):
        stored = request.user.lock_pin
        if not stored:
            return Response({'error': 'No PIN is set.'}, status=status.HTTP_400_BAD_REQUEST)
        if not check_password(str(request.data.get('pin', '')), stored):
            return Response({'error': 'Incorrect PIN.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True})

class TaxRateViewSet(viewsets.ModelViewSet):
    serializer_class = TaxRateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaxRate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LetterheadViewSet(viewsets.ModelViewSet):
    serializer_class = LetterheadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Letterhead.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='export-docx')
    def export_docx_preview(self, request):
        """
        Export an editable Word (.docx) letterhead directly from the provided
        custom design payload (without needing to save first).
        """
        data = request.data or {}
        docx_buffer = generate_letterhead_docx(data)
        company_name = data.get('name') or data.get('companyName') or 'Company'
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', company_name).strip('_') or 'Letterhead'
        filename = f"{clean_name}_Letterhead.docx"

        response = HttpResponse(
            docx_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @action(detail=True, methods=['get', 'post'], url_path='export-docx')
    def export_docx(self, request, pk=None):
        """
        Export a saved letterhead design as an editable Word (.docx) document.
        """
        letterhead = self.get_object()
        docx_buffer = generate_letterhead_docx(letterhead)
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', letterhead.name or 'Company').strip('_') or 'Letterhead'
        filename = f"{clean_name}_Letterhead.docx"

        response = HttpResponse(
            docx_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
