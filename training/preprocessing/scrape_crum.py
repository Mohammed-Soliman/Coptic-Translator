"""Crum dictionary scraper using query-based search."""

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
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_URL_TEMPLATE = "https://remnqymi.com/crum/?query={query}"
DEFAULT_RAW_OUTPUT = Path("data/raw/crum/crum_raw.json")
DEFAULT_CLEAN_OUTPUT = Path("data/dictionary/crum_clean.json")
DEFAULT_SOURCE_NAME = "Crum"
DEFAULT_LICENSE = "unknown"
DEFAULT_QUALITY = "silver"
DEFAULT_VERIFICATION_STATUS = "needs_review"

_COPTIC_RE = re.compile(r"[\u2C80-\u2CFF]+")
_WS_RE = re.compile(r"\s+")


@dataclass
class RawCrumPage:
    url: str
    query: str
    dialect: str
    status_code: int
    title: str
    visible_text: str
    headwords: list[str] = field(default_factory=list)
    gloss_candidates: list[str] = field(default_factory=list)
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


class _CrumHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._in_script = False
        self._in_style = False

        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()

        if tag == "title":
            self._in_title = True
            return
        if tag == "script":
            self._in_script = True
            return
        if tag == "style":
            self._in_style = True
            return
        if tag in {"p", "div", "section", "article", "li", "tr", "td", "br", "hr"}:
            self.text_parts.append("\n")
            return
        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            content = attr_map.get("content", "").strip()
            if content and (name or prop):
                self.meta[name or prop] = content

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_script = False
        elif tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._in_script or self._in_style:
            return

        text = data.strip()
        if not text:
            return

        if self._in_title:
            self.title_parts.append(text)
        else:
            self.text_parts.append(text)

    def title(self) -> str:
        return _WS_RE.sub(" ", " ".join(self.title_parts)).strip()

    def visible_text(self) -> str:
        text = " ".join(self.text_parts)
        text = html.unescape(text)
        text = _WS_RE.sub(" ", text)
        return text.strip()


def _fetch_url(url: str, timeout: int = 30) -> tuple[int, str]:
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
        return response.status, body


def _normalize_text(text: str) -> str:
    return _WS_RE.sub(" ", html.unescape(text)).strip()


def _extract_entries_from_text(visible_text: str) -> tuple[list[str], list[str]]:
    """Extract Coptic headwords and English gloss candidates from visible text."""
    headwords: list[str] = []
    glosses: list[str] = []

    lines = visible_text.splitlines()
    for line in lines:
        line = _normalize_text(line)
        if not line:
            continue

        if _COPTIC_RE.search(line):
            if len(line) < 50:
                headwords.append(line)
            glosses.append(line)
        elif len(line) > 5 and len(line) < 200:
            glosses.append(line)

    return headwords[:5], glosses[:10]


def scrape_crum_search(
    query: str,
    dialect: str,
    search_url_template: str,
    timeout: int = 30,
) -> RawCrumPage:
    """Scrape a single query/dialect combination."""
    encoded_query = quote(query.strip(), safe="")
    url = search_url_template.format(query=encoded_query)

    try:
        status_code, body = _fetch_url(url, timeout=timeout)
    except (HTTPError, URLError) as exc:
        logger.warning(
            "Request failed for query=%s dialect=%s: %s", query, dialect, exc
        )
        return RawCrumPage(
            url=url,
            query=query,
            dialect=dialect,
            status_code=getattr(exc, "code", 0),
            title="",
            visible_text="",
            headwords=[],
            gloss_candidates=[],
            sha256="",
            fetched_at_unix=time.time(),
        )

    parser = _CrumHTMLParser()
    parser.feed(body)

    visible_text = parser.visible_text()
    headwords, glosses = _extract_entries_from_text(visible_text)
    sha256 = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()

    return RawCrumPage(
        url=url,
        query=query,
        dialect=dialect,
        status_code=status_code,
        title=parser.title(),
        visible_text=visible_text,
        headwords=headwords,
        gloss_candidates=glosses,
        sha256=sha256,
        fetched_at_unix=time.time(),
    )


def build_clean_entries(raw_pages: list[RawCrumPage]) -> list[CleanDictionaryEntry]:
    """Convert raw pages into cleaned dictionary entries."""
    clean_entries: list[CleanDictionaryEntry] = []
    seen: set[tuple[str, str]] = set()

    for page in raw_pages:
        if page.status_code != 200 or not page.headwords:
            continue

        for headword in page.headwords:
            lemma = _normalize_text(headword)
            if not lemma:
                continue

            for gloss in page.gloss_candidates[:5]:
                gloss = _normalize_text(gloss)
                if not gloss or _COPTIC_RE.search(gloss):
                    continue

                key = (lemma.casefold(), gloss.casefold())
                if key in seen:
                    continue
                seen.add(key)

                notes = [f"query: {page.query}"]
                if page.dialect != "unknown":
                    notes.append(f"dialect: {page.dialect}")

                clean_entries.append(
                    CleanDictionaryEntry(
                        coptic=lemma,
                        lemma=lemma,
                        english=[gloss],
                        dialect=(
                            [page.dialect] if page.dialect != "unknown" else ["unknown"]
                        ),
                        part_of_speech=None,
                        gender=None,
                        sources=[
                            {
                                "name": DEFAULT_SOURCE_NAME,
                                "type": "dictionary_search",
                                "url": page.url,
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Crum using query-based search."
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        default=["n", "a", "b", "g", "d", "e", "z", "h"],
        help="Query terms to search for.",
    )
    parser.add_argument(
        "--dialects",
        nargs="*",
        default=["unknown"],
        help="Dialects (if supported by the site).",
    )
    parser.add_argument(
        "--search-url-template",
        default=DEFAULT_SEARCH_URL_TEMPLATE,
        help="URL template with {query} placeholder.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=DEFAULT_RAW_OUTPUT,
        help="Path to write raw scraped pages.",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help="Path to write cleaned entries.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between requests.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    raw_pages: list[RawCrumPage] = []

    for query in args.queries:
        for dialect in args.dialects:
            logger.info("Fetching query=%s dialect=%s", query, dialect)
            page = scrape_crum_search(
                query=query,
                dialect=dialect,
                search_url_template=args.search_url_template,
                timeout=args.timeout,
            )
            raw_pages.append(page)
            if args.delay > 0:
                time.sleep(args.delay)

    clean_entries = build_clean_entries(raw_pages)

    write_json(
        args.raw_output,
        {
            "source": DEFAULT_SOURCE_NAME,
            "license": DEFAULT_LICENSE,
            "search_url_template": args.search_url_template,
            "pages": [asdict(page) for page in raw_pages],
        },
    )

    write_json(
        args.clean_output,
        {
            "source": DEFAULT_SOURCE_NAME,
            "license": DEFAULT_LICENSE,
            "quality": DEFAULT_QUALITY,
            "verification_status": DEFAULT_VERIFICATION_STATUS,
            "entries": [asdict(entry) for entry in clean_entries],
        },
    )

    logger.info("Wrote raw output to %s", args.raw_output)
    logger.info("Wrote clean output to %s", args.clean_output)
    logger.info(
        "Scraped %d queries, extracted %d entries", len(raw_pages), len(clean_entries)
    )


if __name__ == "__main__":
    main()
