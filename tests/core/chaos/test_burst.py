import pytest

from mock_engine.chaos.ops.network.burst import BurstOp


@pytest.mark.ci
class TestBurstOp:
    """Test burst chaos operation."""

    def test_burst_initialization(self):
        """Test burst op initializes with correct defaults."""
        op = BurstOp(
            enabled=True,
            probability=0.01,
            burst_rate=10_000,
            burst_duration=10,
            require_cache_items=None,
        )

        assert op.enabled is True
        assert op.probability == 0.01
        assert op.burst_rate == 10_000
        assert op.burst_duration == 10
        assert op.require_cache_items is None
        assert op.burst_active is False
        assert op.burst_start is None

    def test_burst_activation_probability(self):
        """Test burst activates based on probability."""
        op = BurstOp(enabled=True, probability=1.0, burst_rate=5000, burst_duration=5)

        body = {"test": "data"}
        result_body, metadata = op.apply(body)

        assert result_body == body
        assert metadata.get("burst_active") is True
        assert metadata.get("burst_rate") == 5000
        assert metadata.get("burst_duration") == 5
        assert metadata.get("required_cache_items") == 25_000
        assert "burst_started_at" in metadata

    def test_burst_no_activation_low_probability(self):
        """Test burst doesn't activate with low probability."""
        op = BurstOp(enabled=True, probability=0.0, burst_rate=5000, burst_duration=5)

        body = {"test": "data"}
        result_body, metadata = op.apply(body)

        assert result_body == body
        assert metadata == {}

    def test_burst_continues_while_active(self):
        """Test burst continues to return metadata while active."""
        op = BurstOp(enabled=True, probability=1.0, burst_rate=5000, burst_duration=10)

        body = {"test": "data"}
        _, metadata1 = op.apply(body)
        assert metadata1.get("burst_active") is True

        _, metadata2 = op.apply(body)
        assert metadata2.get("burst_active") is True
        assert metadata2.get("burst_rate") == 5000

    def test_burst_expires_after_duration(self):
        """Test burst expires after configured duration."""
        import time

        op = BurstOp(enabled=True, probability=1.0, burst_rate=5000, burst_duration=0.1)

        body = {"test": "data"}

        _, metadata1 = op.apply(body)
        assert metadata1.get("burst_active") is True

        time.sleep(0.2)

        _, metadata2 = op.apply(body)
        assert metadata2 == {}

    def test_burst_custom_cache_items_requirement(self):
        """Test burst with custom required cache items."""
        op = BurstOp(
            enabled=True,
            probability=1.0,
            burst_rate=10_000,
            burst_duration=10,
            require_cache_items=50_000,
        )

        body = {"test": "data"}
        _, metadata = op.apply(body)

        assert metadata.get("burst_active") is True
        assert metadata.get("required_cache_items") == 50_000

    def test_burst_auto_calculate_cache_items(self):
        """Test burst auto-calculates required cache items."""
        op = BurstOp(
            enabled=True,
            probability=1.0,
            burst_rate=8000,
            burst_duration=15,
            require_cache_items=None,
        )

        body = {"test": "data"}
        _, metadata = op.apply(body)

        assert metadata.get("burst_active") is True
        assert metadata.get("required_cache_items") == 120_000

    def test_burst_disabled(self):
        """Test burst doesn't activate when disabled."""
        op = BurstOp(enabled=False, probability=1.0, burst_rate=5000, burst_duration=5)

        body = {"test": "data"}
        result_body, metadata = op.apply(body)

        assert result_body == body
        assert metadata == {}

    def test_burst_type_token(self):
        """Test burst op has correct type token."""
        op = BurstOp(enabled=True)
        assert op.type_token == "burst"

    @pytest.mark.skip(reason="Requires running WebSocket server with rate limiter")
    def test_burst_integration_with_rate_limiter(self):
        """Integration test: burst metadata activates rate limiter.

        TODO: Test should verify:
        1. Burst chaos op returns metadata with burst_active=True
        2. Streaming endpoint reads burst metadata
        3. Rate limiter.activate_burst() called with correct params
        4. Throughput increases during burst period
        5. Rate limiter returns to base rate after burst expires
        6. Cache validation prevents burst if insufficient items
        """
        pass

    @pytest.mark.skip(reason="Requires running pre-generation worker")
    def test_burst_with_pregen_cache_validation(self):
        """Integration test: burst validates cache before activation.

        TODO: Test should verify:
        1. Burst requires 100K items (burst_rate * duration)
        2. Cache has only 50K items
        3. Burst blocked with warning logged
        4. Cache grows to 100K+ items
        5. Burst activates successfully
        6. Throughput increases as expected
        """
        pass
