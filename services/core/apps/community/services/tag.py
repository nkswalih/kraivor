from ..models import Tag


class TagService:
    @staticmethod
    def get_popular_tags(limit: int = 20) -> list[Tag]:
        return list(Tag.objects.order_by("-usage_count")[:limit])

    @staticmethod
    def search_tags(query: str, limit: int = 10) -> list[Tag]:
        return list(
            Tag.objects.filter(name__icontains=query).order_by("-usage_count")[:limit]
        )
