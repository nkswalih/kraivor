from rest_framework import serializers


class SignInIdentifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class SignInPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    device_id = serializers.CharField(required=False, allow_blank=True)


class OTPSendSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)
    device_id = serializers.CharField(required=False, allow_blank=True)
