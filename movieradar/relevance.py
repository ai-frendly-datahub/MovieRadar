from __future__ import annotations

from collections.abc import Iterable

from .models import Article, Source


TRACKED_EVENT_MODELS = {
    "reservation_ranking",
    "box_office",
    "ott_ranking",
    "release_calendar",
}
OPERATIONAL_CONTENT_TYPES = {
    "boxoffice",
    "box_office",
    "ott_ranking",
    "release_calendar",
    "reservation_ranking",
}
OPERATIONAL_PURPOSES = {
    "box_office",
    "korean_box_office",
    "ott_ranking",
    "ott_release",
    "release_calendar",
    "reservation_ranking",
}
STRUCTURED_MOVIE_SOURCES = {
    "KOFIC 박스오피스",
    "Box Office Mojo",
}
OTT_CONTEXT_SOURCES = {
    "Decider",
    "What's on Netflix",
}
REVIEW_SOURCE_NAMES = {
    "Collider",
    "Hollywood Reporter",
    "IndieWire",
    "Screen Rant",
    "Variety Film",
}
STRONG_ENTITY_NAMES = {
    "Award",
    "BoxOffice",
    "Director",
}
MOVIE_URL_TERMS = {
    "/box-office/",
    "/cinema/",
    "/criticism/movies/",
    "/film/",
    "/films/",
    "/movie-",
    "/movie/",
    "/movies/",
    "/movies/movie-news/",
    "/movies/movie-reviews/",
    "/theater/",
    "/theaters/",
    "-film-",
    "-movie-",
    "box-office",
    "film-review",
    "movie-review",
}
NON_MOVIE_URL_TERMS = {
    "/anime/",
    "/athletes/",
    "/basketball/",
    "/games/",
    "/manhwa/",
    "/music/",
    "/shopping/",
    "/shows/",
    "/sport/",
    "/sports/",
    "/tv/",
    "/tv-features/",
    "/tv-reviews/",
    "season-",
    "series-review",
}
OTT_RELEASE_URL_TERMS = {
    "/leaving-soon/",
    "/news/",
    "/top-10/",
    "/whats-new/",
}
FILM_GENERAL_STRONG_TERMS = {
    "academy award",
    "box office",
    "cannes",
    "cinema",
    "cinematic",
    "film",
    "films",
    "movie",
    "movies",
    "oscar",
    "premiere",
    "theater",
    "theaters",
    "theatrical",
    "trailer",
    "개봉",
    "관객",
    "박스오피스",
    "영화",
}
MOVIE_TEXT_STRONG_TERMS = FILM_GENERAL_STRONG_TERMS | {
    "biopic",
    "feature film",
    "film festival",
    "filmmaker",
    "filmmakers",
    "franchise",
    "grossing",
    "romcom",
    "superhero movie",
}
TV_EPISODE_TERMS = {
    "episode",
    "episodes",
    "recap",
    "season",
    "series",
    "showrunner",
    "spinoff",
    "spin-off",
}
INVALID_PAGE_TERMS = {
    "404",
    "access denied",
    "not found",
    "page not found",
    "request blocked",
    "service unavailable",
    "페이지를 찾을 수 없습니다",
}


def apply_source_context_entities(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    classified: list[Article] = []
    for article in articles:
        if article.category != "movie":
            classified.append(article)
            continue

        source = source_map.get(article.source)
        if source is None:
            classified.append(article)
            continue

        tags = _source_context_tags(source)
        if _has_movie_url_signal(article):
            tags.append("movie_url_context")
        if _has_movie_text_signal(article):
            tags.append("movie_text_context")
        if source.name in OTT_CONTEXT_SOURCES and _has_ott_release_url_signal(article):
            tags.append("ott_release_context")

        if tags:
            existing = article.matched_entities.get("SourceSignal", [])
            existing_values = existing if isinstance(existing, list) else [existing]
            merged = sorted({str(value) for value in existing_values} | set(tags))
            article.matched_entities["SourceSignal"] = merged
        classified.append(article)
    return classified


def filter_relevant_articles(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    filtered: list[Article] = []
    for article in articles:
        if article.category != "movie":
            filtered.append(article)
            continue

        source = source_map.get(article.source)
        if source is None or _is_invalid_page(article):
            continue

        event_model = _source_event_model(source)
        if source.name in STRUCTURED_MOVIE_SOURCES or event_model in {
            "box_office",
            "reservation_ranking",
        }:
            filtered.append(article)
            continue

        if _has_non_movie_url_signal(article) and not _has_movie_specific_signal(article):
            continue

        if _has_movie_specific_signal(article):
            filtered.append(article)
            continue

        if _has_movie_review_signal(article, source):
            filtered.append(article)
            continue

        if (
            source.name in OTT_CONTEXT_SOURCES
            and _has_ott_release_url_signal(article)
            and not _looks_like_tv_episode(article)
        ):
            filtered.append(article)
            continue
    return filtered


def _has_movie_specific_signal(article: Article) -> bool:
    if _has_movie_url_signal(article):
        return True
    if _has_movie_text_signal(article):
        return True

    entities = set(article.matched_entities)
    if entities & STRONG_ENTITY_NAMES:
        return True
    if "FilmGeneral" in entities:
        matched_terms = _entity_terms(article, "FilmGeneral")
        return bool(matched_terms & FILM_GENERAL_STRONG_TERMS)
    return False


def _has_movie_url_signal(article: Article) -> bool:
    link = (article.link or "").lower()
    return any(term in link for term in MOVIE_URL_TERMS)


def _has_ott_release_url_signal(article: Article) -> bool:
    link = (article.link or "").lower()
    return any(term in link for term in OTT_RELEASE_URL_TERMS)


def _has_non_movie_url_signal(article: Article) -> bool:
    link = (article.link or "").lower()
    return any(term in link for term in NON_MOVIE_URL_TERMS)


def _has_movie_text_signal(article: Article) -> bool:
    haystack = f"{article.title} {article.summary}".lower()
    return any(term in haystack for term in MOVIE_TEXT_STRONG_TERMS)


def _has_movie_review_signal(article: Article, source: Source) -> bool:
    if source.name not in REVIEW_SOURCE_NAMES:
        return False
    haystack = f"{article.title} {article.link}".lower()
    return "review" in haystack and not _looks_like_tv_episode(article)


def _looks_like_tv_episode(article: Article) -> bool:
    haystack = f"{article.title} {article.summary} {article.link}".lower()
    return any(term in haystack for term in TV_EPISODE_TERMS) and not _has_movie_url_signal(article)


def _is_invalid_page(article: Article) -> bool:
    title = (article.title or "").strip().lower()
    summary = (article.summary or "").strip().lower()
    return any(term in title or term in summary for term in INVALID_PAGE_TERMS)


def _source_context_tags(source: Source) -> list[str]:
    tags = {purpose for purpose in source.info_purpose if purpose in OPERATIONAL_PURPOSES}
    content_type = source.content_type.lower()
    event_model = _source_event_model(source)

    if event_model in TRACKED_EVENT_MODELS:
        tags.add(event_model)
    if content_type in OPERATIONAL_CONTENT_TYPES:
        tags.add(content_type)
    if source.name in STRUCTURED_MOVIE_SOURCES:
        tags.add("official_movie_data")
    return sorted(tags)


def _source_event_model(source: Source) -> str:
    raw = source.config.get("event_model")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    content_type = source.content_type.lower()
    purposes = {purpose.lower() for purpose in source.info_purpose}
    if content_type in {"boxoffice", "box_office"} or "box_office" in purposes:
        return "box_office"
    if content_type == "reservation_ranking" or "reservation_ranking" in purposes:
        return "reservation_ranking"
    if content_type == "ott_ranking" or "ott_ranking" in purposes:
        return "ott_ranking"
    if content_type == "release_calendar" or {"release_calendar", "ott_release"} & purposes:
        return "release_calendar"
    return ""


def _entity_terms(article: Article, key: str) -> set[str]:
    values = article.matched_entities.get(key, [])
    if not isinstance(values, list):
        return set()
    return {str(value).strip().lower() for value in values if str(value).strip()}
