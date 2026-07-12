from app.infrastructure.detection.detector import FrameworkDetector
from app.infrastructure.detection.models import DetectedTechnology, DetectionResult


def get_detector() -> FrameworkDetector:
    return FrameworkDetector()


__all__ = ["DetectedTechnology", "DetectionResult", "get_detector"]
