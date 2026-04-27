# Pillars of Truth - Intake Review

## Purpose

This note records the April 7, 2026 intake review of an external draft:

- An external local draft document (not included in this repository)

The goal is to preserve the research direction from that draft without promoting unverified claims into the project's canonical source-of-truth documents.

## Intake Status

Status: `Draft imported for review, not yet canonical`

Reason:

- The draft contains a large amount of useful direction.
- The repo does not yet contain the claimed 600-source bibliography or 100 adversarial fixtures.
- A quick verification pass shows that some anchors are real and strong, while others are mixed, non-academic, or not yet verified source-by-source.

## What Matches the Repo

- The project already has a strong trust/governance spine.
- The FMEA model is already centered on `F1-F17`.
- The production validator promotion step is complete.
- The next engineering steps still include live provider wiring and further hardening.

## What Does Not Yet Match the Repo

### Academic grounding count

The repo does not currently contain a 600-source verified bibliography.

Current state:

- `LLM/Academic Source Map - LLM, Coding, and Governance.md` contains a curated short list.
- No machine-readable 600-item verified bibliography exists in the repo yet.

### Adversarial corpus count

The repo does not currently contain 100 adversarial fixtures.

Current state:

- the golden corpus contains 30 total fixtures
- the adversarial subset currently contains 14 fixtures

That means the "100-item bad source list" is not yet synced into the executable test corpus.

## Verified Anchors From Quick Review

These anchors were confirmed during the intake review and are safe to keep using as real examples:

- Stanford CRFM / HAI Foundation Model Transparency Index
- Stanford CRFM HELM / holistic evaluation framing
- Princeton SWE-bench
- UC Berkeley LiveCodeBench
- MIT Media Lab ID-RAG

## Source-Quality Risks Found

The external draft should not yet be treated as a clean academic-only bibliography because it mixes categories:

- university-hosted research
- university news pages
- non-academic standards bodies
- industry organizations
- vendor or platform sources

Examples of non-academic or mixed-category entries named in the draft include:

- OWASP
- OpenTelemetry Project
- Anthropic
- Redis
- LangWatch
- GitHub/MDPI mixed citations
- MIT News style pages rather than primary research pages

This matters because the earlier project requirement was stricter:

- resources should come only from academic institutions with strong accreditation and track record

## Working Rule Going Forward

Until a full source audit is done, the project should separate research material into two classes:

### Class A - verified academic anchors

- university-hosted papers
- university-hosted lab/project pages
- accredited academic research centers

These can be cited in canonical project docs.

### Class B - draft or mixed provenance references

- standards bodies
- industry reports
- news pages
- unverified titles from working drafts

These may guide exploration, but should not be presented as verified academic ground truth yet.

## Recommended Next Sync Step

Before we expand the canonical docs again, convert the draft into two controlled artifacts:

1. a verified bibliography with one row per source, institution, URL, year, and verification status
2. an adversarial fixture expansion plan that maps proposed new fixtures to `F1-F17` and current corpus gaps

That would let the repo absorb the research direction without overstating what has already been validated.
