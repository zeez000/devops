import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    cpu_threshold: float = _float("LDD_CPU_THRESHOLD", 85.0)
    memory_threshold: float = _float("LDD_MEMORY_THRESHOLD", 85.0)
    disk_threshold: float = _float("LDD_DISK_THRESHOLD", 90.0)
    interval_seconds: int = _int("LDD_INTERVAL_SECONDS", 5)
    metrics_max_mb: int = _int("LDD_METRICS_MAX_MB", 20)
    incidents_max_mb: int = _int("LDD_INCIDENTS_MAX_MB", 10)
    forensic_cooldown_seconds: int = _int("LDD_FORENSIC_COOLDOWN_SECONDS", 20)
    forensic_max_files: int = _int("LDD_FORENSIC_MAX_FILES", 100)
    monitored_service: str = os.getenv("LDD_MONITORED_SERVICE", "nginx")
    monitored_port: int = _int("LDD_MONITORED_PORT", 80)


settings = Settings()
