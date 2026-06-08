from django.urls import path

from .password_reset_views import ForgotPasswordView, ResetPasswordView
from .views import (
    ResendVerificationView,
    ResolveUsersByIdView,
    ResolveUsersView,
    SignUpView,
    UserProfileView,
    VerifyEmailView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("me/", UserProfileView.as_view(), name="user-profile"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("internal/resolve-users/", ResolveUsersView.as_view(), name="resolve-users"),
    path("internal/resolve-users-by-id/", ResolveUsersByIdView.as_view(), name="resolve-users-by-id"),
]
