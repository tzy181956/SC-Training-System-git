from __future__ import annotations

import time

from app.services.monitoring_service import TTLCache


def test_ttl_cache_returns_same_key_within_ttl() -> None:
    cache = TTLCache(ttl_seconds=1, max_entries=8)

    cache.set(("2026-05-14", None, None, True), {"athletes": [{"athlete_id": 1}]})
    cached = cache.get(("2026-05-14", None, None, True))

    assert cached == {"athletes": [{"athlete_id": 1}]}


def test_ttl_cache_keeps_distinct_monitoring_keys_separate() -> None:
    cache = TTLCache(ttl_seconds=1, max_entries=8)

    cache.set(("2026-05-14", 1, None, True), {"scope": "sport-1"})
    cache.set(("2026-05-14", 2, None, True), {"scope": "sport-2"})
    cache.set(("2026-05-14", 1, 10, False), {"scope": "team-10"})

    assert cache.get(("2026-05-14", 1, None, True)) == {"scope": "sport-1"}
    assert cache.get(("2026-05-14", 2, None, True)) == {"scope": "sport-2"}
    assert cache.get(("2026-05-14", 1, 10, False)) == {"scope": "team-10"}


def test_ttl_cache_expires_after_ttl() -> None:
    cache = TTLCache(ttl_seconds=0.01, max_entries=8)

    cache.set(("2026-05-14", None, None, True), {"updated_at": "first"})
    time.sleep(0.02)

    assert cache.get(("2026-05-14", None, None, True)) is None


def test_ttl_cache_limits_entry_count() -> None:
    cache = TTLCache(ttl_seconds=1, max_entries=2)

    cache.set(("date-1", None, None, True), {"value": 1})
    cache.set(("date-2", None, None, True), {"value": 2})
    cache.set(("date-3", None, None, True), {"value": 3})

    assert cache.get(("date-1", None, None, True)) is None
    assert cache.get(("date-2", None, None, True)) == {"value": 2}
    assert cache.get(("date-3", None, None, True)) == {"value": 3}
