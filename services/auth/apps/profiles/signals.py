import re
import secrets

from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from profiles.models import Profile, UserFollow

USER_MODEL = "users.User"


@receiver(post_save, sender=USER_MODEL)
def create_profile_on_registration(sender, instance, created, **kwargs):
    if not created:
        return
    if Profile.objects.filter(user=instance).exists():  # pragma: no cover
        return
    username = _generate_unique_username(instance)
    Profile.objects.create(
        user=instance,
        username=username,
        display_name=instance.name or instance.email.split("@")[0],
    )


@receiver(post_save, sender=UserFollow)
def increment_follow_counters(sender, instance, created, **kwargs):
    if not created:  # pragma: no cover
        return
    Profile.objects.filter(user=instance.follower).update(
        following_count=F("following_count") + 1
    )
    Profile.objects.filter(user=instance.following).update(
        followers_count=F("followers_count") + 1
    )


@receiver(post_delete, sender=UserFollow)
def decrement_follow_counters(sender, instance, **kwargs):
    Profile.objects.filter(
        user=instance.follower, following_count__gt=0
    ).update(following_count=F("following_count") - 1)
    Profile.objects.filter(
        user=instance.following, followers_count__gt=0
    ).update(followers_count=F("followers_count") - 1)


def _generate_unique_username(user) -> str:
    base = re.sub(r"[^a-z0-9_]", "", user.email.split("@")[0].lower())[:40] or "user"
    candidate = base
    for _ in range(10):
        if not Profile.objects.filter(username=candidate).exists():
            return candidate
        candidate = f"{base}_{secrets.token_hex(2)}"
    return f"user_{secrets.token_hex(4)}"  # pragma: no cover
