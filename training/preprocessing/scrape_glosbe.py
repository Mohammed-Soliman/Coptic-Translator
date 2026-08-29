"""Glosbe scraping helper for candidate Coptic-English dictionary entries.

This script is intentionally conservative:
- it only fetches public pages
- it respects a configurable delay
- it writes raw and cleaned JSON separately
- it does not try to bypass anti-bot protections

Use this as a source of Silver / needs_review candidates, not Gold data.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://glosbe.com/cop/en/{query}"
DEFAULT_RAW_OUTPUT = Path("data/raw/glosbe/glosbe_raw.json")
DEFAULT_CLEAN_OUTPUT = Path("data/dictionary/glosbe_clean.json")
DEFAULT_SOURCE_NAME = "Glosbe"
DEFAULT_LICENSE = "unknown"
DEFAULT_QUALITY = "silver"
DEFAULT_VERIFICATION_STATUS = "needs_review"

_COPTIC_RE = re.compile(r"[\u2C80-\u2CFF]+")
_LATIN_RE = re.compile(r"[A-Za-z]")
_WS_RE = re.compile(r"\s+")
_INTERESTING_KEYS = {
    "example",
    "examples",
    "translation",
    "translations",
    "meaning",
    "meanings",
    "definition",
    "definitions",
    "gloss",
    "glosses",
    "phrase",
    "phrases",
    "text",
    "label",
    "content",
}


@dataclass
class RawGlosbePage:
    query: str
    url: str
    status_code: int
    title: str
    description: str
    visible_text: str
    json_strings: list[str] = field(default_factory=list)
    extracted_pairs: list[dict[str, str]] = field(default_factory=list)
    sha256: str = ""
    fetched_at_unix: float = 0.0


@dataclass
class CleanDictionaryEntry:
    coptic: str
    lemma: str
    english: list[str]
    dialect: list[str]
    part_of_speech: str | None
    gender: str | None
    sources: list[dict[str, Any]]
    quality: str
    verification_status: str
    notes: list[str] = field(default_factory=list)


class _GlosbeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._in_script = False
        self._current_script_type: str | None = None
        self.title_parts: list[str] = []
        self.script_parts: list[str] = []
        self.text_parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}

        if tag.lower() == "title":
            self._in_title = True
            return

        if tag.lower() == "script":
            self._in_script = True
            self._current_script_type = attr_map.get("type", "").lower()
            return

        if tag.lower() == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            content = attr_map.get("content", "").strip()
            if content and (name or prop):
                self.meta[name or prop] = content
            return

        if tag.lower() in {"br", "p", "div", "section", "article", "li", "tr", "td", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script":
            self._in_script = False
            self._current_script_type = None

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._in_title:
            self.title_parts.append(data)
        elif self._in_script:
            self.script_parts.append(data)
        else:
            self.text_parts.append(data)

    def visible_text(self) -> str:
        text = " ".join(self.text_parts)
        text = html.unescape(text)
        text = _WS_RE.sub(" ", text)
        return text.strip()

    def title(self) -> str:
        return _WS_RE.sub(" ", "".join(self.title_parts)).strip()

    def description(self) -> str:
        return self.meta.get("description") or self.meta.get("og:description") or ""


def _fetch_url(url: str, timeout: int = 30) -> tuple[int, str, dict[str, str]]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        headers = {key: value for key, value in response.headers.items()}
        return response.status, body, headers


def _extract_json_scripts(raw_html: str) -> list[str]:
    candidates: list[str] = []

    patterns = [
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL):
            snippet = html.unescape(match).strip()
            if snippet:
                candidates.append(snippet)

    return candidates


def _collect_interesting_strings(value: Any, out: list[str], key: str | None = None) -> None:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_key_str = str(child_key).lower()
            if child_key_str in _INTERESTING_KEYS:
                if isinstance(child_value, str):
                    out.append(child_value)
                elif isinstance(child_value, list):
                    for item in child_value:
                        if isinstance(item, (str, int, float)):
                            out.append(str(item))
                elif isinstance(child_value, dict):
                    _collect_interesting_strings(child_value, out, child_key_str)
            _collect_interesting_strings(child_value, out, child_key_str)
    elif isinstance(value, list):
        for item in value:
            _collect_interesting_strings(item, out, key)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return
        if _COPTIC_RE.search(text) or (_LATIN_RE.search(text) and len(text) < 200):
            out.append(text)


def _parse_json_payloads(json_strings: Iterable[str]) -> list[str]:
    results: list[str] = []

    for payload in json_strings:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue
        _collect_interesting_strings(parsed, results)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in results:
        normalized = _normalize_text(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _normalize_text(text: str) -> str:
    return _WS_RE.sub(" ", html.unescape(text)).strip()


def _split_candidate_pair(text: str) -> tuple[str | None, str | None]:
    separators = [" → ", " — ", " – ", " - ", " = ", " : ", " | ", "\t"]
    candidate = _normalize_text(text)

    for separator in separators:
        if separator in candidate:
            left, right = candidate.split(separator, 1)
            left = left.strip(" -—:|→")
            right = right.strip(" -—:|→")
            if _COPTIC_RE.search(left) and _LATIN_RE.search(right):
                return left, right
            if _COPTIC_RE.search(right) and _LATIN_RE.search(left):
                return right, left

    coptic_bits = _COPTIC_RE.findall(candidate)
    latin_bits = _LATIN_RE.findall(candidate)
    if coptic_bits and latin_bits:
        coptic = max(coptic_bits, key=len)
        english = candidate.replace(coptic, "", 1).strip(" -—:|→")
        return coptic, english or None

    return None, None


def _extract_candidate_pairs(visible_text: str, json_strings: list[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    lines = [line.strip() for line in visible_text.splitlines()]
    all_texts = [line for line in lines if line]

    for json_text in json_strings:
        all_texts.append(json_text)

    for text in all_texts:
        if len(text) < 2:
            continue

        coptic, english = _split_candidate_pair(text)
        if not coptic:
            continue

        key = (coptic, english or "")
        if key in seen:
            continue
        seen.add(key)

        candidates.append(
            {
                "coptic": coptic,
                "english": english or "",
                "source_excerpt": _normalize_text(text),
            }
        )

    return candidates


def scrape_glosbe_page(query: str, base_url_template: str, timeout: int = 30) -> RawGlosbePage:
    encoded_query = quote(query.strip(), safe="")
    url = base_url_template.format(query=encoded_query, raw_query=query.strip())

    try:
        status_code, body, _headers = _fetch_url(url, timeout=timeout)
    except HTTPError as exc:
        logger.warning("HTTP error for %s: %s", url, exc)
        return RawGlosbePage(
            query=query,
            url=url,
            status_code=exc.code,
            title="",
            description="",
            visible_text="",
            json_strings=[],
            extracted_pairs=[],
            sha256="",
            fetched_at_unix=time.time(),
        )
    except URLError as exc:
        logger.warning("Network error for %s: %s", url, exc)
        return RawGlosbePage(
            query=query,
            url=url,
            status_code=0,
            title="",
            description="",
            visible_text="",
            json_strings=[],
            extracted_pairs=[],
            sha256="",
            fetched_at_unix=time.time(),
        )

    parser = _GlosbeHTMLParser()
    parser.feed(body)

    visible_text = parser.visible_text()
    json_strings = _extract_json_scripts(body)
    extracted_pairs = _extract_candidate_pairs(visible_text, _parse_json_payloads(json_strings))

    sha256 = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()

    return RawGlosbePage(
        query=query,
        url=url,
        status_code=status_code,
        title=parser.title(),
        description=parser.description(),
        visible_text=visible_text,
        json_strings=json_strings,
        extracted_pairs=extracted_pairs,
        sha256=sha256,
        fetched_at_unix=time.time(),
    )


def build_clean_entries(raw_pages: list[RawGlosbePage]) -> list[CleanDictionaryEntry]:
    clean_entries: list[CleanDictionaryEntry] = []
    seen: set[tuple[str, str]] = set()

    for page in raw_pages:
        for pair in page.extracted_pairs:
            coptic = _normalize_text(pair.get("coptic", ""))
            english = _normalize_text(pair.get("english", ""))

            if not coptic:
                continue

            key = (coptic.casefold(), english.casefold())
            if key in seen:
                continue
            seen.add(key)

            english_values = [english] if english else []
            notes = []
            if pair.get("source_excerpt"):
                notes.append(f"excerpt: {pair['source_excerpt']}")
            if page.title:
                notes.append(f"title: {page.title}")

            clean_entries.append(
                CleanDictionaryEntry(
                    coptic=coptic,
                    lemma=coptic,
                    english=english_values,
                    dialect=["unknown"],
                    part_of_speech=None,
                    gender=None,
                    sources=[
                        {
                            "name": DEFAULT_SOURCE_NAME,
                            "type": "secondary_web_source",
                            "url": page.url,
                            "query": page.query,
                            "status_code": page.status_code,
                            "sha256": page.sha256,
                            "license": DEFAULT_LICENSE,
                            "verified": False,
                        }
                    ],
                    quality=DEFAULT_QUALITY,
                    verification_status=DEFAULT_VERIFICATION_STATUS,
                    notes=notes,
                )
            )

    return clean_entries


def load_queries_from_seed_file(path: Path, top_n: int) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(path)

    raw = json.loads(path.read_text(encoding="utf-8"))

    queries: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                queries.append(item)
            elif isinstance(item, dict):
                lemma = item.get("lemma") or item.get("coptic") or item.get("surface")
                if isinstance(lemma, str):
                    queries.append(lemma)

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = query.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)

    return deduped[:top_n]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Glosbe candidate Coptic entries.")
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=None,
        help="Optional JSON file containing lemmas/queries, for example data/corpus/lemma_frequencies.json.",
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        default=None,
        help="Explicit query terms to scrape.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=50,
        help="Number of seed queries to use from --seed-file.",
    )
    parser.add_argument(
        "--base-url-template",
        default=DEFAULT_BASE_URL,
        help="Glosbe URL template. Use {query} for the URL-encoded query.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=DEFAULT_RAW_OUTPUT,
        help="Path to write raw scraped pages JSON.",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help="Path to write cleaned dictionary JSON.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--source-name",
        default=DEFAULT_SOURCE_NAME,
        help="Source label to write into output metadata.",
    )
    parser.add_argument(
        "--license",
        default=DEFAULT_LICENSE,
        help="License label to write into output metadata.",
    )
    parser.add_argument(
        "--quality",
        default=DEFAULT_QUALITY,
        help="Quality label for cleaned entries.",
    )
    parser.add_argument(
        "--verification-status",
        default=DEFAULT_VERIFICATION_STATUS,
        help="Verification label for cleaned entries.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on the number of queries processed.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    queries: list[str] = []
    if args.queries:
        queries.extend(args.queries)

    if args.seed_file:
        queries.extend(load_queries_from_seed_file(args.seed_file, args.top_n))

    deduped_queries: list[str] = []
    seen_queries: set[str] = set()
    for query in queries:
        normalized = query.strip()
        if normalized and normalized not in seen_queries:
            seen_queries.add(normalized)
            deduped_queries.append(normalized)

    if args.limit > 0:
        deduped_queries = deduped_queries[: args.limit]

    if not deduped_queries:
        raise SystemExit("No queries supplied. Use --queries or --seed-file.")

    raw_pages: list[RawGlosbePage] = []
    for index, query in enumerate(deduped_queries, start=1):
        logger.info("Scraping %d/%d: %s", index, len(deduped_queries), query)
        page = scrape_glosbe_page(query, args.base_url_template, timeout=args.timeout)
        raw_pages.append(page)
        if args.delay > 0 and index < len(deduped_queries):
            time.sleep(args.delay)

    clean_entries = build_clean_entries(raw_pages)

    write_json(
        args.raw_output,
        {
            "source": args.source_name,
            "license": args.license,
            "queries": deduped_queries,
            "pages": [asdict(page) for page in raw_pages],
        },
    )

    write_json(
        args.clean_output,
        {
            "source": args.source_name,
            "license": args.license,
            "quality": args.quality,
            "verification_status": args.verification_status,
            "entries": [asdict(entry) for entry in clean_entries],
        },
    )

    logger.info("Wrote raw output to %s", args.raw_output)
    logger.info("Wrote clean output to %s", args.clean_output)
    logger.info("Extracted %d cleaned entries", len(clean_entries))


if __name__ == "__main__":
    main()