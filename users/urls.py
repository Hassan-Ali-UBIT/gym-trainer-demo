# urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,     # refresh
)
from .views import (
    RegisterView, LoginView, GenerateOTPView, VerifyOTPView,
    ChangePasswordView, GetUpdateUserView,
    ResetPasswordView, CustomTokenObtainPairView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login-refresh'),
    path('django-login/', LoginView.as_view(), name='django-login'),
    path('otp/', GenerateOTPView.as_view(), name='generate-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('me/', GetUpdateUserView.as_view(), name='get-update-user'),
]

