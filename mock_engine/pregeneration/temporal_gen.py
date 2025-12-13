import time
from typing import Literal


class TemporalGenerator:
    """
    Manages temporal state for pre-generated items during streaming.

    Supports two modes:
    - actual_time_based: Adjusts timestamp based on real elapsed time
    - per_generation: Increments timestamp by fixed step per call
    """

    def __init__(
        self,
        field_name: str,
        start_date: int,
        step: int,
        mode: Literal["actual_time_based", "per_generation"] = "actual_time_based",
        time_multiplier: float = 1.0,
    ):
        """
        Initialize temporal generator.

        Args:
            field_name: Name of the temporal field to replace
            start_date: Initial timestamp value (microseconds)
            step: Step size in microseconds for increments
            mode: Generation mode - actual_time_based or per_generation
            time_multiplier: Speed multiplier for actual_time_based mode
        """
        self.field_name = field_name
        self.start_date = start_date
        self.step = step
        self.mode = mode
        self.time_multiplier = time_multiplier

        self.real_start_time = time.time()  # seconds
        self.last_timestamp = start_date
        self.call_count = 0

    def next(self) -> int:
        """
        Get next timestamp value based on configured mode.

        Returns:
            Next timestamp in microseconds
        """
        self.call_count += 1

        if self.mode == "actual_time_based":
            real_elapsed_seconds = time.time() - self.real_start_time
            elapsed_micros = int(
                real_elapsed_seconds * 1_000_000 * self.time_multiplier
            )
            self.last_timestamp = self.start_date + elapsed_micros
        else:
            self.last_timestamp += self.step

        return self.last_timestamp

    def reset(self):
        """Reset generator state to initial values."""
        self.real_start_time = time.time()
        self.last_timestamp = self.start_date
        self.call_count = 0

    def get_stats(self) -> dict:
        """Get current generator statistics."""
        return {
            "field_name": self.field_name,
            "mode": self.mode,
            "call_count": self.call_count,
            "current_timestamp": self.last_timestamp,
            "elapsed_seconds": time.time() - self.real_start_time,
        }
