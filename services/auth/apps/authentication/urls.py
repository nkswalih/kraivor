from django.urls import path

from .views import (
    LogoutAllView,
    LogoutView,
    OTPSendView,
    OTPVerifyView,
    RefreshTokenView,
    SignInIdentifyView,
    SignInPasswordView,
)

urlpatterns = [
    # KRV-011: Multi-step Sign In
    path("signin/identify/", SignInIdentifyView.as_view(), name="signin-identify"),
    path("signin/password/", SignInPasswordView.as_view(), name="signin-password"),
    path("signin/otp/send/", OTPSendView.as_view(), name="signin-otp-send"),
    path("signin/otp/verify/", OTPVerifyView.as_view(), name="signin-otp-verify"),
    # KRV-013: Refresh Token Rotation
    path("refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    # Logout endpoints
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout/all/", LogoutAllView.as_view(), name="logout-all"),
]
