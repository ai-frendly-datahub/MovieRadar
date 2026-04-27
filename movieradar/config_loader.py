from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml
from radar_core.models import (
    CategoryConfig,
    EntityDefinition,
    NotificationConfig,
    RadarSettings,
    Source,
)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read_yaml(path: Path) -> dict[str, object]:
    raw = cast(object, yaml.safe_load(path.read_text(encoding="utf-8")))
    if isinstance(raw, dict):
        return {str(k): v for k, v in cast(dict[object, object], raw).items()}
    return {}


def _str(d: dict[str, object], k: str, default: str = "") -> str:
    v = d.get(k)
    return v if isinstance(v, str) and v.strip() else default


def _bool(d: dict[str, object], k: str, default: bool = False) -> bool:
    value = d.get(k)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _float(d: dict[str, object], k: str, default: float = 1.0) -> float:
    value = d.get(k)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _str_list(d: dict[str, object], k: str) -> list[str]:
    value = d.get(k)
    if isinstance(value, str):
        values: list[object] = [value]
    elif isinstance(value, list):
        values = cast(list[object], value)
    elif isinstance(value, tuple | set):
        values = list(cast(tuple[object, ...] | set[object], value))
    else:
        values = []
    return [str(item).strip() for item in values if str(item).strip()]


def _dict(d: dict[str, object], k: str) -> dict[str, object]:
    value = d.get(k)
    if isinstance(value, dict):
        return {str(key): val for key, val in cast(dict[object, object], value).items()}
    return {}


def _dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, object]] = []
    for item in cast(list[object], value):
        if isinstance(item, dict):
            items.append({str(key): val for key, val in cast(dict[object, object], item).items()})
    return items


def _resolve_env_refs(value: object) -> object:
    if isinstance(value, str):
        import os
        import re

        result = value
        for match in re.finditer(r"\$\{([^}]+)\}", value):
            result = result.replace(match.group(0), os.environ.get(match.group(1), ""))
        return result
    if isinstance(value, dict):
        return {str(k): _resolve_env_refs(v) for k, v in cast(dict[object, object], value).items()}
    if isinstance(value, list):
        return [_resolve_env_refs(item) for item in cast(list[object], value)]
    return value


def _path(val: str) -> Path:
    p = Path(val).expanduser()
    return p if p.is_absolute() else (_PROJECT_ROOT / p).resolve()


def load_settings(config_path: Path | None = None) -> RadarSettings:
    f = config_path or _PROJECT_ROOT / "config" / "config.yaml"
    if not f.exists():
        raise FileNotFoundError(f"Config file not found: {f}")
    raw = _read_yaml(f)
    return RadarSettings(
        database_path=_path(_str(raw, "database_path", "data/radar_data.duckdb")),
        report_dir=_path(_str(raw, "report_dir", "reports")),
        raw_data_dir=_path(_str(raw, "raw_data_dir", "data/raw")),
        search_db_path=_path(_str(raw, "search_db_path", "data/search_index.db")),
    )


def load_category_config(category_name: str, categories_dir: Path | None = None) -> CategoryConfig:
    base = categories_dir or _PROJECT_ROOT / "config" / "categories"
    f = Path(base) / f"{category_name}.yaml"
    if not f.exists():
        raise FileNotFoundError(f"Category config not found: {f}")
    raw = _read_yaml(f)
    sources = [_parse_source(item) for item in _dict_items(raw.get("sources"))]
    entities = [_parse_entity(item) for item in _dict_items(raw.get("entities"))]
    dn = _str(raw, "display_name") or _str(raw, "category_name") or category_name
    return CategoryConfig(
        category_name=_str(raw, "category_name", category_name),
        display_name=dn,
        sources=sources,
        entities=entities,
    )


def load_category_quality_config(
    category_name: str,
    categories_dir: Path | None = None,
) -> dict[str, object]:
    base = categories_dir or _PROJECT_ROOT / "config" / "categories"
    f = Path(base) / f"{category_name}.yaml"
    if not f.exists():
        raise FileNotFoundError(f"Category config not found: {f}")
    raw = _read_yaml(f)
    quality_config: dict[str, object] = {}
    for key in ("data_quality", "source_backlog", "integration_candidates"):
        if key in raw:
            quality_config[key] = _resolve_env_refs(raw[key])
    return quality_config


def _parse_source(entry: dict[str, object]) -> Source:
    source_config = _dict(entry, "config")
    for key in (
        "event_model",
        "verification_role",
        "observed_date_field",
        "event_date_field",
        "merge_policy",
    ):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            source_config.setdefault(key, value.strip())

    canonical_key_fields = entry.get("canonical_key_fields")
    if isinstance(canonical_key_fields, list):
        source_config.setdefault(
            "canonical_key_fields",
            [
                str(item).strip()
                for item in cast(list[object], canonical_key_fields)
                if str(item).strip()
            ],
        )

    return Source(
        name=_str(entry, "name", "Unnamed"),
        type=_str(entry, "type", "rss"),
        url=_str(entry, "url"),
        id=_str(entry, "id"),
        enabled=_bool(entry, "enabled", True),
        language=_str(entry, "language"),
        country=_str(entry, "country"),
        region=_str(entry, "region"),
        trust_tier=_str(entry, "trust_tier", "T3_professional"),
        weight=_float(entry, "weight", 1.0),
        content_type=_str(entry, "content_type", "news"),
        collection_tier=_str(entry, "collection_tier", "C1_rss"),
        producer_role=_str(entry, "producer_role"),
        info_purpose=_str_list(entry, "info_purpose"),
        notes=_str(entry, "notes"),
        config=source_config,
    )


def _parse_entity(entry: dict[str, object]) -> EntityDefinition:
    kw_raw = entry.get("keywords", [])
    keywords = [
        str(keyword).strip()
        for keyword in (kw_raw if isinstance(kw_raw, list) else [])
        if str(keyword).strip()
    ]
    name = _str(entry, "name", "entity")
    return EntityDefinition(
        name=name,
        display_name=_str(entry, "display_name", name),
        keywords=keywords,
    )


def load_notification_config(config_path: Path | None = None) -> NotificationConfig:
    f = config_path or _PROJECT_ROOT / "config" / "notifications.yaml"
    if not f.exists():
        return NotificationConfig(enabled=False, channels=[])
    return NotificationConfig(enabled=False, channels=[])


__all__ = [
    "load_category_config",
    "load_category_quality_config",
    "load_notification_config",
    "load_settings",
]
