from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from movieradar.models import Article, CategoryConfig, Source
from movieradar.quality_report import build_quality_report, write_quality_report


def _article(
    *,
    source: str,
    title: str,
    published: datetime | None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=f"https://example.com/{source}/{title}".replace(" ", "-"),
        summary=title,
        published=published,
        source=source,
        category="movie",
        matched_entities=matched_entities or {},
    )


def test_build_quality_report_tracks_movie_event_statuses() -> None:
    now = datetime(2026, 4, 13, tzinfo=UTC)
    category = CategoryConfig(
        category_name="movie",
        display_name="Movie",
        sources=[
            Source(
                name="KOFIC 박스오피스",
                type="javascript",
                url="https://kobis.or.kr",
                content_type="boxoffice",
                config={"event_model": "box_office"},
            ),
            Source(
                name="What's on Netflix",
                type="rss",
                url="https://www.whats-on-netflix.com/feed/",
                content_type="release_calendar",
                info_purpose=["ott_release"],
                config={"event_model": "release_calendar"},
            ),
            Source(name="Decider", type="rss", url="https://decider.com/feed/"),
        ],
        entities=[],
    )
    articles = [
        _article(
            source="KOFIC 박스오피스",
            title="daily box office",
            published=now - timedelta(hours=8),
            matched_entities={"BoxOffice": ["box office"]},
        ),
        _article(
            source="What's on Netflix",
            title="coming to Netflix",
            published=now - timedelta(days=20),
            matched_entities={"Platform": ["Netflix"]},
        ),
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": ["box_office", "release_calendar"]
                },
                "freshness_sla": {
                    "box_office_days": 1,
                    "release_calendar_days": 14,
                },
            }
        },
        generated_at=now,
    )

    summary = report["summary"]
    assert summary["tracked_sources"] == 2
    assert summary["fresh_sources"] == 1
    assert summary["stale_sources"] == 1
    assert summary["not_tracked_sources"] == 1
    assert summary["box_office_events"] == 1
    assert summary["release_calendar_events"] == 1
    assert summary["movie_signal_event_count"] == 2
    assert summary["event_required_field_gap_count"] >= 1
    assert summary["daily_review_item_count"] >= 1
    assert report["events"][0]["canonical_key"]
    assert "required_field_gaps" in report["events"][0]


def test_write_quality_report_writes_latest_and_dated_json(tmp_path) -> None:
    report = {
        "category": "movie",
        "generated_at": "2026-04-13T00:00:00+00:00",
        "summary": {},
        "sources": [],
        "events": [],
    }

    paths = write_quality_report(report, output_dir=tmp_path, category_name="movie")

    assert paths["latest"].name == "movie_quality.json"
    assert paths["dated"].name == "movie_20260413_quality.json"
    assert json.loads(paths["latest"].read_text(encoding="utf-8"))["category"] == "movie"
