from src.core.docling_adapter import ImportedChapter, ImportedChunk
from src.core.speech_renderer import render_chapter_text


def test_render_chapter_text_normalizes_markdown_and_preserves_paragraphs():
    chapter = ImportedChapter(
        number=1,
        title="**Chapter 1**",
        chunks=[
            ImportedChunk(
                text="## Intro\n\nThis is **bold** and [linked](https://example.com).",
                headings=["Book Title", "Chapter 1", "Section A"],
            ),
            ImportedChunk(
                text="1. First item\n2. Second item",
                headings=["Book Title", "Chapter 1", "Section A"],
            ),
        ],
    )

    rendered = render_chapter_text(chapter)

    assert "**" not in rendered
    assert "[linked](https://example.com)" not in rendered
    assert "linked" in rendered
    assert "Section A" in rendered
    assert "First item" in rendered
    assert "Second item" in rendered
    assert "\n\n" in rendered