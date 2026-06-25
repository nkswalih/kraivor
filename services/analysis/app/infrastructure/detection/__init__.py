from app.infrastructure.detection.models import DetectedTechnology, DetectionResult


def get_detector():
    from app.infrastructure.detection.detector import FrameworkDetector
    return FrameworkDetector()


__all__ = [
    "DetectedTechnology",
    "DetectionResult",
    "get_detector",
]

