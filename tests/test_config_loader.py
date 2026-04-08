from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from movieradar.config_loader import (
    load_category_config,
    load_notification_config,
    load_settings,
)


class TestLoadSettings:
    """Unit tests for load_settings function."""

    def test_load_settings_file_not_found(self, tmp_path):
        """Raises FileNotFoundError when config file is missing."""
        missing_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_settings(missing_path)
        assert "Config file not found" in str(exc_info.value)

    def test_load_settings_valid_config(self, tmp_path):
        """Loads settings from a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
database_path: data/test.duckdb
report_dir: reports
raw_data_dir: data/raw
search_db_path: data/search.db
"""
        )
        settings = load_settings(config_file)
        assert settings.database_path.name == "test.duckdb"
        assert settings.report_dir.name == "reports"

    def test_load_settings_defaults(self, tmp_path):
        """Uses defaults for missing keys."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        settings = load_settings(config_file)
        assert "radar_data.duckdb" in str(settings.database_path)

    def test_load_settings_empty_values_use_defaults(self, tmp_path):
        """Empty string values fall back to defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
database_path: ""
report_dir: "   "
"""
        )
        settings = load_settings(config_file)
        assert "radar_data.duckdb" in str(settings.database_path)


class TestLoadCategoryConfig:
    """Unit tests for load_category_config function."""

    def test_load_category_not_found(self, tmp_path):
        """Raises FileNotFoundError when category file is missing."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_category_config("nonexistent", categories_dir=tmp_path)
        assert "Category config not found" in str(exc_info.value)

    def test_load_category_valid(self, tmp_path):
        """Loads a valid category configuration."""
        cat_file = tmp_path / "movie.yaml"
        cat_file.write_text(
            """
category_name: movie
display_name: Movies
sources:
  - name: MovieSource
    type: rss
    url: https://example.com/feed
entities:
  - name: Entity1
    display_name: Entity One
    keywords:
      - keyword1
      - keyword2
"""
        )
        config = load_category_config("movie", categories_dir=tmp_path)
        assert config.category_name == "movie"
        assert config.display_name == "Movies"
        assert len(config.sources) == 1
        assert config.sources[0].name == "MovieSource"
        assert len(config.entities) == 1
        assert config.entities[0].name == "Entity1"
        assert "keyword1" in config.entities[0].keywords

    def test_load_category_empty_sources(self, tmp_path):
        """Handles category with no sources."""
        cat_file = tmp_path / "empty.yaml"
        cat_file.write_text(
            """
category_name: empty
"""
        )
        config = load_category_config("empty", categories_dir=tmp_path)
        assert config.category_name == "empty"
        assert config.sources == []
        assert config.entities == []

    def test_load_category_javascript_source(self, tmp_path):
        """Loads category with JavaScript source type."""
        cat_file = tmp_path / "dynamic.yaml"
        cat_file.write_text(
            """
category_name: dynamic
sources:
  - name: DynamicSource
    type: javascript
    url: https://example.com/dynamic
"""
        )
        config = load_category_config("dynamic", categories_dir=tmp_path)
        assert config.sources[0].type == "javascript"

    def test_load_category_browser_source(self, tmp_path):
        """Loads category with browser source type."""
        cat_file = tmp_path / "browser.yaml"
        cat_file.write_text(
            """
category_name: browser
sources:
  - name: BrowserSource
    type: browser
    url: https://example.com/spa
"""
        )
        config = load_category_config("browser", categories_dir=tmp_path)
        assert config.sources[0].type == "browser"

    def test_load_category_display_name_fallback(self, tmp_path):
        """Falls back to category_name when display_name is missing."""
        cat_file = tmp_path / "simple.yaml"
        cat_file.write_text(
            """
category_name: simple
"""
        )
        config = load_category_config("simple", categories_dir=tmp_path)
        assert config.display_name == "simple"

    def test_load_category_entity_keywords_empty(self, tmp_path):
        """Handles entities with empty or missing keywords."""
        cat_file = tmp_path / "nokw.yaml"
        cat_file.write_text(
            """
category_name: nokw
entities:
  - name: NoKeywords
    display_name: No Keywords
"""
        )
        config = load_category_config("nokw", categories_dir=tmp_path)
        assert len(config.entities) == 1
        assert config.entities[0].keywords == []

    def test_load_category_entity_keywords_whitespace(self, tmp_path):
        """Strips whitespace from keywords."""
        cat_file = tmp_path / "ws.yaml"
        cat_file.write_text(
            """
category_name: ws
entities:
  - name: WithSpaces
    keywords:
      - "  spaced  "
      - ""
      - "valid"
"""
        )
        config = load_category_config("ws", categories_dir=tmp_path)
        # Empty strings should be filtered out
        keywords = config.entities[0].keywords
        assert "spaced" in keywords
        assert "valid" in keywords
        assert "" not in keywords

    def test_load_category_source_defaults(self, tmp_path):
        """Uses defaults for missing source fields."""
        cat_file = tmp_path / "defaults.yaml"
        cat_file.write_text(
            """
category_name: defaults
sources:
  - url: https://example.com/feed
"""
        )
        config = load_category_config("defaults", categories_dir=tmp_path)
        assert config.sources[0].name == "Unnamed"
        assert config.sources[0].type == "rss"

    def test_load_category_korean_content(self, tmp_path):
        """Handles Korean text in category configuration."""
        cat_file = tmp_path / "korean.yaml"
        cat_file.write_text(
            """
category_name: korean
display_name: 영화
sources:
  - name: 한국영화소스
    type: rss
    url: https://example.com/feed
entities:
  - name: 한국영화
    display_name: 한국 영화
    keywords:
      - 영화
      - 한국
"""
        )
        config = load_category_config("korean", categories_dir=tmp_path)
        assert config.display_name == "영화"
        assert config.sources[0].name == "한국영화소스"
        assert "영화" in config.entities[0].keywords


class TestLoadNotificationConfig:
    """Unit tests for load_notification_config function."""

    def test_load_notification_missing_file(self, tmp_path):
        """Returns disabled config when file is missing."""
        missing_path = tmp_path / "notifications.yaml"
        config = load_notification_config(missing_path)
        assert config.enabled is False
        assert config.channels == []

    def test_load_notification_existing_file(self, tmp_path):
        """Returns disabled config even when file exists (current implementation)."""
        notif_file = tmp_path / "notifications.yaml"
        notif_file.write_text(
            """
enabled: true
channels:
  - type: telegram
    token: xxx
"""
        )
        config = load_notification_config(notif_file)
        # Current implementation always returns disabled
        assert config.enabled is False
