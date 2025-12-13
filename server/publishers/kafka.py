from __future__ import annotations

import orjson
from typing import Any

from server.logging import get_logger
from server.publishers.base import BasePublisher

logger = get_logger(__name__)


class KafkaPublisher(BasePublisher):
    """Publishes messages to Kafka topics using aiokafka."""

    def __init__(self, bootstrap_servers: str, **kwargs):
        """Initialize Kafka publisher.

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers (e.g., "localhost:9092")
            **kwargs: Additional AIOKafkaProducer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer_config = kwargs
        self.producer = None
        self._connected = False

        logger.info("kafka_publisher_initialized", bootstrap_servers=bootstrap_servers)

    async def _ensure_connected(self):
        """Ensure producer is initialized and connected."""
        if self._connected and self.producer:
            return

        try:
            from aiokafka import AIOKafkaProducer
        except ImportError:
            raise ImportError(
                "aiokafka is required for Kafka publishing. "
                "Install with: pip install aiokafka"
            )

        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: orjson.dumps(v),
            **self.producer_config,
        )
        await self.producer.start()
        self._connected = True
        logger.info("kafka_producer_started", bootstrap_servers=self.bootstrap_servers)

    async def publish(
        self, topic: str, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """Publish messages to Kafka topic.

        Args:
            topic: Kafka topic name
            messages: List of message payloads
            **kwargs: Additional send options (key, partition, timestamp, headers)

        Returns:
            dict with publish results
        """
        await self._ensure_connected()

        if not self.producer:
            raise RuntimeError("Kafka producer not initialized")

        sent_count = 0
        failed_count = 0
        futures = []

        for msg in messages:
            try:
                future = await self.producer.send(topic, value=msg, **kwargs)
                futures.append(future)
                sent_count += 1
            except Exception as e:
                logger.error("kafka_send_failed", topic=topic, error=str(e))
                failed_count += 1

        await self.producer.flush()

        logger.info(
            "kafka_publish_complete",
            topic=topic,
            sent=sent_count,
            failed=failed_count,
        )

        return {
            "success": True,
            "topic": topic,
            "sent": sent_count,
            "failed": failed_count,
            "total": len(messages),
        }

    async def close(self):
        """Stop producer and cleanup."""
        if self.producer:
            await self.producer.stop()
            self._connected = False
            logger.info("kafka_producer_stopped")

    def health_check(self) -> dict[str, Any]:
        """Check Kafka connection health."""
        return {
            "connected": self._connected,
            "bootstrap_servers": self.bootstrap_servers,
        }
