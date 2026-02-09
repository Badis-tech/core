"""Performance profiling utilities for form automation"""

import asyncio
import time
import psutil
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class ProfilingPhase(BaseModel):
    """Profiling data for a specific operation phase"""
    phase_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = {}

    class Config:
        use_enum_values = False


class ProfilingData(BaseModel):
    """Performance profiling data for form automation"""
    # High-level timing
    total_duration_ms: float
    detection_duration_ms: Optional[float] = None
    filling_duration_ms: Optional[float] = None

    # Phase-level breakdown
    phases: List[ProfilingPhase] = []

    # Operation counts
    field_count: int = 0
    screenshot_count: int = 0
    retry_count: int = 0

    # Resource metrics
    peak_memory_mb: Optional[float] = None
    browser_instance_count: int = 1

    # Bottleneck identification
    slowest_phase: Optional[str] = None
    slowest_phase_duration_ms: Optional[float] = None

    # Timestamps
    profiled_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = False


class ProfilerCollector:
    """Collects profiling data for a single operation"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.phases: List[ProfilingPhase] = []
        self.start_time: Optional[float] = None
        self.metadata: Dict[str, Any] = {}
        self.process = psutil.Process()
        self.peak_memory_mb = 0.0

    def start(self):
        """Begin profiling session"""
        self.start_time = time.time()

    def finish(self) -> ProfilingData:
        """Complete profiling and return aggregated data"""
        if self.start_time is None:
            raise RuntimeError("Profiler not started")

        total_duration = (time.time() - self.start_time) * 1000

        # Find slowest phase
        slowest = max(self.phases, key=lambda p: p.duration_ms) if self.phases else None

        return ProfilingData(
            total_duration_ms=total_duration,
            phases=self.phases,
            slowest_phase=slowest.phase_name if slowest else None,
            slowest_phase_duration_ms=slowest.duration_ms if slowest else None,
            peak_memory_mb=self.peak_memory_mb,
            **self.metadata,
        )

    @asynccontextmanager
    async def profile_phase(self, phase_name: str, **metadata):
        """Context manager to profile a phase"""
        phase_start = time.time()
        start_dt = datetime.utcnow()
        success = False

        # Track memory
        try:
            mem_before = self.process.memory_info().rss / 1024 / 1024
        except (AttributeError, ProcessLookupError):
            mem_before = 0.0

        try:
            yield
            success = True
        finally:
            end_dt = datetime.utcnow()
            duration_ms = (time.time() - phase_start) * 1000

            try:
                mem_after = self.process.memory_info().rss / 1024 / 1024
                self.peak_memory_mb = max(self.peak_memory_mb, mem_after)
                memory_delta = mem_after - mem_before
            except (AttributeError, ProcessLookupError):
                memory_delta = 0.0

            phase = ProfilingPhase(
                phase_name=phase_name,
                start_time=start_dt,
                end_time=end_dt,
                duration_ms=duration_ms,
                success=success,
                metadata={**metadata, "memory_delta_mb": memory_delta},
            )
            self.phases.append(phase)


def format_profiling_report(profiling: ProfilingData) -> str:
    """Format profiling data as human-readable CLI output"""

    report = []
    report.append("\n" + "=" * 70)
    report.append("PROFILING REPORT")
    report.append("=" * 70)
    report.append(f"Total Duration: {profiling.total_duration_ms:.2f} ms")

    if profiling.peak_memory_mb:
        report.append(f"Peak Memory: {profiling.peak_memory_mb:.2f} MB")

    report.append(f"Field Count: {profiling.field_count}")
    report.append(f"Screenshot Count: {profiling.screenshot_count}")

    if profiling.slowest_phase:
        report.append(
            f"\nBottleneck: {profiling.slowest_phase} ({profiling.slowest_phase_duration_ms:.2f} ms)"
        )

    report.append("\nPHASE BREAKDOWN:")
    report.append("-" * 70)
    report.append(f"{'Phase':<35} {'Duration (ms)':<15} {'% of Total':<15}")
    report.append("-" * 70)

    for phase in sorted(profiling.phases, key=lambda p: p.duration_ms, reverse=True):
        percent = (phase.duration_ms / profiling.total_duration_ms) * 100
        status = "[OK]" if phase.success else "[FAIL]"
        report.append(
            f"{phase.phase_name:<35} {phase.duration_ms:>10.2f} ms   {percent:>6.1f}% {status}"
        )

    report.append("=" * 70 + "\n")

    return "\n".join(report)
