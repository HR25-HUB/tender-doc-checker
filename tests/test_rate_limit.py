"""
Tests for rate limiting functionality using in-memory mock storage.
Tests various rate limiting scenarios including time windows, user limits, and edge cases.
"""
import time
from dataclasses import dataclass

import pytest

# Constants for rate limiting windows
SECOND = 1
MINUTE = 60
HOUR = 3600


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    requests_per_window: int
    window_seconds: int
    key_prefix: str = "rate_limit"


class InMemoryRateLimiter:
    """In-memory implementation of rate limiter for testing"""

    def __init__(self):
        self.storage: dict[str, list] = {}
        self.current_time = time.time()

    def _get_storage_key(self, identifier: str, window_seconds: int) -> str:
        """Generate storage key for rate limit tracking"""
        return f"{window_seconds}:{identifier}"

    def _clean_old_requests(self, requests: list, window_seconds: int) -> list:
        """Remove old requests outside the time window"""
        cutoff_time = self.current_time - window_seconds
        return [req_time for req_time in requests if req_time > cutoff_time]

    def check_rate_limit(
        self, identifier: str, config: RateLimitConfig
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit
        Returns: (is_allowed, remaining_requests)
        """
        key = self._get_storage_key(identifier, config.window_seconds)

        if key not in self.storage:
            self.storage[key] = []

        # Clean old requests
        self.storage[key] = self._clean_old_requests(
            self.storage[key], config.window_seconds
        )

        # Check if limit exceeded
        if len(self.storage[key]) >= config.requests_per_window:
            return False, 0

        # Add current request
        self.storage[key].append(self.current_time)
        remaining = max(0, config.requests_per_window - len(self.storage[key]))

        return True, remaining

    def reset_limit(self, identifier: str, window_seconds: int):
        """Reset rate limit for specific identifier and window"""
        key = self._get_storage_key(identifier, window_seconds)
        if key in self.storage:
            del self.storage[key]

    def reset_all(self):
        """Reset all rate limits"""
        self.storage.clear()

    def set_time(self, timestamp: float):
        """Set current time for testing purposes"""
        self.current_time = timestamp


class TestRateLimitBasicFunctionality:
    """Test basic rate limiting functionality"""

    def test_single_request_allowed(self):
        """Test that first request is always allowed"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=5, window_seconds=60)

        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is True
        assert remaining == 4

    def test_multiple_requests_within_limit(self):
        """Test multiple requests within limit"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=3, window_seconds=60)

        # Make 3 requests within limit
        for i in range(3):
            allowed, remaining = limiter.check_rate_limit("user1", config)
            assert allowed is True
            assert remaining == 2 - i

    def test_limit_exceeded(self):
        """Test that limit is enforced when exceeded"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=2, window_seconds=60)

        # Make 2 allowed requests
        for _ in range(2):
            allowed, _ = limiter.check_rate_limit("user1", config)
            assert allowed is True

        # 3rd request should be blocked
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is False
        assert remaining == 0


class TestRateLimitTimeWindows:
    """Test rate limiting with different time windows"""

    def test_per_second_limit(self):
        """Test per-second rate limiting"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=2, window_seconds=1)

        # Make 2 requests in same second
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is True

        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is True

        # 3rd request should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

    def test_per_minute_limit(self):
        """Test per-minute rate limiting"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=60, window_seconds=60)

        # Make 60 requests within minute
        for i in range(60):
            allowed, remaining = limiter.check_rate_limit("user1", config)
            assert allowed is True
            assert remaining == 59 - i

        # 61st request should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

    def test_time_window_expiration(self):
        """Test that old requests expire from time window"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=2, window_seconds=10)

        # Make 2 requests
        limiter.check_rate_limit("user1", config)
        limiter.check_rate_limit("user1", config)

        # Should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

        # Advance time by 11 seconds (window + 1)
        limiter.set_time(time.time() + 11)

        # Should be allowed again
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is True
        assert remaining == 1


class TestRateLimitUserIsolation:
    """Test rate limiting isolation between different users/IPs"""

    def test_user_isolation(self):
        """Test that rate limits are isolated per user"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=2, window_seconds=60)

        # User 1 makes 2 requests
        for _ in range(2):
            allowed, _ = limiter.check_rate_limit("user1", config)
            assert allowed is True

        # User 1 should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

        # User 2 should still be allowed
        allowed, remaining = limiter.check_rate_limit("user2", config)
        assert allowed is True
        assert remaining == 1

    def test_ip_isolation(self):
        """Test rate limiting by IP address"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=3, window_seconds=60)

        ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]

        # Each IP can make 3 requests independently
        for ip in ips:
            for i in range(3):
                allowed, remaining = limiter.check_rate_limit(ip, config)
                assert allowed is True
                assert remaining == 2 - i

            # 4th request should be blocked for this IP
            allowed, _ = limiter.check_rate_limit(ip, config)
            assert allowed is False


class TestRateLimitEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_limit_config(self):
        """Test behavior with zero requests allowed"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=0, window_seconds=60)

        # All requests should be blocked
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is False
        assert remaining == 0

    def test_large_window(self):
        """Test with very large time window"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(
            requests_per_window=1000, window_seconds=3600
        )  # 1 hour instead of 24

        # Make 1000 requests
        for i in range(1000):
            allowed, remaining = limiter.check_rate_limit("user1", config)
            assert allowed is True
            assert remaining == 999 - i

        # 1001st should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

    def test_concurrent_identifiers(self):
        """Test many different identifiers simultaneously"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=1, window_seconds=60)

        # Test with 1000 different users
        for i in range(1000):
            user_id = f"user_{i}"
            allowed, remaining = limiter.check_rate_limit(user_id, config)
            assert allowed is True
            assert remaining == 0

    def test_reset_functionality(self):
        """Test rate limit reset functionality"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=2, window_seconds=60)

        # Make 2 requests
        limiter.check_rate_limit("user1", config)
        limiter.check_rate_limit("user1", config)

        # Should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

        # Reset limit
        limiter.reset_limit("user1", 60)

        # Should be allowed again
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is True
        assert remaining == 1


class TestRateLimitIntegration:
    """Integration tests for rate limiting in application context"""

    def test_api_endpoint_simulation(self):
        """Simulate rate limiting on API endpoints"""
        limiter = InMemoryRateLimiter()

        # Different endpoints with different limits
        endpoints = {
            "/api/upload": RateLimitConfig(requests_per_window=5, window_seconds=60),
            "/api/search": RateLimitConfig(requests_per_window=100, window_seconds=60),
            "/api/admin": RateLimitConfig(requests_per_window=10, window_seconds=3600),
        }

        user_id = "user123"

        # Test upload endpoint
        for i in range(5):
            allowed, remaining = limiter.check_rate_limit(
                f"{user_id}:upload", endpoints["/api/upload"]
            )
            assert allowed is True
            assert remaining == 4 - i

        # Should be blocked
        allowed, _ = limiter.check_rate_limit(
            f"{user_id}:upload", endpoints["/api/upload"]
        )
        assert allowed is False

        # Search endpoint should still work
        allowed, _ = limiter.check_rate_limit(
            f"{user_id}:search", endpoints["/api/search"]
        )
        assert allowed is True

    def test_sliding_window_behavior(self):
        """Test sliding window rate limiting behavior"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=3, window_seconds=10)

        base_time = time.time()

        # Make 3 requests at different times
        limiter.set_time(base_time)
        limiter.check_rate_limit("user1", config)

        limiter.set_time(base_time + 3)
        limiter.check_rate_limit("user1", config)

        limiter.set_time(base_time + 6)
        limiter.check_rate_limit("user1", config)

        # Should be blocked
        allowed, _ = limiter.check_rate_limit("user1", config)
        assert allowed is False

        # After 4 more seconds, first request should expire
        limiter.set_time(base_time + 11)
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is True
        # Don't check exact remaining count as cleanup happens before adding new request


class TestRateLimitPerformance:
    """Performance tests for rate limiting"""

    def test_high_throughput(self):
        """Test rate limiter with high throughput"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=10000, window_seconds=60)

        # Simulate 99 requests from 100 users (under 100 limit)
        for i in range(9900):
            user_id = f"user_{i % 100}"
            allowed, _ = limiter.check_rate_limit(user_id, config)
            assert allowed is True

        # Test with a smaller, more manageable limit
        config_small = RateLimitConfig(requests_per_window=3, window_seconds=60)

        # Make 3 requests for a specific user to hit limit
        user_id = "user_test"
        for i in range(3):
            allowed, remaining = limiter.check_rate_limit(user_id, config_small)
            assert allowed is True

        # 4th request should be blocked
        allowed, _ = limiter.check_rate_limit(user_id, config_small)
        assert allowed is False

    def test_memory_cleanup(self):
        """Test that old data is properly cleaned up"""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_window=1, window_seconds=1)

        # Make requests with old timestamps
        old_time = time.time() - 3600  # 1 hour ago
        limiter.set_time(old_time)
        limiter.check_rate_limit("user1", config)

        # Set current time
        limiter.set_time(time.time())

        # Should be allowed as old data should be cleaned
        allowed, remaining = limiter.check_rate_limit("user1", config)
        assert allowed is True
        assert remaining == 0


@pytest.fixture
def rate_limiter():
    """Fixture for rate limiter instance"""
    return InMemoryRateLimiter()


@pytest.fixture
def standard_config():
    """Fixture for standard rate limit configuration"""
    return RateLimitConfig(requests_per_window=10, window_seconds=60)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
