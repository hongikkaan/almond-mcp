"""Keyword matching for the curated source-directory catalogue."""
import re
import unicodedata


# Catalogue vocabulary, not a general translation or detail-content search.
KOREAN_TERMS = {
    "목재": ("timber", "wood"), "목구조": ("timber", "wood"),
    "벽": ("wall",), "바닥": ("floor",), "지붕": ("roof",),
    "접합": ("junction", "connection"), "단면": ("section",),
    "단열": ("thermal",), "차음": ("acoustic",), "내화": ("fire",),
    "창": ("window",), "창호": ("window", "door"), "문": ("door",),
    "설비": ("fixture",), "조경": ("landscape",), "제작": ("fabrication",),
    "조립": ("assembly",), "모듈": ("modular",), "가구": ("furniture",),
    "평면": ("plan",), "블록": ("block",), "심볼": ("symbol",),
    "기둥": ("column",), "보": ("beam",), "철골": ("steel",),
    "콘크리트": ("concrete",),
}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()))


def search_sources(sources: list[dict], query: str) -> dict:
    query_terms = tokens(query)
    if query.strip() and not query_terms:
        return {"status": "error", "error_code": "invalid_query", "query": query,
                "message": "The query contains no searchable words. Use an empty query to list sources.",
                "query_terms": [], "expanded_terms": [], "sources": []}
    expanded = {term for word in query_terms for term in KOREAN_TERMS.get(word, ())} - query_terms
    search_terms = query_terms | expanded
    matches = []
    for source in sources:
        haystack = unicodedata.normalize("NFKC", " ".join(
            [source["title"], *source["tags"], *source["formats"]])).casefold()
        matched = sorted(term for term in search_terms if term in haystack)
        if not search_terms or matched:
            matches.append({**source, "matched_terms": matched})
    matches.sort(key=lambda source: (-len(source["matched_terms"]), source["source_id"]))
    return {"status": "success", "query": query, "query_terms": sorted(query_terms),
            "expanded_terms": sorted(expanded), "sources": matches}
