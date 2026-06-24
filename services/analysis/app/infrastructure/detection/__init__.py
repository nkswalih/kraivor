from app.infrastructure.detection.models import DetectionResult, DetectedTechnology


def get_detector() -> "FrameworkDetector":
    from app.infrastructure.detection.detector import FrameworkDetector
    return FrameworkDetector()


__all__ = [
    "DetectionResult",
    "DetectedTechnology",
    "get_detector",
]

