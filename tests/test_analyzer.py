from __future__ import annotations

from movieradar.analyzer import apply_entity_rules
from movieradar.models import Article, EntityDefinition


def _make_article(title: str = "", summary: str = "") -> Article:
    return Article(
        title=title,
        link="https://example.com/1",
        summary=summary,
        published=None,
        source="TestSource",
        category="test",
    )


def _make_entity(name: str, keywords: list[str]) -> EntityDefinition:
    return EntityDefinition(name=name, display_name=name, keywords=keywords)


def test_keyword_match():
    """Korean keyword in title triggers match."""
    article = _make_article(title="마블 신작 영화 개봉")
    entities = [_make_entity("마블", ["마블"])]
    results = apply_entity_rules([article], entities)
    assert len(results) == 1
    assert "마블" in results[0].matched_entities


def test_no_match():
    """Article without matching keywords has empty matched_entities."""
    article = _make_article(title="날씨 뉴스", summary="오늘 맑음")
    entities = [_make_entity("마블", ["마블"])]
    results = apply_entity_rules([article], entities)
    assert len(results) == 1
    assert results[0].matched_entities == {}


def test_case_insensitive():
    """ASCII keyword matching is case-insensitive."""
    article = _make_article(title="Marvel Movie Release")
    entities = [_make_entity("Marvel", ["marvel"])]
    results = apply_entity_rules([article], entities)
    assert "Marvel" in results[0].matched_entities


def test_multiple_entities():
    """Multiple entities can match the same article."""
    article = _make_article(
        title="마블과 DC 신작 비교",
        summary="어벤져스와 배트맨",
    )
    entities = [
        _make_entity("마블", ["마블"]),
        _make_entity("DC", ["배트맨"]),
    ]
    results = apply_entity_rules([article], entities)
    assert "마블" in results[0].matched_entities
    assert "DC" in results[0].matched_entities


def test_empty_articles():
    """Empty article list returns empty result."""
    entities = [_make_entity("테스트", ["키워드"])]
    results = apply_entity_rules([], entities)
    assert results == []


def test_keyword_in_summary():
    """Keyword in summary (not title) also triggers match."""
    article = _make_article(title="영화 뉴스", summary="넷플릭스 오리지널 시리즈")
    entities = [_make_entity("넷플릭스", ["넷플릭스"])]
    results = apply_entity_rules([article], entities)
    assert "넷플릭스" in results[0].matched_entities


def test_ascii_word_boundary():
    """ASCII keywords respect word boundaries."""
    article = _make_article(title="Marveled at the view")
    entities = [_make_entity("Marvel", ["marvel"])]
    results = apply_entity_rules([article], entities)
    # "marvel" should NOT match "Marveled" due to word boundary
    assert results[0].matched_entities == {}
