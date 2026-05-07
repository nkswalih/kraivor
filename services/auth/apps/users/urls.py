from django.urls import path

from .views import ResendVerificationView, SignUpView, UserProfileView, VerifyEmailView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("me/", UserProfileView.as_view(), name="user-profile"),
    # KRV-010 — Email Verification
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
]