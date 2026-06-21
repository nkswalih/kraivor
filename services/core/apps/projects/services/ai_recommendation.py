logger = __import__("logging").getLogger(__name__)


class AIRecommendationService:
    @staticmethod
    def suggest_tasks_from_description(project_id: str, description: str) -> list:
        return []

    @staticmethod
    def estimate_story_points(task_id: str) -> int | None:
        return None

    @staticmethod
    def detect_blocked_tasks(project_id: str) -> list:
        return []

    @staticmethod
    def suggest_dependencies(task_id: str) -> list:
        return []
