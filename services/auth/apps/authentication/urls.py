from django.urls import path

from .views import (
    OTPVerifyView,
    OTPSendView,
    SignInIdentifyView,
    SignInPasswordView,
)

urlpatterns = [
    # KRV-011: Multi-step Sign In
    path("signin/identify/", SignInIdentifyView.as_view(), name="signin-identify"),
    path("signin/password/", SignInPasswordView.as_view(), name="signin-password"),
    path("signin/otp/send/", OTPSendView.as_view(), name="signin-otp-send"),
    path("signin/otp/verify/", OTPVerifyView.as_view(), name="signin-otp-verify"),
]