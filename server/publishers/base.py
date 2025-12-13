from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePublisher(ABC):
    """Base class for message publishers (Kafka, PubSub, etc.)."""

    @abstractmethod
    async def publish(
        self, topic: str, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """Publish messages to a topic.

        Args:
            topic: Topic/channel name to publish to
            messages: List of message payloads (will be serialized to JSON)
            **kwargs: Publisher-specific options

        Returns:
            dict with publish results/metadata
        """
        pass

    @abstractmethod
    async def close(self):
        """Close publisher and cleanup resources."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Check publisher health/connectivity.

        Returns:
            dict with health status
        """
        pass
