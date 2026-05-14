import re

from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from rest_framework import serializers

from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "name"]
        extra_kwargs = {
            "email": {"validators": [EmailValidator()]},
        }

    def validate_email(self, value):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            raise serializers.ValidationError("Invalid email format")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value.lower()

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters")
        try:
            validate_password(value)
        except serializers.ValidationError as e:
            raise serializers.ValidationError(f"Password is too weak: {', '.join(e.detail)}") from e
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # email_verified defaults to False — JWT-based verification handled in SignUpView
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar_url", "email_verified", "created_at"]
        read_only_fields = ["id", "email", "email_verified", "created_at"]
