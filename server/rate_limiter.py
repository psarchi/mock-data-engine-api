"""Adaptive rate limiter for streaming endpoints."""

from __future__ import annotations

import time
from typing import Optional

from server.logging import get_logger

logger = get_logger(__name__)


class AdaptiveRateLimiter:
    """Token bucket rate limiter with burst support and auto-detection.

    Features:
    - Token bucket algorithm for smooth rate limiting
    - Burst mode override for temporary high-throughput scenarios
    - Auto-detection and adjustment based on actual throughput
    """

    def __init__(
        self,
        base_rate: int = 1000,
        auto_detect: bool = False,
        auto_detect_sample_size: int = 1000,
    ):
        """Initialize rate limiter.

        Args:
            base_rate: Base rate limit in events per second
            auto_detect: Enable auto-detection and adjustment
            auto_detect_sample_size: Number of events to sample before adjusting
        """
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.tokens = float(base_rate)
        self.last_refill = time.time()

        self.burst_active = False
        self.burst_until: Optional[float] = None
        self.burst_rate: Optional[int] = None

        self.auto_detect = auto_detect
        self.auto_detect_sample_size = auto_detect_sample_size
        self.samples: list[tuple[float, int]] = []  # (timestamp, count)
        self.total_events = 0

        logger.info(
            "rate_limiter_initialized",
            base_rate=base_rate,
            auto_detect=auto_detect,
            sample_size=auto_detect_sample_size,
        )

    def activate_burst(self, burst_rate: int, duration: float):
        """Temporarily override rate for burst scenario.

        Args:
            burst_rate: Target rate during burst (events/sec)
            duration: Burst duration in seconds
        """
        self.burst_active = True
        self.burst_rate = burst_rate
        self.burst_until = time.time() + duration
        self.current_rate = burst_rate
        self.tokens = float(burst_rate)

        logger.info(
            "burst_activated",
            burst_rate=burst_rate,
            duration=duration,
            until=self.burst_until,
        )

    def _check_burst_expiration(self):
        """Check if burst has expired and reset to base rate."""
        if self.burst_active and self.burst_until and time.time() > self.burst_until:
            self.burst_active = False
            self.burst_until = None
            self.burst_rate = None
            self.current_rate = self.base_rate
            self.tokens = min(self.tokens, float(self.base_rate))

            logger.info(
                "burst_expired_reset_to_base_rate",
                base_rate=self.base_rate,
                was_burst_rate=self.burst_rate,
            )

    def _record_sample(self, count: int):
        """Record sample for auto-detection.

        Args:
            count: Number of events consumed
        """
        if not self.auto_detect:
            return

        self.samples.append((time.time(), count))
        self.total_events += count

        if len(self.samples) > self.auto_detect_sample_size:
            _, oldest_count = self.samples.pop(0)
            self.total_events -= oldest_count

        if len(self.samples) >= self.auto_detect_sample_size:
            self._adjust_rate()

    def _adjust_rate(self):
        """Adjust rate based on actual throughput.

        Uses 90% of observed throughput for safety margin.
        Burst mode can override this for chaos scenarios.
        """
        if len(self.samples) < 2:
            return

        first_ts, _ = self.samples[0]
        last_ts, _ = self.samples[-1]
        elapsed = last_ts - first_ts

        if elapsed > 0:
            actual_throughput = self.total_events / elapsed
            # Use 90% of actual throughput for safety margin
            new_rate = int(actual_throughput * 0.9)

            if abs(new_rate - self.current_rate) > (self.current_rate * 0.2):
                old_rate = self.current_rate
                self.base_rate = new_rate
                if not self.burst_active:
                    self.current_rate = new_rate

                logger.info(
                    "rate_auto_adjusted",
                    old_rate=old_rate,
                    new_rate=new_rate,
                    actual_throughput=int(actual_throughput),
                    samples=len(self.samples),
                )

                self.samples.clear()
                self.total_events = 0

    async def consume(self, count: int = 1) -> bool:
        """Attempt to consume tokens from the bucket.

        Args:
            count: Number of events to consume

        Returns:
            True if tokens were available and consumed, False otherwise
        """
        self._check_burst_expiration()

        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.current_rate
        self.tokens = min(self.current_rate, self.tokens + refill_amount)
        self.last_refill = now

        if self.tokens >= count:
            self.tokens -= count
            self._record_sample(count)
            return True

        return False

    def get_stats(self) -> dict:
        """Get current rate limiter statistics.

        Returns:
            Dict with current rate, tokens, burst status, etc.
        """
        return {
            "current_rate": self.current_rate,
            "base_rate": self.base_rate,
            "tokens_available": int(self.tokens),
            "burst_active": self.burst_active,
            "burst_rate": self.burst_rate,
            "burst_expires_in": max(0, self.burst_until - time.time())
            if self.burst_until
            else None,
            "auto_detect_enabled": self.auto_detect,
            "samples_collected": len(self.samples),
        }
