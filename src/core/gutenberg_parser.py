from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, Comment, Tag

from src.core.parser_artifacts import write_parser_artifacts
from src.core.text_parser import ParsedTextChapter, ParsedTextDocument

MAX_WORDS_PER_CHAPTER = 4000
BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "li", "pre")
GUTENBERG_TITLE_PREFIX = "the project gutenberg ebook of"
FRONT_MATTER_MIN_WORDS = 40


@dataclass(frozen=True)
class _HtmlCandidate:
    member_name: str
    html_text: str
    score: int
    size: int


@dataclass(frozen=True)
class _Block:
    text: str
    is_heading: bool


def parse_gutenberg_zip(
    file_path: str,
    output_dir: Optional[str] = None,
    max_words_per_chapter: int = MAX_WORDS_PER_CHAPTER,
) -> ParsedTextDocument:
    candidate, cover_filename = _load_gutenberg_assets(file_path, output_dir)
    soup = BeautifulSoup(candidate.html_text, "html.parser")
    cleanup_counts = _cleanup_gutenberg_soup(soup)

    fallback_title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").strip() or "Untitled"
    title, title_source = _resolve_title(soup, fallback_title)
    author, author_source = _resolve_author(soup)
    blocks = _extract_blocks(soup, title=title, author=author)
    chapters, parse_report = _build_chapters(blocks, max_words_per_chapter=max_words_per_chapter)

    if output_dir:
        report_payload = {
            "title": title,
            "title_source": title_source,
            "author": author,
            "author_source": author_source,
            "selected_html_member": candidate.member_name,
            "chapter_count": len(chapters),
            "chapter_titles": [chapter.title for chapter in chapters],
            "explicit_chapter_markers": parse_report["explicit_chapter_markers"],
            "fallback_split_used": parse_report["fallback_split_used"],
            "removed_boilerplate_sections": cleanup_counts["boilerplate_sections"],
            "removed_toc_blocks": cleanup_counts["toc_blocks"],
            "removed_footnote_blocks": cleanup_counts["footnote_blocks"],
            "removed_footnote_refs": cleanup_counts["footnote_refs"],
            "warnings": parse_report["warnings"],
        }
        write_parser_artifacts(output_dir, _render_cleaned_text(title, author, blocks), report_payload)

    return ParsedTextDocument(
        title=title,
        author=author,
        format="zip",
        chapters=chapters,
        cover_filename=cover_filename,
    )


def _load_gutenberg_assets(file_path: str, output_dir: Optional[str]) -> Tuple[_HtmlCandidate, Optional[str]]:
    with zipfile.ZipFile(file_path) as archive:
        html_candidates = _read_html_candidates(archive)
        if not html_candidates:
            raise ValueError("ZIP does not contain any Gutenberg HTML files")

        best_candidate = max(html_candidates, key=lambda candidate: (candidate.score, candidate.size))
        cover_filename = _extract_cover_from_zip(archive, output_dir) if output_dir else None
        return best_candidate, cover_filename


def _read_html_candidates(archive: zipfile.ZipFile) -> List[_HtmlCandidate]:
    candidates: List[_HtmlCandidate] = []
    for member in archive.infolist():
        if member.is_dir() or not _safe_zip_member(member.filename):
            continue
        if not member.filename.lower().endswith((".html", ".htm")):
            continue

        html_text = archive.read(member.filename).decode("utf-8", errors="ignore")
        score = _score_html_candidate(member.filename, html_text)
        candidates.append(
            _HtmlCandidate(
                member_name=member.filename,
                html_text=html_text,
                score=score,
                size=member.file_size,
            )
        )

    return candidates


def _score_html_candidate(member_name: str, html_text: str) -> int:
    lower_text = html_text.lower()
    score = 0
    if "project gutenberg" in lower_text:
        score += 5
    if "<body" in lower_text:
        score += 2
    if re.search(r"<h1\b", lower_text):
        score += 2
    if re.search(r'id=["\'](?:chap|pref|book|part)', lower_text):
        score += 3
    if "contents" in lower_text or "table of contents" in lower_text:
        score += 1
    if member_name.lower().endswith("images.html"):
        score += 1
    score += min(lower_text.count("<p"), 200) // 20
    return score


def _cleanup_gutenberg_soup(soup: BeautifulSoup) -> Dict[str, int]:
    counts = {
        "boilerplate_sections": 0,
        "toc_blocks": 0,
        "footnote_blocks": 0,
        "footnote_refs": 0,
    }

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    for tag in soup.find_all(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for tag in list(soup.find_all(_is_gutenberg_boilerplate_tag)):
        counts["boilerplate_sections"] += 1
        tag.decompose()

    counts["toc_blocks"] += _remove_table_of_contents(soup)

    for tag in list(soup.find_all(_is_footnote_block_tag)):
        counts["footnote_blocks"] += 1
        tag.decompose()

    for tag in soup.find_all(["img", "figure"]):
        tag.decompose()

    for anchor in list(soup.find_all("a")):
        href = (anchor.get("href") or "").strip()
        anchor_id = (anchor.get("id") or "").strip()
        classes = {value.casefold() for value in anchor.get("class", [])}
        anchor_text = _normalize_whitespace(anchor.get_text(" ", strip=True))

        if _is_footnote_reference(href=href, anchor_id=anchor_id, classes=classes, text=anchor_text):
            counts["footnote_refs"] += 1
            anchor.decompose()
            continue

        if href.startswith("#") or anchor_id.startswith(("chap", "pref", "part", "book")):
            anchor.unwrap()

    for tag in list(soup.find_all("sup")):
        sup_text = _normalize_whitespace(tag.get_text(" ", strip=True))
        if re.fullmatch(r"\[?\d+[A-Za-z]?\]?", sup_text):
            counts["footnote_refs"] += 1
            tag.decompose()

    return counts


def _remove_table_of_contents(soup: BeautifulSoup) -> int:
    removed = 0
    for heading in list(soup.find_all(re.compile(r"^h[1-6]$"))):
        heading_text = _normalize_whitespace(heading.get_text(" ", strip=True)).casefold()
        if heading_text not in {"contents", "table of contents"}:
            continue

        removed += 1
        sibling = heading.find_next_sibling()
        heading.decompose()

        while sibling and _looks_like_toc_block(sibling):
            current = sibling
            sibling = current.find_next_sibling()
            removed += 1
            current.decompose()

    return removed


def _extract_blocks(soup: BeautifulSoup, title: str, author: Optional[str]) -> List[_Block]:
    body = soup.body or soup
    blocks: List[_Block] = []
    seen_texts: set[str] = set()
    title_casefold = title.casefold()
    author_casefold = author.casefold() if author else None

    for element in body.find_all(BLOCK_TAGS):
        text = _normalize_block_text(element.get_text(" ", strip=True))
        if not text:
            continue
        if text.casefold() == title_casefold:
            continue
        if author_casefold and text.casefold() in {author_casefold, f"by {author_casefold}"}:
            continue
        if _is_audio_hostile_block(text):
            continue
        if text in seen_texts and element.name in {"h1", "h2", "h3"}:
            continue

        blocks.append(_Block(text=text, is_heading=element.name in {"h1", "h2", "h3", "h4", "h5", "h6"}))
        seen_texts.add(text)

    return blocks


def _resolve_title(soup: BeautifulSoup, fallback_title: str) -> Tuple[str, str]:
    for meta_name in ("dc.title", "og:title"):
        title = _meta_content(soup, meta_name)
        if title:
            return title, "meta"

    heading = soup.find("h1")
    if heading:
        title = _normalize_block_text(heading.get_text(" ", strip=True))
        if title:
            return title, "heading"

    return fallback_title, "filename"


def _resolve_author(soup: BeautifulSoup) -> Tuple[Optional[str], str]:
    author = _meta_content(soup, "dc.creator")
    if author:
        return author, "meta"

    for heading_name in ("h2", "h3", "p"):
        for tag in soup.find_all(heading_name):
            text = _normalize_block_text(tag.get_text(" ", strip=True))
            if not text:
                continue
            match = re.match(r"^by\s+(.+)$", text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), "heading"

    return None, "missing"


def _meta_content(soup: BeautifulSoup, key: str) -> Optional[str]:
    if key.startswith("og:"):
        tag = soup.find("meta", attrs={"property": key})
    else:
        tag = soup.find("meta", attrs={"name": key})

    if not tag:
        return None

    value = _normalize_whitespace(tag.get("content", ""))
    return value or None


def _build_chapters(
    blocks: Sequence[_Block],
    max_words_per_chapter: int,
) -> Tuple[List[ParsedTextChapter], Dict[str, object]]:
    warnings: List[str] = []
    explicit_markers = sum(1 for block in blocks if block.is_heading and _looks_like_chapter_heading(block.text))

    if explicit_markers:
        chapters = _build_explicit_chapters(blocks, max_words_per_chapter)
    else:
        chapters = _split_blocks_by_word_budget([block.text for block in blocks], max_words_per_chapter)
        warnings.append("No explicit chapter markers found; fallback word-budget splitting used.")

    return chapters, {
        "explicit_chapter_markers": explicit_markers,
        "fallback_split_used": explicit_markers == 0,
        "warnings": warnings,
    }


def _build_explicit_chapters(
    blocks: Sequence[_Block],
    max_words_per_chapter: int,
) -> List[ParsedTextChapter]:
    chapters: List[ParsedTextChapter] = []
    current_title: Optional[str] = None
    current_blocks: List[str] = []
    front_matter: List[str] = []

    for block in blocks:
        if block.is_heading and _looks_like_chapter_heading(block.text):
            if current_title is not None:
                chapters.extend(_finalize_chapter(current_title, current_blocks, len(chapters), max_words_per_chapter))
            elif front_matter:
                front_matter_text = _join_blocks(front_matter)
                if _count_words(front_matter_text) >= FRONT_MATTER_MIN_WORDS:
                    chapters.extend(_finalize_chapter("Opening", front_matter, len(chapters), max_words_per_chapter))
                front_matter = []

            current_title = block.text
            current_blocks = []
            continue

        if current_title is None:
            front_matter.append(block.text)
        else:
            current_blocks.append(block.text)

    if current_title is not None:
        chapters.extend(_finalize_chapter(current_title, current_blocks, len(chapters), max_words_per_chapter))
    elif front_matter:
        chapters.extend(_split_blocks_by_word_budget(front_matter, max_words_per_chapter))

    return chapters or [ParsedTextChapter(number=1, title="Chapter 1", content="")]


def _finalize_chapter(
    title: str,
    blocks: Sequence[str],
    completed_chapter_count: int,
    max_words_per_chapter: int,
) -> List[ParsedTextChapter]:
    parts = _split_blocks_by_word_budget(list(blocks), max_words_per_chapter)
    if not parts:
        return []

    multi_part = len(parts) > 1
    chapters: List[ParsedTextChapter] = []
    for index, part in enumerate(parts, start=1):
        chapter_title = title if not multi_part else f"{title} (Part {index})"
        chapters.append(
            ParsedTextChapter(
                number=completed_chapter_count + len(chapters) + 1,
                title=chapter_title,
                content=part.content,
            )
        )
    return chapters


def _split_blocks_by_word_budget(blocks: Sequence[str], max_words_per_chapter: int) -> List[ParsedTextChapter]:
    chapters: List[ParsedTextChapter] = []
    current_blocks: List[str] = []
    current_words = 0

    for block in blocks:
        block_words = _count_words(block)
        if current_blocks and current_words + block_words > max_words_per_chapter:
            chapters.append(
                ParsedTextChapter(
                    number=len(chapters) + 1,
                    title=f"Chapter {len(chapters) + 1}",
                    content=_join_blocks(current_blocks),
                )
            )
            current_blocks = []
            current_words = 0

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chapters.append(
            ParsedTextChapter(
                number=len(chapters) + 1,
                title=f"Chapter {len(chapters) + 1}",
                content=_join_blocks(current_blocks),
            )
        )

    return chapters


def _render_cleaned_text(title: str, author: Optional[str], blocks: Sequence[_Block]) -> str:
    output_blocks = [title]
    if author:
        output_blocks.append(f"By {author}")
    output_blocks.extend(block.text for block in blocks)
    return _join_blocks(output_blocks) + "\n"


def _join_blocks(blocks: Sequence[str]) -> str:
    return "\n\n".join(block for block in blocks if block).strip()


def _count_words(text: str) -> int:
    return len(text.split())


def _normalize_block_text(text: str) -> str:
    normalized = _normalize_whitespace(text)
    normalized = normalized.strip("-_~ ")
    return normalized


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_zip_member(name: str) -> bool:
    if name.startswith("/") or ".." in name.split("/"):
        return False
    return True


def _extract_cover_from_zip(archive: zipfile.ZipFile, output_dir: Optional[str]) -> Optional[str]:
    if not output_dir:
        return None

    os.makedirs(output_dir, exist_ok=True)

    image_members = [
        member
        for member in archive.infolist()
        if not member.is_dir()
        and _safe_zip_member(member.filename)
        and member.filename.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not image_members:
        return None

    preferred = next(
        (member for member in image_members if "cover" in os.path.basename(member.filename).lower()),
        max(image_members, key=lambda member: member.file_size),
    )

    extension = os.path.splitext(preferred.filename)[1].lower()
    cover_filename = "cover.jpg" if extension in {".jpg", ".jpeg"} else "cover.png"
    cover_path = os.path.join(output_dir, cover_filename)
    with archive.open(preferred.filename) as source_file, open(cover_path, "wb") as cover_file:
        cover_file.write(source_file.read())
    return cover_filename


def _is_gutenberg_boilerplate_tag(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    tag_id = (tag.get("id") or "").casefold()
    classes = {value.casefold() for value in tag.get("class", [])}
    if tag_id in {"pg-header", "pg-footer", "pg-start-separator", "pg-end-separator"}:
        return True
    if any("pg-boilerplate" in value for value in classes):
        return True
    return False


def _is_footnote_block_tag(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    tag_id = (tag.get("id") or "").casefold()
    classes = {value.casefold() for value in tag.get("class", [])}
    if "footnote" in classes:
        return True
    if tag.name in {"p", "div", "section", "aside", "li"} and tag_id.startswith("fn-"):
        return True
    return False


def _is_footnote_reference(
    href: str,
    anchor_id: str,
    classes: set[str],
    text: str,
) -> bool:
    if href.startswith("#fn") or anchor_id.startswith("fnref"):
        return True
    if "pginternal" in classes and re.fullmatch(r"\[?\d+[A-Za-z]?\]?", text):
        return True
    return False


def _looks_like_toc_block(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    if tag.name in {"table", "nav", "ul", "ol"}:
        return True
    anchors = tag.find_all("a")
    if not anchors:
        return False
    hrefs = [(anchor.get("href") or "").strip() for anchor in anchors]
    return all(href.startswith("#") for href in hrefs)


def _is_audio_hostile_block(text: str) -> bool:
    lower_text = text.casefold()
    metadata_prefixes = (
        "title:",
        "author:",
        "release date:",
        "language:",
        "credits:",
        "other information and formats:",
    )
    if lower_text.startswith(metadata_prefixes):
        return True
    if lower_text.startswith("*** start of the project gutenberg ebook"):
        return True
    if lower_text.startswith("*** end of the project gutenberg ebook"):
        return True
    if lower_text.startswith(GUTENBERG_TITLE_PREFIX):
        return True
    if "project gutenberg license" in lower_text:
        return True
    if lower_text.startswith("this ebook is for the use of anyone anywhere"):
        return True
    if "www.gutenberg.org" in lower_text and len(text.split()) < 80:
        return True
    return False


def _looks_like_chapter_heading(text: str) -> bool:
    stripped = text.strip()
    explicit_patterns = (
        r"^(chapter|part|book)\s+([0-9]+|[ivxlcdm]+)\b.*$",
        r"^\d+\.\s+.+$",
    )
    named_sections = {
        "introduction",
        "preface",
        "prologue",
        "epilogue",
        "foreword",
        "afterword",
        "appendix",
        "conclusion",
    }
    if stripped.casefold() in named_sections:
        return True
    if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in explicit_patterns):
        return True
    return bool(re.match(r"^[A-Z][A-Z0-9 ,;:'\-?!]{2,120}$", stripped))