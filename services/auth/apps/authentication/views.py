"""
Sign-in views for KRV-011.

Multi-step authentication flow:
1. POST /signin/identify - Email only, returns next step
2. POST /signin/password - Password verification
3. POST /signin/otp/send - Send OTP to email
4. POST /signin/otp/verify - Verify OTP and return tokens

Returns:
- access_token: In JSON response (store in memory)
- refresh_token: HttpOnly cookie (30-day persist)
"""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .otp import (
    OTPRateLimitError,
    OTPInvalidError,
    OTPExpiredError,
    get_otp_service,
    get_otp_sender,
)
from .security import (
    LoginLockoutError,
    check_password as verify_password,
    get_client_ip,
    get_lockout_manager,
    generate_device_id,
)
from .serializers import (
    OTPVerifySerializer,
    OTPSendSerializer,
    SignInIdentifySerializer,
    SignInPasswordSerializer,
)
from .jwt import generate_token_pair, create_refresh_cookie

from apps.users.models import User

logger = logging.getLogger(__name__)


def log_login_event(user, ip, user_agent, device_id, success: bool, method: str):
    """Log login event for audit trail."""
    logger.info(
        f"Login event: user={user.email}, ip={ip}, device_id={device_id}, "
        f"method={method}, success={success}, timestamp={timezone.now().isoformat()}"
    )


class SignInIdentifyView(APIView):
    """
    POST /api/auth/signin/identify
    
    Step 1: Email only - determines next authentication method.
    
    Request:
        {"email": "user@example.com"}
    
    Response (user exists + verified):
        {
            "next_step": "password",
            "user_exists": true,
            "email_verified": true,
            "methods": ["password", "otp"]
        }
    
    Response (user exists + NOT verified):
        {
            "next_step": "verify_email",
            "user_exists": true,
            "email_verified": false,
            "message": "Please verify your email first"
        }
    
    Response (user doesn't exist):
        {
            "next_step": "signup",
            "user_exists": false,
            "email_verified": false
        }
    
    Locked account:
        429 Too Many Requests, retry_after header
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignInIdentifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].lower()
        ip = get_client_ip(request)

        # Check lockout
        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)
        
        if is_locked:
            response = Response(
                {
                    "error": "Too many failed attempts. Account temporarily locked.",
                    "error_code": "account_locked",
                    "retry_after": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_after)
            return response

        # Check if user exists
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            user_exists = True
            email_verified = user.email_verified
        except User.DoesNotExist:
            # Don't reveal whether user exists (prevents enumeration)
            user_exists = False
            email_verified = False

        if not user_exists:
            return Response(
                {
                    "next_step": "signup",
                    "user_exists": False,
                    "email_verified": False,
                }
            )

        if not email_verified:
            return Response(
                {
                    "next_step": "verify_email",
                    "user_exists": True,
                    "email_verified": False,
                    "message": "Please verify your email first",
                }
            )

        # User exists and verified - continue to password or OTP
        return Response(
            {
                "next_step": "choose_method",
                "user_exists": True,
                "email_verified": True,
                "methods": ["password", "otp"],
            }
        )


class SignInPasswordView(APIView):
    """
    POST /api/auth/signin/password
    
    Step 2: Password verification.
    
    Request:
        {"email": "user@example.com", "password": "secret123", "device_id": ""}
    
    Response (success):
        {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",  # only for programmatic clients
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {"id": "uuid", "email": "...", "name": "..."}
        }
    
    Response (failure):
        401 Unauthorized, {"error": "Invalid credentials", "error_code": "invalid_credentials"}
    
    Locked account:
        429 Too Many Requests, retry_after header
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignInPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        device_id = serializer.validated_data.get('device_id') or generate_device_id(request)
        
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Check lockout first (fail fast)
        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)
        
        if is_locked:
            response = Response(
                {
                    "error": "Too many failed attempts. Account temporarily locked.",
                    "error_code": "account_locked",
                    "retry_after": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_after)
            return response

        # Get user
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Same response as wrong password (prevents enumeration)
            return Response(
                {"error": "Invalid credentials", "error_code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Verify password (Django already uses constant-time comparison)
        if not verify_password(password, user.password):
            # Record failure
            failed_attempts = lockout_mgr.record_failure(email, ip)
            
            log_login_event(
                user=user,
                ip=ip,
                user_agent=user_agent,
                device_id=device_id,
                success=False,
                method="password",
            )
            
            return Response(
                {"error": "Invalid credentials", "error_code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Success - clear lockout attempts
        lockout_mgr.clear_attempts(email, ip)

        # Generate tokens
        tokens = generate_token_pair(user, device_id, ip, user_agent)
        
        # Create refresh cookie
        refresh_cookie = create_refresh_cookie(tokens['refresh_token'])

        # Log successful login
        log_login_event(
            user=user,
            ip=ip,
            user_agent=user_agent,
            device_id=device_id,
            success=True,
            method="password",
        )

        response = Response(
            {
                "access_token": tokens['access_token'],
                "token_type": tokens['token_type'],
                "expires_in": tokens['expires_in'],
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                },
            },
            status=status.HTTP_200_OK,
        )

        # Set refresh token cookie
        response.set_cookie(
            'refresh_token',
            refresh_cookie['refresh_token'],
            httponly=refresh_cookie['httponly'],
            secure=refresh_cookie['secure'],
            samesite=refresh_cookie['samesite'],
            path=refresh_cookie['path'],
            max_age=refresh_cookie['max_age'],
        )

        return response


class OTPSendView(APIView):
    """
    POST /api/auth/signin/otp/send
    
    Send OTP to user's email for verification.
    
    Request:
        {"email": "user@example.com"}
    
    Response:
        {"message": "OTP sent to your email"}
    
    Rate limited:
        429 Too Many Requests
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].lower()
        ip = get_client_ip(request)

        # Check lockout
        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)
        
        if is_locked:
            response = Response(
                {
                    "error": "Too many failed attempts. Account temporarily locked.",
                    "error_code": "account_locked",
                    "retry_after": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_after)
            return response

        # Check if user exists and verified
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials", "error_code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.email_verified:
            return Response(
                {"error": "Please verify your email first", "error_code": "email_not_verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate and send OTP
        otp_service = get_otp_service()
        
        try:
            otp, _ = otp_service.create_and_send(email)
        except OTPRateLimitError as e:
            response = Response(
                {
                    "error": "Too many OTP requests. Please wait before trying again.",
                    "error_code": "rate_limit_exceeded",
                    "retry_after": e.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(e.retry_after)
            return response

        # Send OTP via email
        otp_sender = get_otp_sender()
        try:
            otp_sender.send(email, otp)
        except Exception:
            logger.exception(f"Failed to send OTP to {email}")

        logger.info(f"OTP sent to {email} for sign-in")

        return Response(
            {"message": "OTP sent to your email"},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    """
    POST /api/auth/signin/otp/verify
    
    Verify OTP and return tokens.
    
    Request:
        {"email": "user@example.com", "otp_code": "123456", "device_id": ""}
    
    Response (success):
        Same as password sign-in
    
    Response (failure):
        401 Unauthorized, error code depends on failure reason
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].lower()
        otp_code = serializer.validated_data['otp_code']
        device_id = serializer.validated_data.get('device_id') or generate_device_id(request)
        
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Check lockout
        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)
        
        if is_locked:
            response = Response(
                {
                    "error": "Too many failed attempts. Account temporarily locked.",
                    "error_code": "account_locked",
                    "retry_after": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_after)
            return response

        # Get user
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials", "error_code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Verify OTP
        otp_service = get_otp_service()
        
        try:
            otp_service.verify_otp(email, otp_code)
        except OTPExpiredError:
            lockout_mgr.record_failure(email, ip)
            return Response(
                {"error": "OTP has expired. Please request a new one.", "error_code": "otp_expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except OTPInvalidError as e:
            lockout_mgr.record_failure(email, ip)
            return Response(
                {"error": str(e), "error_code": "invalid_otp"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Success - clear lockout
        lockout_mgr.clear_attempts(email, ip)

        # Generate tokens
        tokens = generate_token_pair(user, device_id, ip, user_agent)
        
        # Create refresh cookie
        refresh_cookie = create_refresh_cookie(tokens['refresh_token'])

        # Log successful login
        log_login_event(
            user=user,
            ip=ip,
            user_agent=user_agent,
            device_id=device_id,
            success=True,
            method="otp",
        )

        response = Response(
            {
                "access_token": tokens['access_token'],
                "token_type": tokens['token_type'],
                "expires_in": tokens['expires_in'],
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                },
            },
            status=status.HTTP_200_OK,
        )

        # Set refresh token cookie
        response.set_cookie(
            'refresh_token',
            refresh_cookie['refresh_token'],
            httponly=refresh_cookie['httponly'],
            secure=refresh_cookie['secure'],
            samesite=refresh_cookie['samesite'],
            path=refresh_cookie['path'],
            max_age=refresh_cookie['max_age'],
        )

        return response