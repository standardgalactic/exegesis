# Exegesis

**Local-first discovery, retrieval, extraction, and model-assisted analysis of a distributed scholarly corpus.**

Exegesis is an experimental research tool for turning a distributed bibliography of scholarly documents into a locally accessible, searchable, and eventually cross-referenced body of work.

It begins with a Markdown bibliography, identifies linked PDF documents, downloads them, extracts their text, and uses locally hosted language models to produce structured analyses.

The system is designed around a fundamental distinction: **source documents constitute the evidence; generated summaries constitute interpretations of that evidence.**

Exegesis preserves source provenance and does not treat model-generated summaries as authoritative transcriptions.

**Status:** v0.1, proof of concept. The discovery, retrieval, extraction, and Ollama summarization pipeline has been exercised successfully on a small sample.

## 1. Motivation

A substantial research corpus is often distributed across repositories, GitHub Pages sites, personal websites, preprints, and archived documents.

Even when a central bibliography exists, reading and comparing hundreds of documents remains difficult. Documents may overlap, revise earlier arguments, introduce incompatible terminology, or depend on definitions developed elsewhere.

Exegesis is intended to reduce the mechanical costs of working with such a corpus without transferring interpretive authority to a language model.

Its initial objectives are to:

- Discover and inventory documents from an existing bibliography.
- Preserve the original source location and bibliographic context.
- Download and extract document text reproducibly.
- Generate preliminary summaries using locally available models.
- Retain intermediate analyses for inspection and comparison.
- Support future searches, thematic comparisons, and cross-document synthesis.

The long-term objective is not merely automatic summarization. It is a research environment in which documents can be compared, disagreements identified, conceptual dependencies reconstructed, and generated interpretations checked against their sources.

## 2. Architecture

The current pipeline consists of five operations:

```text
Markdown bibliography
        |
        v
     discover
        |
        v
  Source manifest
        |
        v
       fetch
        |
        v
   Local PDF files
        |
        v
      extract
        |
        v
 Page-numbered text
        |
        v
     summarize
        |
        v
  Chunk analyses
  Final summaries
  Model metadata
```

The `report` command provides an overview of the indexed corpus.

The pipeline is deliberately modular. Downloaded source documents, extracted text, and model outputs are distinct artifacts, allowing individual stages to be repeated or improved without necessarily repeating the entire workflow.

## 3. Requirements and installation

Exegesis is developed for a local Python environment and uses Ollama for language-model inference.

The current workflow has been exercised under Linux/WSL with Python 3.12.

Requirements include Python 3, `pip`, a local Ollama installation, sufficient storage for downloaded PDFs, and enough memory for the selected model.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[pdf]'
```

The editable installation makes the `exegesis` command available inside the virtual environment and allows local source-code changes to take effect without reinstalling the package in ordinary cases.

Confirm the installation:

```bash
exegesis --help
```

Confirm that Ollama is installed and has available models:

```bash
ollama list
```

The initial experiments use:

```text
granite4.1:3b
granite4.1:8b
```

If necessary, obtain the models using:

```bash
ollama pull granite4.1:3b
ollama pull granite4.1:8b
```

Ollama must be running and accessible through its local API when summarization is requested.

## 4. Quick start

The following commands assume that the `standardgalactic` repository is a sibling directory of `exegesis`.

```bash
cd ~/exegesis
source .venv/bin/activate

# Discover active PDF references.
exegesis discover ../standardgalactic/README.md

# Inspect the indexed corpus.
exegesis report

# Preview downloads without retrieving files.
exegesis fetch --dry-run

# Download a small sample.
exegesis fetch --limit 3

# Extract text from the downloaded documents.
exegesis extract --limit 3

# Inspect available local models.
ollama list

# Generate a preliminary summary.
exegesis summarize --model granite4.1:3b --limit 1
```

The `--limit` option is useful for controlled experiments before processing the full corpus.

The first successful sample included three papers from the active-inference collection:

- *Amortized Deliberation*
- *Closure Under Projection*
- *Interpretation and Its Overcoming*

Their extraction produced 12, 11, and 80 pages respectively, for a combined 103 pages and approximately 168,779 extracted characters.

A subsequent run successfully generated and stored a Granite 3B summary of *Amortized Deliberation*.

These results demonstrate operational completion of the initial pipeline. They do not, by themselves, establish the factual accuracy or analytical quality of the generated summaries.

## 5. Discovery and bibliography handling

The `discover` command reads a Markdown document and identifies direct PDF links.

```bash
exegesis discover ../standardgalactic/README.md
```

By default, discovery includes only active Markdown PDF references.

The manifest preserves source-occurrence information, including the reference title, original URL, README line number, surrounding heading, and whether the reference appeared inside an HTML comment.

A single PDF URL may appear multiple times in the bibliography. Such occurrences retain their bibliographic context while the URL is deduplicated for downloading.

Distinct URLs may also point to different editions, revisions, or copies of the same underlying work. Work-level deduplication is not yet implemented.

### Archived and commented-out references

To include PDFs inside HTML comments:

```bash
exegesis discover ../standardgalactic/README.md --include-comments
```

**Important:** Discovery replaces the existing manifest.

Using `--include-comments` therefore changes which documents are eligible for subsequent operations.

Commented-out references may represent abandoned drafts, withdrawn documents, obsolete versions, private material, or works intentionally excluded from public navigation.

Their presence in a source README does not constitute permission to publish or redistribute them.

The default active-only behavior should be retained for ordinary processing.

### Current discovery limitations

Version 0.1 discovers direct Markdown PDF links.

It does not yet recursively visit linked HTML pages, traverse repository directories, or automatically discover documents through external search engines.

HTML traversal is a proposed future feature and must remain explicitly bounded and opt-in.

## 6. PDF retrieval

Preview eligible downloads:

```bash
exegesis fetch --dry-run
```

Download a limited sample:

```bash
exegesis fetch --limit 3
```

The fetch stage downloads PDF content, validates its PDF header and EOF marker, calculates a SHA-256 hash, and records retrieval outcomes in:

```text
data/fetch-status.jsonl
```

Successful existing downloads are skipped.

The checksum is important because a URL alone does not identify immutable content. A PDF hosted at a stable URL may change over time.

Content hashes provide a basis for detecting revisions, checking reproducibility, and distinguishing source versions in later analyses.

The current validation is a basic file-integrity check, not a guarantee that a PDF is semantically valid or safe.

## 7. Text extraction

Run extraction after downloading documents:

```bash
exegesis extract --limit 3
```

Exegesis uses PyMuPDF to extract page-numbered text and writes a JSON document for each processed PDF.

The extraction stage preserves page boundaries because page references are essential for later verification.

The recommended import for current PyMuPDF releases is:

```python
import pymupdf as fitz
```

This retains compatibility with existing calls such as `fitz.open()` while avoiding the deprecated `fitz` import.

### Extraction limitations

PDF text extraction is not equivalent to reconstructing the original document.

Common problems include mathematical notation appearing out of order, footnotes being interleaved with body text, incorrect reading order in multicolumn layouts, lost figure relationships, and omitted graphical content.

Scanned or image-only PDFs may yield little or no text.

OCR is deliberately not automatic in v0.1.

A future extraction-quality check should distinguish successfully processed files from files whose extracted text is too incomplete to support reliable analysis.

## 8. Local model-assisted summarization

Exegesis uses Ollama to run language models locally.

The initial experiments use IBM's Granite 4.1 models:

```bash
exegesis summarize --model granite4.1:3b --limit 1
```

For comparison:

```bash
exegesis summarize --model granite4.1:8b --limit 1
```

The summarization stage divides extracted material into manageable chunks, generates intermediate analyses, and produces a final document-level synthesis.

Results are stored separately by model, making it possible to compare different model configurations without intentionally mixing their outputs.

An observed output path is:

```text
data/summaries/granite4.1-3b/
```

A generated summary JSON file includes:

| Field | Purpose |
|---|---|
| `url` | Original source URL |
| `model` | Model used for generation |
| `source_sha256` | Source-content hash |
| `chunk_count` | Number of analyzed chunks |
| `notes` | Intermediate model analyses |
| `summary` | Final document synthesis |
| `warning` | Processing warnings, if any |

### Inspecting results

List generated summaries:

```bash
find data/summaries -type f
```

Read the final Granite 3B summary:

```bash
jq -r '.summary' data/summaries/granite4.1-3b/*.json
```

Inspect processing metadata:

```bash
jq '{
  model,
  chunk_count,
  warning,
  source_sha256
}' data/summaries/granite4.1-3b/*.json
```

Inspect intermediate notes:

```bash
jq '.notes' data/summaries/granite4.1-3b/*.json
```

Intermediate notes should be preserved because they make it easier to investigate whether important qualifications were lost during final synthesis.

They should not be confused with the model's private reasoning or with a verified reconstruction of the source.

## 9. Performance and model selection

The first Granite 3B summarization of *Amortized Deliberation* completed in approximately 72 seconds in the local test environment.

This is a single observation, not a statistically meaningful performance benchmark.

Runtime depends on document length, chunk count, model size, context configuration, available RAM and VRAM, and Ollama's execution behavior.

For illustration, at a hypothetical constant 72 seconds per document:

| Documents | Estimated processing time |
|---|---|
| 10 | 12 minutes |
| 100 | 2 hours |
| 500 | 10 hours |

Actual corpus-wide processing time may differ substantially because document lengths and model workloads are heterogeneous.

### Proof-of-concept strategy

Granite 3B is the preferred starting model for broad corpus coverage.

The smaller model offers a practical way to test the full workflow before committing substantial computational resources to larger-model analysis.

Granite 8B can be used for selective comparisons and more demanding documents.

A proposed two-tier workflow is:

```text
Entire corpus
     |
     v
Granite 3B analysis
     |
     v
Quality inspection
     |
     +---- Adequate results --> Retain
     |
     +---- Uncertain results --> Reanalyze with 8B
```

This selective escalation strategy is proposed, not automated in v0.1.

### Measuring execution time

Use the shell's `time` command:

```bash
time exegesis summarize --model granite4.1:3b --limit 1
```

Or:

```bash
time exegesis summarize --model granite4.1:8b --limit 1
```

For unbuffered terminal output:

```bash
PYTHONUNBUFFERED=1 exegesis summarize \
  --model granite4.1:3b --limit 1
```

This displays progress messages as the application emits them. It does not enable token-by-token streaming from Ollama.

Streaming output would require an additional implementation change.

A cached result may also be skipped rather than regenerated, so performance comparisons must verify that equivalent work was actually performed.

## 10. Evaluating summary quality

A successfully generated summary is not necessarily a faithful summary.

Model evaluation should examine whether the output:

1. Identifies the document's central thesis.
2. Preserves important definitions and distinctions.
3. Represents mathematical claims accurately.
4. Distinguishes hypotheses, proofs, examples, and speculation.
5. Retains limitations and unresolved questions.
6. Avoids introducing unsupported claims.
7. Preserves relevant relationships between sections.
8. Provides traceable evidence for claims that require verification.

For mathematical and philosophical documents, fluency alone is an inadequate quality measure.

A summary may be grammatically coherent while misrepresenting the logical structure of an argument.

The initial Granite comparison should therefore consider both computational cost and analytical fidelity.

No formal summary-quality benchmark has yet been completed.

## 11. Provenance and verification

Source provenance is a primary design constraint.

Every retrieved document should remain traceable to its original URL, bibliographic occurrence, and source-content hash.

The following distinctions must be maintained:

**Original document:** The authoritative source for what the author wrote.

**Extracted text:** A machine-readable representation that may contain extraction errors.

**Intermediate model notes:** Generated interpretations of portions of the extracted text.

**Final model summary:** A generated synthesis that may omit, simplify, or misstate claims.

**Verified analysis:** An interpretation checked against the original source, including relevant pages and mathematical expressions.

A model-generated citation is not automatically a verified citation.

Claims, quotations, equations, and page references intended for publication must be checked against the original PDF.

## 12. Data storage and reproducibility

Generated artifacts are stored locally under `data/`.

The current workflow produces downloaded PDFs, extraction outputs, retrieval records, and model-specific summaries.

Generated data is excluded from Git by default to avoid committing large corpora and derived artifacts unintentionally.

For reproducible experiments, future records should include model digest, inference parameters, prompt-template version, extraction version, source hash, execution time, and processing status.

The current summary JSON records the model name, source hash, chunk count, notes, and final summary, but does not constitute a complete experimental provenance record.

Reproducibility should not be assumed solely because two runs use the same model name.

## 13. Testing

Install the test dependency:

```bash
pip install pytest
```

Run the test suite:

```bash
pytest -q
```

The test suite should eventually cover bibliography parsing, comment handling, URL deduplication, fetch integrity, extraction behavior, failure recovery, and summary schema validation.

Passing tests establishes compliance with the tested implementation behavior, not the correctness of model-generated interpretations.

## 14. Development roadmap

### Phase I: Corpus acquisition and extraction

Implemented in the initial prototype:

- Direct Markdown PDF discovery.
- Active-only discovery by default.
- Optional commented-reference discovery.
- URL-level download deduplication.
- PDF retrieval and basic validation.
- SHA-256 content hashing.
- Page-aware text extraction.
- Local Ollama summarization.
- Model-separated summary artifacts.

### Phase II: Reliability and observability

Proposed improvements include token-streaming output, per-document timing, explicit progress reporting, resumable batch execution, structured failure classification, extraction-quality diagnostics, and richer model provenance.

The objective is to make large batch operations inspectable and recoverable.

### Phase III: Comparative model evaluation

Establish a small manually reviewed benchmark corpus.

Compare Granite 3B and 8B on factual fidelity, preservation of formal claims, completeness, hallucination rate, and computational cost.

Evaluate whether selective escalation to a larger model provides sufficient improvement to justify the additional processing time.

### Phase IV: Corpus organization

Introduce work-level deduplication, edition and revision relationships, thematic classification, document metadata, and local full-text search.

These features should preserve distinctions between documents rather than collapsing related works into a single generated description.

### Phase V: Cross-document analysis

Develop explicit representations of conceptual dependencies, recurring definitions, mathematical assumptions, competing hypotheses, and unresolved disagreements.

Potential applications include identifying where a later paper revises an earlier claim, finding incompatible definitions across documents, tracing the development of a mathematical framework, and locating source passages relevant to a research question.

Such relationships should be treated as hypotheses until verified.

### Phase VI: Controlled source expansion

Explore opt-in traversal of linked HTML pages and repository indexes, with explicit limits on traversal depth, domains, document types, and retrieval volume.

Recursive crawling should never be enabled implicitly by ordinary bibliography discovery.

## 15. Research philosophy

Exegesis is not intended to replace reading.

Its purpose is to make a large scholarly corpus more navigable while preserving the possibility of correction.

The distinction between evidence and interpretation is central to the project.

A source document can be revisited. An extraction can be corrected. A model summary can be regenerated. A comparison can be challenged. A claim can be traced to its origin.

The usefulness of the system depends less on producing persuasive summaries than on maintaining these opportunities for revision.

**The goal is not to eliminate interpretation, but to make interpretation inspectable, revisable, and accountable to its sources.**

## License

See the repository's license file for the applicable terms. The license governing Exegesis software does not automatically govern the documents retrieved or analyzed by the system.