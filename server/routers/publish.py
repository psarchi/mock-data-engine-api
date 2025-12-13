from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mock_engine.config import get_config_manager
from mock_engine.context import GenContext
from server.auth import RequireAuth
from server.deps import get_generator
from server.logging import get_logger
from server.publishers import KafkaPublisher, PubSubPublisher

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/publish", tags=["publish"])


class PublishRequest(BaseModel):
    """Request body for publishing data."""

    count: int = Field(
        1, ge=1, le=100000, description="Number of events to generate and publish"
    )
    topic: str | None = Field(
        None, description="Topic name (overrides default schema topic)"
    )
    batch_size: int = Field(
        1000, ge=1, le=10000, description="Batch size for publishing"
    )


class PublishResponse(BaseModel):
    """Response for publish operations."""

    success: bool
    schema: str
    topic: str
    provider: str
    generated: int
    sent: int
    failed: int
    batches: int
    elapsed_seconds: float


_kafka_publisher: KafkaPublisher | None = None
_pubsub_publisher: PubSubPublisher | None = None


def get_kafka_publisher() -> KafkaPublisher:
    """Get or create Kafka publisher instance."""
    global _kafka_publisher

    if _kafka_publisher is None:
        try:
            cm = get_config_manager()
            enabled = cm.get_value("server.publishing.kafka.enabled", False)
            if not enabled:
                raise HTTPException(
                    status_code=503, detail="Kafka publishing is not enabled"
                )

            bootstrap_servers = cm.get_value(
                "server.publishing.kafka.bootstrap_servers", "localhost:9092"
            )
            _kafka_publisher = KafkaPublisher(bootstrap_servers=bootstrap_servers)
        except Exception as e:
            logger.error("kafka_publisher_init_failed", error=str(e))
            raise HTTPException(
                status_code=503, detail=f"Kafka publisher initialization failed: {e}"
            )

    return _kafka_publisher


def get_pubsub_publisher() -> PubSubPublisher:
    """Get or create Pub/Sub publisher instance."""
    global _pubsub_publisher

    if _pubsub_publisher is None:
        try:
            cm = get_config_manager()
            enabled = cm.get_value("server.publishing.pubsub.enabled", False)
            if not enabled:
                raise HTTPException(
                    status_code=503, detail="Pub/Sub publishing is not enabled"
                )

            project_id = cm.get_value("server.publishing.pubsub.project_id", "")
            if not project_id:
                raise HTTPException(
                    status_code=503, detail="Pub/Sub project_id not configured"
                )

            _pubsub_publisher = PubSubPublisher(project_id=project_id)
        except Exception as e:
            logger.error("pubsub_publisher_init_failed", error=str(e))
            raise HTTPException(
                status_code=503, detail=f"Pub/Sub publisher initialization failed: {e}"
            )

    return _pubsub_publisher


async def generate_and_publish(
    schema: str,
    count: int,
    batch_size: int,
    publisher,
    topic: str,
) -> PublishResponse:
    """Generate data and publish in batches.

    Args:
        schema: Schema name to generate
        count: Total number of events to generate
        batch_size: Batch size for publishing
        publisher: Publisher instance (Kafka or Pub/Sub)
        topic: Topic name to publish to

    Returns:
        PublishResponse with results
    """
    import time

    start_time = time.time()

    # Get generator
    try:
        gen = get_generator(schema)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Schema not found: {schema}")

    total_sent = 0
    total_failed = 0
    batch_count = 0
    ctx = GenContext(seed=None)
    ctx.schema_name = schema

    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch_count_items = batch_end - batch_start

        items = [gen.generate(ctx) for _ in range(batch_count_items)]

        try:
            result = await publisher.publish(topic, items)
            total_sent += result.get("sent", 0)
            total_failed += result.get("failed", 0)
            batch_count += 1

            logger.debug(
                "publish_batch_complete",
                schema=schema,
                topic=topic,
                batch=batch_count,
                sent=result.get("sent", 0),
            )
        except Exception as e:
            logger.error(
                "publish_batch_failed", schema=schema, topic=topic, error=str(e)
            )
            total_failed += batch_count_items

        await asyncio.sleep(0)

    elapsed = time.time() - start_time

    logger.info(
        "publish_complete",
        schema=schema,
        topic=topic,
        generated=count,
        sent=total_sent,
        failed=total_failed,
        batches=batch_count,
        elapsed=elapsed,
    )

    return PublishResponse(
        success=True,
        schema=schema,
        topic=topic,
        provider=publisher.__class__.__name__.replace("Publisher", "").lower(),
        generated=count,
        sent=total_sent,
        failed=total_failed,
        batches=batch_count,
        elapsed_seconds=round(elapsed, 3),
    )


@router.post("/kafka/{schema}", response_model=PublishResponse)
async def publish_to_kafka(
    schema: str,
    request: PublishRequest,
    _token: RequireAuth = None,
) -> PublishResponse:
    """Generate and publish data to Kafka topic.

    Requires authentication via token.

    Args:
        schema: Schema name to generate
        request: Publish request with count, topic, batch_size

    Returns:
        PublishResponse with results
    """
    publisher = get_kafka_publisher()

    topic = request.topic or schema

    return await generate_and_publish(
        schema=schema,
        count=request.count,
        batch_size=request.batch_size,
        publisher=publisher,
        topic=topic,
    )


@router.post("/pubsub/{schema}", response_model=PublishResponse)
async def publish_to_pubsub(
    schema: str,
    request: PublishRequest,
    _token: RequireAuth = None,
) -> PublishResponse:
    """Generate and publish data to Google Cloud Pub/Sub topic.

    Requires authentication via token.

    Args:
        schema: Schema name to generate
        request: Publish request with count, topic, batch_size

    Returns:
        PublishResponse with results
    """
    publisher = get_pubsub_publisher()

    topic = request.topic or schema

    return await generate_and_publish(
        schema=schema,
        count=request.count,
        batch_size=request.batch_size,
        publisher=publisher,
        topic=topic,
    )


@router.get("/health")
async def health_check(_token: RequireAuth = None) -> dict[str, Any]:
    """Check health of all configured publishers.

    Requires authentication via token.

    Returns:
        dict with health status of each publisher
    """
    health = {}

    try:
        cm = get_config_manager()

        if cm.get_value("server.publishing.kafka.enabled", False):
            try:
                publisher = get_kafka_publisher()
                health["kafka"] = publisher.health_check()
            except Exception as e:
                health["kafka"] = {"error": str(e)}

        if cm.get_value("server.publishing.pubsub.enabled", False):
            try:
                publisher = get_pubsub_publisher()
                health["pubsub"] = publisher.health_check()
            except Exception as e:
                health["pubsub"] = {"error": str(e)}

    except Exception as e:
        logger.error("health_check_failed", error=str(e))

    return {"publishers": health}


async def shutdown_publishers():
    """Cleanup publishers on shutdown."""
    global _kafka_publisher, _pubsub_publisher

    if _kafka_publisher:
        await _kafka_publisher.close()
        _kafka_publisher = None

    if _pubsub_publisher:
        await _pubsub_publisher.close()
        _pubsub_publisher = None

    logger.info("publishers_shutdown_complete")
