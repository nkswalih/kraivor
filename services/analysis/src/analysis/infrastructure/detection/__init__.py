from analysis.infrastructure.detection.detector import FrameworkDetector
from analysis.infrastructure.detection.models import DetectedTechnology, DetectionResult


def get_detector() -> FrameworkDetector:
    return FrameworkDetector()


__all__ = ["DetectedTechnology", "DetectionResult", "get_detector"]
