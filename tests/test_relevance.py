from __future__ import annotations

from movieradar.models import Article, Source
from movieradar.relevance import apply_source_context_entities, filter_relevant_articles


def _article(
    *,
    title: str,
    source: str = "Hollywood Reporter",
    category: str = "movie",
    link: str | None = None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=link or f"https://example.com/{title.replace(' ', '-')}",
        summary=title,
        published=None,
        source=source,
        category=category,
        matched_entities=matched_entities or {},
    )


def test_apply_source_context_entities_adds_structured_source_signal() -> None:
    article = _article(
        title="KOFIC box office",
        source="KOFIC 박스오피스",
        matched_entities={"BoxOffice": ["박스오피스"]},
    )
    source = Source(
        name="KOFIC 박스오피스",
        type="javascript",
        url="https://kobis.or.kr",
        content_type="boxoffice",
        info_purpose=["box_office"],
        config={"event_model": "box_office"},
    )

    classified = apply_source_context_entities([article], [source])

    assert classified[0].matched_entities["SourceSignal"] == [
        "box_office",
        "boxoffice",
        "movie_text_context",
        "movie_url_context",
        "official_movie_data",
    ]


def test_filter_relevant_articles_excludes_broad_tv_and_keeps_movie_signals() -> None:
    sources = [
        Source(
            name="Hollywood Reporter",
            type="rss",
            url="https://www.hollywoodreporter.com/feed/",
        ),
        Source(name="Collider", type="rss", url="https://collider.com/feed/"),
        Source(name="Box Office Mojo", type="javascript", url="https://www.boxofficemojo.com/"),
    ]
    articles = [
        _article(
            title="You, Me & Tuscany Review",
            link="https://www.hollywoodreporter.com/movies/movie-reviews/you-me-tuscany-review/",
            matched_entities={"FilmGeneral": ["movie"]},
        ),
        _article(
            title="Abbott Elementary relationship twist",
            link="https://www.hollywoodreporter.com/tv/tv-features/abbott-elementary/",
            matched_entities={},
        ),
        _article(
            title="10 Most Intense Gangster Movies, Ranked",
            source="Collider",
            link="https://collider.com/most-intense-gangster-movies-ranked/",
            matched_entities={"FilmGeneral": ["movies"]},
        ),
        _article(
            title="Home - Box Office Mojo",
            source="Box Office Mojo",
            link="https://www.boxofficemojo.com/",
            matched_entities={"BoxOffice": ["box office"]},
        ),
    ]

    filtered = filter_relevant_articles(
        apply_source_context_entities(articles, sources),
        sources,
    )

    assert [article.title for article in filtered] == [
        "You, Me & Tuscany Review",
        "10 Most Intense Gangster Movies, Ranked",
        "Home - Box Office Mojo",
    ]


def test_filter_relevant_articles_keeps_filmmakers_commentary() -> None:
    source = Source(
        name="IndieWire",
        type="rss",
        url="https://www.indiewire.com/feed/",
        info_purpose=["review", "industry_news"],
    )
    article = _article(
        title="When Creative Geniuses Start Making AI Slop - Opinion",
        source="IndieWire",
        link="https://www.indiewire.com/features/commentary/what-happens-aging-artists-embrace-ai-opinion/",
        matched_entities={},
    )
    article.summary = "The trend is prevalent among great filmmakers, too."

    filtered = filter_relevant_articles(
        apply_source_context_entities([article], [source]),
        [source],
    )

    assert filtered == [article]
    assert filtered[0].matched_entities["SourceSignal"] == ["movie_text_context"]
