"""
Management command to sync denormalized author fields (username, display_name, avatar_url)
on all existing Discussions and Comments from the auth profile service.

Usage:
    python manage.py sync_author_denormalization
"""

import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.community.models import Comment, Discussion
from apps.community.tasks import update_author_denormalization

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Sync denormalized author fields on Discussions and Comments from profile data."
    )

    def handle(self, *args, **options):
        disc_ids = set(
            Discussion.objects.values_list("author_id", flat=True).distinct()
        )
        comm_ids = set(Comment.objects.values_list("author_id", flat=True).distinct())
        all_author_ids = disc_ids | comm_ids

        if not all_author_ids:
            self.stdout.write(self.style.SUCCESS("No authors to sync."))
            return

        self.stdout.write(f"Found {len(all_author_ids)} unique author(s) to sync...")

        identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
        endpoint = f"{identity_url}/api/profiles/internal/resolve-by-id/"
        header = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")

        for author_id in all_author_ids:
            try:
                resp = requests.post(
                    endpoint,
                    json={"user_ids": [str(author_id)]},
                    headers={header: "1"},
                    timeout=5,
                )
                if resp.status_code == 200:
                    profiles = resp.json().get("profiles", {})
                    profile = profiles.get(str(author_id))
                    if profile:
                        update_author_denormalization.delay(
                            str(author_id),
                            profile["username"],
                            profile["display_name"],
                            profile["avatar_url"],
                        )
                        self.stdout.write(f"  Queued sync for author {author_id}")
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  No profile found for author {author_id}"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to resolve author {author_id}: HTTP {resp.status_code}"
                        )
                    )
            except requests.exceptions.RequestException as exc:
                self.stdout.write(
                    self.style.ERROR(f"  Request failed for author {author_id}: {exc}")
                )

        self.stdout.write(
            self.style.SUCCESS("Done. Celery workers will process the sync tasks.")
        )
