from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from movieradar.models import Article
from movieradar.storage import RadarStorage


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check_quality.py"
    spec = importlib.util.spec_from_file_location("movieradar_check_quality_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_quality_artifacts_uses_latest_stored_checkpoint(
    tmp_path: Path,
    capsys,
) -> None:
    project_root = tmp_path
    (project_root / "config" / "categories").mkdir(parents=True)

    (project_root / "config" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "database_path": "data/radar_data.duckdb",
                "report_dir": "reports",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_root / "config" / "categories" / "movie.yaml").write_text(
        yaml.safe_dump(
            {
                "category_name": "movie",
                "display_name": "Movie Radar",
                "sources": [
                    {
                        "id": "kofic_box_office",
                        "name": "KOFIC 박스오피스",
                        "type": "rss",
                        "url": "https://example.com/box-office.xml",
                        "content_type": "box_office",
                        "enabled": True,
                        "config": {
                            "event_model": "box_office",
                        },
                    }
                ],
                "entities": [],
                "data_quality": {
                    "quality_outputs": {
                        "tracked_event_models": ["box_office"],
                    }
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    article_time = datetime.now(UTC) - timedelta(days=30)
    db_path = project_root / "data" / "radar_data.duckdb"
    with RadarStorage(db_path) as storage:
        storage.upsert_articles(
            [
                Article(
                    title="Weekend box office update",
                    link="https://example.com/movie/box-office/1",
                    summary="Latest box office standings.",
                    published=article_time,
                    collected_at=article_time,
                    source="KOFIC 박스오피스",
                    category="movie",
                    matched_entities={"BoxOffice": ["box office"]},
                )
            ]
        )

    module = _load_script_module()
    paths, report = module.generate_quality_artifacts(project_root)

    assert Path(paths["latest"]).exists()
    assert Path(paths["dated"]).exists()
    assert report["summary"]["tracked_sources"] == 1
    assert report["summary"]["box_office_events"] == 1

    module.PROJECT_ROOT = project_root
    module.main()
    captured = capsys.readouterr()
    assert "quality_report=" in captured.out
    assert "tracked_sources=1" in captured.out
    assert "movie_signal_event_count=1" in captured.out
