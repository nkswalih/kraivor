from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from profiles.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = "Create Profile records for any existing Users that lack one."

    def handle(self, **options):
        users_without_profile = []
        for user in User.objects.iterator():
            if not hasattr(user, "profile") or user.profile is None:
                users_without_profile.append(user)

        if not users_without_profile:
            self.stdout.write(self.style.SUCCESS("All users already have a profile."))
            return

        created = 0
        for user in users_without_profile:
            Profile.objects.create(
                user=user,
                username=user.username or user.email.split("@")[0],
                display_name=user.name or user.email.split("@")[0],
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} profile(s) for users that lacked one.")
        )
