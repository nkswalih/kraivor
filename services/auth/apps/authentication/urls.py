from authentication.oauth.google.views import (
    GoogleOAuthCallbackView,
    GoogleOAuthInitiateView,
)
from django.urls import path

from .oauth.views import (
    GitHubConnectView,
    GitHubOAuthCallbackView,
    GitHubOAuthInitiateView,
)
from .views import (
    LogoutAllView,
    LogoutView,
    OTPSendView,
    OTPVerifyView,
    RefreshTokenView,
    SessionListView,
    SessionRevokeAllView,
    SessionRevokeView,
    SignInIdentifyView,
    SignInPasswordView,
    SignOutView,
)

urlpatterns = [
    # KRV-011: Multi-step Sign In
    path("signin/identify/", SignInIdentifyView.as_view(), name="signin-identify"),
    path("signin/password/", SignInPasswordView.as_view(), name="signin-password"),
    path("signin/otp/send/", OTPSendView.as_view(), name="signin-otp-send"),
    path("signin/otp/verify/", OTPVerifyView.as_view(), name="signin-otp-verify"),
    # KRV-013: Refresh Token Rotation
    path("refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    # Legacy logout (keep for backwards compat)
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout/all/", LogoutAllView.as_view(), name="logout-all"),
    # KRV-014: Sign Out & Session Management
    path("signout/", SignOutView.as_view(), name="signout"),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/all/", SessionRevokeAllView.as_view(), name="session-revoke-all"),
    path(
        "sessions/<uuid:session_id>/",
        SessionRevokeView.as_view(),
        name="session-revoke",
    ),
    # KRV-015: GitHub OAuth
    path(
        "oauth/github/", GitHubOAuthInitiateView.as_view(), name="github-oauth-initiate"
    ),
    path(
        "oauth/github/callback/",
        GitHubOAuthCallbackView.as_view(),
        name="github-oauth-callback",
    ),
    path("oauth/github/connect/", GitHubConnectView.as_view(), name="github-connect"),
    # KRV-016 — Google OAuth
    path(
        "oauth/google/", GoogleOAuthInitiateView.as_view(), name="google-oauth-initiate"
    ),
    path(
        "oauth/google/callback/",
        GoogleOAuthCallbackView.as_view(),
        name="google-oauth-callback",
    ),
]
