# 0002. Page-aware, sentence-based chunking measured in words

- Status: accepted
- Date: 2026-11-18

## Context

Retrieval returns passages ("chunks") of the annual reports, and every answer must cite the
page a statement comes from. The reports are long PDFs in Romanian with prose, tables and
charts. Text extracted from PDFs has artefacts: words hyphenated across lines, cedilla
variants of ș and ț, invisible characters.

Chunk size is a trade-off. Large chunks mix several topics and dilute the meaning of their
embedding; small chunks lose the context needed to understand them.

## Decision

- Extract text page by page with pypdf and keep the PDF page number (1-based, as shown by
  PDF viewers).
- Normalise text: Unicode NFC, cedilla to comma-below letters, remove invisible characters,
  rejoin words hyphenated across lines, collapse whitespace.
- Split each page into sentences and pack whole sentences into chunks of at most 200 words,
  repeating up to 40 words of trailing sentences at the start of the next chunk.
- Chunks never cross a page boundary.
- Measure size in words rather than model tokens. Both limits are configuration values.

## Alternatives considered

- **Fixed-size windows of characters or tokens.** Simplest, but cuts sentences in half.
- **Chunks spanning pages.** Keeps paragraphs that continue on the next page together, but a
  chunk would no longer have a single page to cite.
- **Token-based sizes.** More precise, but ties chunking to one model's tokenizer before the
  embedding model is chosen (PR 3).
- **PyMuPDF or pdfplumber for extraction.** Often better on tables; PyMuPDF is AGPL licensed,
  pdfplumber is slower. pypdf is permissively licensed, pure Python and good enough for
  prose. To be revisited if evaluation shows extraction is the bottleneck.

## Consequences

- Every chunk has exactly one page, so citations are precise.
- A paragraph that continues on the next page is split in two.
- Sentence detection is a heuristic: abbreviations such as "S.A." can end a sentence early.
- Tables lose their structure and long table rows are cut by word count. Questions about
  figures in tables are the most likely to fail; this is a known limitation.
- Sizes (200 / 40 words) are a starting point, to be tuned with the evaluation set (PR 5).
