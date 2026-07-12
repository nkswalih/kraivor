import logging
from django.apps import AppConfig
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authentication"

    def ready(self):
        """
        Replace the default SimpleJWT token_backend with one that
        injects 'kid' into JWT headers.

        Runs after all apps are loaded but before any request.
        """
        try:
            from authentication.backends import JWKSTokenBackend
            from rest_framework_simplejwt import state as simplejwt_state
            from rest_framework_simplejwt.settings import api_settings

            kid = getattr(django_settings, "JWT_KEY_ID", None)
            if not kid:
                logger.warning(
                    "JWT_KEY_ID not configured — tokens will lack 'kid' header"
                )
                return

            new_backend = JWKSTokenBackend(
                api_settings.ALGORITHM,
                api_settings.SIGNING_KEY,
                api_settings.VERIFYING_KEY,
                api_settings.AUDIENCE,
                api_settings.ISSUER,
                api_settings.JWK_URL,
                api_settings.LEEWAY,
                api_settings.JSON_ENCODER,
            )
            simplejwt_state.token_backend = new_backend
            logger.info(
                "token_backend replaced with kid-injecting backend (kid=%s)", kid
            )
        except Exception as exc:
            logger.error("Failed to replace token_backend: %s", exc)
