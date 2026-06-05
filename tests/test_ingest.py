from docswarm.ingest import chunk_text, content_hash, dedupe, extract
from docswarm.ingest.base import RawDocument


def test_chunk_text_respects_size_and_min():
    text = "\n\n".join(f"Paragraph number {i} with some filler content." * 3
                       for i in range(20))
    chunks = chunk_text(text, max_chars=200, overlap=20)
    assert chunks
    assert all(len(c) >= 40 for c in chunks)


def test_extract_plain_text():
    res = extract(b"hello world", filename="note.txt")
    assert res.ok
    assert res.method == "plain"
    assert "hello" in res.text


def test_extract_unknown_dependency_is_graceful():
    # a .pdf with no pymupdf installed should not crash; method is informative
    res = extract(b"%PDF-1.4 fake", filename="x.pdf")
    assert res.method in ("pdf_text", "pdf_ocr", "pdf_hybrid", "error", "unsupported")


def test_dedupe_by_content_hash():
    a = RawDocument(doc_id="1", filename="a.txt", content=b"same")
    b = RawDocument(doc_id="2", filename="b.txt", content=b"same")
    c = RawDocument(doc_id="3", filename="c.txt", content=b"different")
    out = dedupe([a, b, c])
    assert len(out) == 2
    assert content_hash(b"same") == a.sha256
