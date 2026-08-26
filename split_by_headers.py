"""Split a markdown document into one JSON chunk per header section.

Each chunk's page_content is the concatenated text of all paragraphs inside
one header section. Header hierarchy (h1/h2/h3) is tracked in metadata and
reset when a heading of equal or higher level is encountered.
Headers inside fenced code blocks are ignored (they appear as 'fence' tokens,
not 'heading_open' tokens in the markdown-it token stream).
"""
from markdown_it import MarkdownIt

from _splitter_common import run

_MODALITY = "Headers"


def split(markdown_text: str, metadata_base: dict) -> list[dict]:
    tokens = MarkdownIt().parse(markdown_text)
    chunks = []
    headers: dict[int, str] = {}
    paragraphs: list[str] = []

    def flush() -> None:
        if not paragraphs:
            return
        meta = {**metadata_base, **{f"h{k}": v for k, v in headers.items()}}
        chunks.append({"__document__": True, "metadata": meta,
                        "page_content": "\n\n".join(paragraphs)})
        paragraphs.clear()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            flush()
            level = int(tok.tag[1])
            headers[level] = tokens[i + 1].content
            for deeper in [k for k in headers if k > level]:
                del headers[deeper]
            i += 3
        elif tok.type == "paragraph_open":
            paragraphs.append(tokens[i + 1].content)
            i += 3
        else:
            i += 1

    flush()
    return chunks


if __name__ == "__main__":
    run(split, _MODALITY, "Split markdown by header sections into LangChain Document JSON.")
