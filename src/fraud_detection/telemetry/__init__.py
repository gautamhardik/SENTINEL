"""
Subsecond Telemetry and Latency Profiler Module.
"""
import time
from typing import Any, Dict


class LatencyProfiler:
    """Tracks stage-by-stage inference latency in milliseconds."""

    def __init__(self):
        self.stage_latencies: Dict[str, float] = {}
        self.total_start: float = time.time()
        self._current_stage: str = ""
        self._stage_start: float = 0.0

    def start_stage(self, name: str) -> None:
        self._current_stage = name
        self._stage_start = time.time()

    def end_stage(self, name: str) -> float:
        duration = round((time.time() - self._stage_start) * 1000.0, 4)
        self.stage_latencies[name] = duration
        return duration

    @property
    def total_latency_ms(self) -> float:
        return round((time.time() - self.total_start) * 1000.0, 4)
