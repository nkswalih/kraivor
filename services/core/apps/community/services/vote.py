from django.db.models import F, Q

from ..models import Comment, Discussion, Vote


class VoteService:
    @staticmethod
    def vote_discussion(
        discussion: Discussion, user_id: str, value: int
    ) -> tuple[Vote, str]:
        existing = Vote.objects.filter(user_id=user_id, discussion=discussion).first()
        if existing:
            if existing.value == value:
                return existing, "no_change"
            old_value = existing.value
            existing.value = value
            existing.save(update_fields=["value"])
            delta = value - old_value
            if delta > 0:
                Discussion.objects.filter(id=discussion.id).update(
                    upvote_count=F("upvote_count") + 1,
                    downvote_count=F("downvote_count") - 1,
                )
            else:
                Discussion.objects.filter(id=discussion.id).update(
                    upvote_count=F("upvote_count") - 1,
                    downvote_count=F("downvote_count") + 1,
                )
            return existing, "changed"
        vote = Vote.objects.create(user_id=user_id, discussion=discussion, value=value)
        if value == 1:
            Discussion.objects.filter(id=discussion.id).update(
                upvote_count=F("upvote_count") + 1
            )
        else:
            Discussion.objects.filter(id=discussion.id).update(
                downvote_count=F("downvote_count") + 1
            )
        return vote, "created"

    @staticmethod
    def remove_discussion_vote(discussion: Discussion, user_id: str) -> bool:
        vote = Vote.objects.filter(user_id=user_id, discussion=discussion).first()
        if not vote:
            return False
        was_upvote = vote.value == 1
        vote.delete()
        if was_upvote:
            Discussion.objects.filter(id=discussion.id).update(
                upvote_count=F("upvote_count") - 1
            )
        else:
            Discussion.objects.filter(id=discussion.id).update(
                downvote_count=F("downvote_count") - 1
            )
        return True

    @staticmethod
    def vote_comment(comment: Comment, user_id: str, value: int) -> tuple[Vote, str]:
        existing = Vote.objects.filter(user_id=user_id, comment=comment).first()
        if existing:
            if existing.value == value:
                return existing, "no_change"
            old_value = existing.value
            existing.value = value
            existing.save(update_fields=["value"])
            delta = value - old_value
            if delta > 0:
                Comment.objects.filter(id=comment.id).update(
                    upvote_count=F("upvote_count") + 1,
                    downvote_count=F("downvote_count") - 1,
                )
            else:
                Comment.objects.filter(id=comment.id).update(
                    upvote_count=F("upvote_count") - 1,
                    downvote_count=F("downvote_count") + 1,
                )
            return existing, "changed"
        vote = Vote.objects.create(user_id=user_id, comment=comment, value=value)
        if value == 1:
            Comment.objects.filter(id=comment.id).update(
                upvote_count=F("upvote_count") + 1
            )
        else:
            Comment.objects.filter(id=comment.id).update(
                downvote_count=F("downvote_count") + 1
            )
        return vote, "created"

    @staticmethod
    def remove_comment_vote(comment: Comment, user_id: str) -> bool:
        vote = Vote.objects.filter(user_id=user_id, comment=comment).first()
        if not vote:
            return False
        was_upvote = vote.value == 1
        vote.delete()
        if was_upvote:
            Comment.objects.filter(id=comment.id).update(
                upvote_count=F("upvote_count") - 1
            )
        else:
            Comment.objects.filter(id=comment.id).update(
                downvote_count=F("downvote_count") - 1
            )
        return True

    @staticmethod
    def get_user_votes(
        user_id: str,
        discussion_ids: list | None = None,
        comment_ids: list | None = None,
    ) -> dict:
        q = Q(user_id=user_id)
        if discussion_ids:
            q &= Q(discussion_id__in=discussion_ids)
        elif comment_ids:
            q &= Q(comment_id__in=comment_ids)
        return {
            str(v.discussion_id or v.comment_id): v.value
            for v in Vote.objects.filter(q)
        }
