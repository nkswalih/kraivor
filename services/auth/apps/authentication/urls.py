from django.urls import path

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
     # ── Legacy logout (keep for backwards compat) ─────────────────────────────
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout/all/", LogoutAllView.as_view(), name="logout-all"),
 
    # ── KRV-014: Sign Out & Session Management ────────────────────────────────
    # POST   /api/auth/signout/              — revoke cookie token, no JWT needed
    # GET    /api/auth/sessions/             — list active sessions
    # DELETE /api/auth/sessions/all/         — revoke all sessions
    # DELETE /api/auth/sessions/<id>/        — revoke one session
    #
    # IMPORTANT: sessions/all/ must come BEFORE sessions/<session_id>/
    # Otherwise Django matches "all" as a UUID and returns a 404.
    path("signout/", SignOutView.as_view(), name="signout"),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/all/", SessionRevokeAllView.as_view(), name="session-revoke-all"),
    path("sessions/<uuid:session_id>/", SessionRevokeView.as_view(), name="session-revoke"),
    
]
