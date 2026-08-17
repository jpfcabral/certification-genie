from enum import Enum


class CertificationType(Enum):
    """Supported certification exams.

    Extensible to support additional certifications in the future.
    """

    AI_103 = "AI-103"
