"""Split a markdown document into one JSON chunk per paragraph.

Each paragraph inherits the enclosing header hierarchy (h1/h2/h3) as metadata,
along with a paragraph_number that is reset to 1 each time any header changes.
"""
from markdown_it import MarkdownIt

from _splitter_common import run

_MODALITY = "Paragraphs"


def split(markdown_text: str, metadata_base: dict) -> list[dict]:
    tokens = MarkdownIt().parse(markdown_text)
    chunks = []
    headers: dict[int, str] = {}
    para_number = 0

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            level = int(tok.tag[1])
            headers[level] = tokens[i + 1].content
            for deeper in [k for k in headers if k > level]:
                del headers[deeper]
            para_number = 0
            i += 3
        elif tok.type == "paragraph_open":
            para_number += 1
            meta = {**metadata_base, **{f"h{k}": v for k, v in headers.items()},
                    "paragraph_number": para_number}
            chunks.append({"__document__": True, "metadata": meta,
                            "page_content": tokens[i + 1].content})
            i += 3
        else:
            i += 1

    return chunks


if __name__ == "__main__":
    run(split, _MODALITY, "Split markdown by paragraph into LangChain Document JSON.")
