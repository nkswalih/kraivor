import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.community.models import Comment, Discussion, Vote

logger = logging.getLogger(__name__)


def _identity_endpoint(path: str) -> str:
    base = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001/api")
    if base.endswith("/api"):
        base = base[:-4]
    return f"{base}/api{path}"


class Command(BaseCommand):
    help = "Backfill discussion_count, comment_count, and reputation_score on auth profiles from core data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print stats without sending updates.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Count discussions per author (non-deleted)
        disc_counts = dict(
            Discussion.objects.filter(deleted_at__isnull=True)
            .values("author_id")
            .annotate(cnt=Count("id"))
            .values_list("author_id", "cnt")
        )

        # Count upvotes received per author (on non-deleted discussions)
        upvotes = dict(
            Vote.objects.filter(
                Q(discussion__isnull=False) & Q(value=1),
                discussion__deleted_at__isnull=True,
            )
            .values("discussion__author_id")
            .annotate(cnt=Count("id"))
            .values_list("discussion__author_id", "cnt")
        )

        # Count downvotes received per author (on non-deleted discussions)
        downvotes = dict(
            Vote.objects.filter(
                Q(discussion__isnull=False) & Q(value=-1),
                discussion__deleted_at__isnull=True,
            )
            .values("discussion__author_id")
            .annotate(cnt=Count("id"))
            .values_list("discussion__author_id", "cnt")
        )

        # Count top-level comments per author (on non-deleted discussions)
        comment_counts = dict(
            Comment.objects.filter(
                parent__isnull=True,
                discussion__deleted_at__isnull=True,
            )
            .values("author_id")
            .annotate(cnt=Count("id"))
            .values_list("author_id", "cnt")
        )

        all_author_ids = (
            set(disc_counts.keys())
            | set(upvotes.keys())
            | set(downvotes.keys())
            | set(comment_counts.keys())
        )

        if not all_author_ids:
            self.stdout.write(self.style.SUCCESS("No authors found."))
            return

        self.stdout.write(f"Found {len(all_author_ids)} author(s) to backfill...")

        header_key = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")
        endpoint = _identity_endpoint("/profiles/internal/community-event/")

        success = 0
        failed = 0

        for author_id in all_author_ids:
            author_id_str = str(author_id)
            dc = disc_counts.get(author_id, 0)
            cc = comment_counts.get(author_id, 0)
            uv = upvotes.get(author_id, 0)
            dv = downvotes.get(author_id, 0)
            rep = dc * 5 + uv * 2 - dv * 1

            self.stdout.write(
                f"  {author_id_str}: discussions={dc}, comments={cc}, upvotes={uv}, "
                f"downvotes={dv}, reputation={rep}"
            )

            if dry_run:
                continue

            try:
                resp = requests.post(
                    endpoint,
                    json={
                        "event_type": "backfill.user_stats",
                        "author_id": author_id_str,
                        "data": {
                            "discussion_count": dc,
                            "comment_count": cc,
                            "reputation_score": rep,
                        },
                    },
                    headers={header_key: "1"},
                    timeout=5,
                )
                if resp.status_code == 200:
                    success += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed for {author_id_str}: HTTP {resp.status_code}"
                        )
                    )
                    failed += 1
            except requests.exceptions.RequestException as exc:
                self.stdout.write(
                    self.style.ERROR(f"  Request failed for {author_id_str}: {exc}")
                )
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {success} succeeded, {failed} failed."
            )
        )
