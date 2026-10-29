from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from movieradar.collector import (
    _JS_SOURCE_TYPES,
    RateLimiter,
    _detect_encoding,
    _entry_text,
    _extract_datetime,
    _extract_published,
    _parse_retry_after,
    _resolve_max_workers,
    collect_sources,
)
from movieradar.exceptions import NetworkError, ParseError, SourceError
from movieradar.models import Article, Source
from movieradar.storage import RadarStorage


class TestRateLimiter:
    """Unit tests for the RateLimiter class."""

    def test_acquire_no_delay_on_first_call(self):
        """First acquire call should not delay."""
        limiter = RateLimiter(min_interval=0.5)
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    def test_acquire_delays_subsequent_calls(self):
        """Subsequent calls within min_interval should delay."""
        limiter = RateLimiter(min_interval=0.1)
        limiter.acquire()
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        # Should have delayed close to min_interval
        assert elapsed >= 0.08


class TestResolveMaxWorkers:
    """Unit tests for _resolve_max_workers function."""

    def test_default_value(self):
        """Default returns 5 when no env var and no argument."""
        with patch.dict("os.environ", {}, clear=True):
            result = _resolve_max_workers(None)
        assert result == 5

    def test_explicit_value(self):
        """Explicit value is used when provided."""
        result = _resolve_max_workers(3)
        assert result == 3

    def test_max_capped_at_10(self):
        """Values above 10 are capped."""
        result = _resolve_max_workers(20)
        assert result == 10

    def test_min_capped_at_1(self):
        """Values below 1 are raised to 1."""
        result = _resolve_max_workers(0)
        assert result == 1

    def test_env_var_override(self):
        """Environment variable overrides default."""
        with patch.dict("os.environ", {"RADAR_MAX_WORKERS": "7"}):
            result = _resolve_max_workers(None)
        assert result == 7

    def test_invalid_env_var_uses_default(self):
        """Invalid env var falls back to default."""
        with patch.dict("os.environ", {"RADAR_MAX_WORKERS": "invalid"}):
            result = _resolve_max_workers(None)
        assert result == 5


class TestParseRetryAfter:
    """Unit tests for _parse_retry_after function."""

    def test_none_value(self):
        """None input returns None."""
        assert _parse_retry_after(None) is None

    def test_empty_string(self):
        """Empty string returns None."""
        assert _parse_retry_after("") is None
        assert _parse_retry_after("   ") is None

    def test_numeric_string(self):
        """Numeric string returns int."""
        assert _parse_retry_after("60") == 60
        assert _parse_retry_after("120") == 120

    def test_date_string(self):
        """Date string returns the string itself."""
        date_str = "Wed, 21 Oct 2025 07:28:00 GMT"
        assert _parse_retry_after(date_str) == date_str


class TestDetectEncoding:
    """Unit tests for _detect_encoding function."""

    def test_utf8_default(self):
        """Default encoding is UTF-8."""
        response = MagicMock()
        response.headers = {"Content-Type": "text/xml"}
        assert _detect_encoding(response) == "utf-8"

    def test_euc_kr_detection(self):
        """EUC-KR encoding is detected from Content-Type."""
        response = MagicMock()
        response.headers = {"Content-Type": "text/html; charset=euc-kr"}
        assert _detect_encoding(response) == "euc-kr"

    def test_charset_extraction(self):
        """Charset is extracted from Content-Type header."""
        response = MagicMock()
        response.headers = {"Content-Type": "text/html; charset=iso-8859-1"}
        assert _detect_encoding(response) == "iso-8859-1"


class TestExtractDatetime:
    """Unit tests for _extract_datetime function."""

    def test_published_parsed(self):
        """Parses published_parsed struct_time."""
        # Use a mid-year date to avoid timezone edge cases at year boundaries
        entry = {"published_parsed": time.strptime("2024-06-15 12:00:00", "%Y-%m-%d %H:%M:%S")}
        result = _extract_datetime(entry)
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.tzinfo == UTC

    def test_updated_parsed_fallback(self):
        """Falls back to updated_parsed if published_parsed is missing."""
        entry = {"updated_parsed": time.strptime("2024-07-20 12:00:00", "%Y-%m-%d %H:%M:%S")}
        result = _extract_datetime(entry)
        assert result is not None
        assert result.year == 2024
        assert result.month == 7

    def test_rfc2822_date_string(self):
        """Parses RFC 2822 date string."""
        entry = {"published": "Mon, 01 Jan 2024 12:00:00 +0000"}
        result = _extract_datetime(entry)
        assert result is not None
        assert result.year == 2024

    def test_no_date_returns_none(self):
        """Returns None when no date fields are present."""
        entry = {}
        result = _extract_datetime(entry)
        assert result is None

    def test_feedparser_struct_stores_utc_under_asia_seoul(self, monkeypatch, tmp_path):
        """2026-10-28 15:00 UTC struct stays 15:00 UTC when TZ=Asia/Seoul."""
        monkeypatch.setenv("TZ", "Asia/Seoul")
        time.tzset()
        try:
            entry = {"published_parsed": time.strptime("2026-10-28 15:00:00", "%Y-%m-%d %H:%M:%S")}
            published, published_raw = _extract_published(entry)
            assert published_raw is None
            assert published == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)

            article = Article(
                title="게시일",
                link="https://example.com/published-tz",
                summary="요약",
                published=published,
                source="TestSource",
                category="movie",
                published_raw=published_raw,
            )
            with RadarStorage(tmp_path / "tz.duckdb") as storage:
                storage.upsert_articles([article])
                loaded = storage.recent_articles("movie", days=3650)
            assert loaded[0].published == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)
        finally:
            monkeypatch.undo()
            time.tzset()

    def test_offset_string_keeps_offset(self):
        """Strings that already carry an offset keep that offset."""
        entry = {"published": "Wed, 28 Oct 2026 15:00:00 +0900"}
        result = _extract_datetime(entry)
        assert result is not None
        assert result.utcoffset() == timedelta(hours=9)
        assert result.astimezone(UTC) == datetime(2026, 10, 28, 6, 0, tzinfo=UTC)

    def test_zoneless_string_uses_source_or_host_default(self):
        """Zone-less strings use default_timezone, else .kr → Seoul and others → UTC."""
        kr_source = Source(name="씨네21", type="rss", url="https://www.cine21.co.kr/rss/news.xml")
        kr_result = _extract_datetime({"published": "2026-10-28 15:00:00"}, kr_source)
        assert kr_result == datetime(2026, 10, 28, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))

        utc_source = Source(name="Variety", type="rss", url="https://variety.com/feed/")
        utc_result = _extract_datetime({"published": "2026-10-28 15:00:00"}, utc_source)
        assert utc_result == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)

        explicit = Source(
            name="Variety",
            type="rss",
            url="https://variety.com/feed/",
            default_timezone="Asia/Seoul",
        )
        explicit_result = _extract_datetime({"published": "2026-10-28 15:00:00"}, explicit)
        assert explicit_result == datetime(2026, 10, 28, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))

        configured = Source(
            name="Variety",
            type="rss",
            url="https://variety.com/feed/",
            config={"default_timezone": "Asia/Seoul"},
        )
        configured_result = _extract_datetime({"published": "2026-10-28 15:00:00"}, configured)
        assert configured_result == datetime(2026, 10, 28, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))


class TestEntryText:
    """Unit tests for _entry_text function."""

    def test_string_value(self):
        """Returns string value when present."""
        entry = {"title": "Test Title"}
        assert _entry_text(entry, "title") == "Test Title"

    def test_missing_key(self):
        """Returns empty string for missing key."""
        entry = {}
        assert _entry_text(entry, "title") == ""

    def test_non_string_value(self):
        """Returns empty string for non-string values."""
        entry = {"title": 123}
        assert _entry_text(entry, "title") == ""

    def test_none_value(self):
        """Returns empty string for None value."""
        entry = {"title": None}
        assert _entry_text(entry, "title") == ""


class TestJavaScriptSourceTypes:
    """Tests for JavaScript/browser source type handling."""

    def test_js_source_types_defined(self):
        """JS source types include 'javascript' and 'browser'."""
        assert "javascript" in _JS_SOURCE_TYPES
        assert "browser" in _JS_SOURCE_TYPES

    def test_rss_not_in_js_types(self):
        """RSS is not considered a JS source type."""
        assert "rss" not in _JS_SOURCE_TYPES


class TestSourceModel:
    """Tests for Source model usage in collector."""

    def test_source_creation_rss(self):
        """Source model can be created with RSS type."""
        source = Source(
            name="TestSource",
            type="rss",
            url="https://example.com/feed",
        )
        assert source.name == "TestSource"
        assert source.type == "rss"
        assert source.url == "https://example.com/feed"

    def test_source_creation_javascript(self):
        """Source model can be created with JavaScript type."""
        source = Source(
            name="JSSource",
            type="javascript",
            url="https://example.com/page",
        )
        assert source.name == "JSSource"
        assert source.type == "javascript"

    def test_source_creation_browser(self):
        """Source model can be created with browser type."""
        source = Source(
            name="BrowserSource",
            type="browser",
            url="https://example.com/dynamic",
        )
        assert source.name == "BrowserSource"
        assert source.type == "browser"


class TestSourceSplitting:
    """Tests for source filtering before collection."""

    def test_collect_sources_skips_disabled_sources_and_reports_enabled_unsupported_sources(self):
        sources = [
            Source(name="Disabled", type="rss", url="https://example.com/feed", enabled=False),
            Source(name="MCPSource", type="mcp", url="https://example.com/mcp"),
        ]

        articles, errors = collect_sources(sources, category="movie")

        assert articles == []
        assert all("Disabled" not in error for error in errors)
        assert "MCPSource: Unsupported source type 'mcp'" in errors


class TestCollectorExceptions:
    """Tests for collector exception handling."""

    def test_source_error_message(self):
        """SourceError formats message with source name."""
        error = SourceError("TestSource", "Connection failed")
        assert "TestSource" in str(error)
        assert "Connection failed" in str(error)

    def test_network_error(self):
        """NetworkError can be raised with message."""
        error = NetworkError("Timeout occurred")
        assert "Timeout" in str(error)

    def test_parse_error(self):
        """ParseError can be raised with message."""
        error = ParseError("Invalid XML")
        assert "Invalid XML" in str(error)
