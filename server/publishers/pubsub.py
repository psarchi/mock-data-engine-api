from __future__ import annotations

import orjson
from typing import Any

from server.logging import get_logger
from server.publishers.base import BasePublisher

logger = get_logger(__name__)


class PubSubPublisher(BasePublisher):
    """Publishes messages to Google Cloud Pub/Sub topics."""

    def __init__(self, project_id: str, **kwargs):
        """Initialize Pub/Sub publisher.

        Args:
            project_id: GCP project ID
            **kwargs: Additional PublisherClient configuration
        """
        self.project_id = project_id
        self.client_config = kwargs
        self.client = None
        self._connected = False

        logger.info("pubsub_publisher_initialized", project_id=project_id)

    def _ensure_connected(self):
        """Ensure publisher client is initialized."""
        if self._connected and self.client:
            return

        try:
            from google.cloud import pubsub_v1
        except ImportError:
            raise ImportError(
                "google-cloud-pubsub is required for Pub/Sub publishing. "
                "Install with: pip install google-cloud-pubsub"
            )

        self.client = pubsub_v1.PublisherClient(**self.client_config)
        self._connected = True
        logger.info("pubsub_client_initialized", project_id=self.project_id)

    async def publish(
        self, topic: str, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """Publish messages to Pub/Sub topic.

        Args:
            topic: Pub/Sub topic name (without project prefix)
            messages: List of message payloads
            **kwargs: Additional publish options (ordering_key, attributes)

        Returns:
            dict with publish results
        """
        self._ensure_connected()

        if not self.client:
            raise RuntimeError("Pub/Sub client not initialized")

        topic_path = self.client.topic_path(self.project_id, topic)

        sent_count = 0
        failed_count = 0
        futures = []

        for msg in messages:
            try:
                data = orjson.dumps(msg)

                future = self.client.publish(topic_path, data, **kwargs)
                futures.append(future)
                sent_count += 1
            except Exception as e:
                logger.error("pubsub_publish_failed", topic=topic, error=str(e))
                failed_count += 1

        message_ids = []
        for future in futures:
            try:
                message_id = future.result(timeout=10)
                message_ids.append(message_id)
            except Exception as e:
                logger.error("pubsub_future_failed", error=str(e))
                failed_count += 1
                sent_count -= 1

        logger.info(
            "pubsub_publish_complete",
            topic=topic,
            sent=sent_count,
            failed=failed_count,
        )

        return {
            "success": True,
            "topic": topic,
            "topic_path": topic_path,
            "sent": sent_count,
            "failed": failed_count,
            "total": len(messages),
            "message_ids": message_ids[:10],  # Sample of message IDs
        }

    async def close(self):
        """Cleanup Pub/Sub client."""
        if self.client:
            self._connected = False
            logger.info("pubsub_client_closed")

    def health_check(self) -> dict[str, Any]:
        """Check Pub/Sub connection health."""
        return {
            "connected": self._connected,
            "project_id": self.project_id,
        }
