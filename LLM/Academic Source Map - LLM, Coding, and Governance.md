# Academic Source Map - LLM, Coding, and Governance

## Purpose

This note curates academic-only sources for expanding the LLM-Wiki project. All sources below are hosted by accredited academic institutions or university-managed research centers. The list is intentionally biased toward material that supports this project's actual needs:

- LLM foundations
- evaluation rigor
- code generation and software engineering benchmarks
- agent architecture
- retrieval and external knowledge
- security, governance, and high-stakes deployment

## Selection Rules

- Academic institution host only
- Strong institutional reputation and research track record
- Direct relevance to LLM evaluation, coding, agents, retrieval, or governance
- Prefer sources that can inform system design decisions rather than trend commentary

## Highest-Priority Sources

| Theme | Source | Institution | Why it matters here |
| --- | --- | --- | --- |
| Foundation models | [On the Opportunities and Risks of Foundation Models](https://crfm.stanford.edu/report.html) | Stanford CRFM | Best high-level framing for capabilities, risks, security, evaluation, and downstream homogenization. Useful as the top-level conceptual anchor for the trust model. |
| Holistic evaluation | [Improving Transparency in AI Language Models: A Holistic Evaluation](https://hai.stanford.edu/policy/improving-transparency-in-ai-language-models-a-holistic-evaluation) | Stanford HAI | Directly supports the project's emphasis on multi-metric evaluation, transparency, and comparable reporting rather than single-score claims. |
| Real-world coding benchmark | [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://pli.princeton.edu/blog/2023/swe-bench-can-language-models-resolve-real-world-github-issues) | Princeton Language and Intelligence | Strong benchmark reference for repository-scale coding tasks. Helps frame future validator, repair, and agent evaluation against real software workflows instead of toy completion tasks. |
| Agent evaluation rigor | [AI Agents That Matter](https://agents.cs.princeton.edu/) | Princeton University | Important corrective to benchmark hype. Especially relevant for any future claims about agentic promotion, multi-step repair, or autonomous code changes. |
| Execution-aware code generation | [Enhancing Language Models for Program Synthesis using Execution](https://www.csail.mit.edu/event/enhancing-language-models-program-synthesis-using-execution) | MIT CSAIL | Useful for any future design that uses execution feedback, reranking, or verifier loops for code-related tasks. |
| Code benchmark design | [SAFIM: Evaluation of LLMs on Syntax-Aware Code Fill-in-the-Middle Tasks](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2025/EECS-2025-50.pdf) | UC Berkeley EECS | Valuable because it emphasizes execution-based evaluation, contamination control, and realistic code-edit behavior beyond standalone function generation. |
| Agent systems architecture | [System Architecture for Agentic Large Language Models](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2025/EECS-2025-5.html) | UC Berkeley EECS | Relevant if the project later grows from single-shot evaluation into tool-using or rollback-capable agents. Strong fit for control-plane and safety thinking. |
| Prompt-injection defense | [Finetuning as a Defense Against LLM Secret-leaking](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2024/EECS-2024-135.html) | UC Berkeley EECS | Useful for the security side of prompt handling, instruction secrecy, and defense-in-depth against leakage and injection-style failures. |
| Software engineering adoption | [Assessing Opportunities for LLMs in Software Engineering and Acquisition](https://www.sei.cmu.edu/library/assessing-opportunities-for-llms-in-software-engineering-and-acquisition/) | Carnegie Mellon University Software Engineering Institute | Strong decision framework for matching LLM capability to software engineering use cases with explicit concerns and mitigation tactics. |
| High-stakes deployment | [Assessing LLMs for High Stakes Applications](https://www.sei.cmu.edu/library/assessing-llms-high-stakes-applications/) | Carnegie Mellon University Software Engineering Institute | Reinforces the need for trust, security, reliability, reproducibility, and assessment before deployment in consequential workflows. |

## Secondary Sources

| Theme | Source | Institution | Why it matters here |
| --- | --- | --- | --- |
| Retrieval foundations | [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/) | Stanford University | Not LLM-specific, but still the cleanest academic foundation for retrieval logic, ranking, indexing, and evidence access if the project evolves toward RAG. |
| Retrieval + agents + code | [External Knowledge Augmented Language Models for Code Generation and Agents](https://kilthub.cmu.edu/articles/thesis/External_Knowledge_Augmented_Language_Models_for_Code_Generation_and_Agents/28541399) | Carnegie Mellon University | Strong bridge source connecting code generation, external knowledge, retrieval augmentation, and agentic use. |
| Evaluation in high-stakes contexts | [Evaluating LLMs for Text Summarization: An Introduction](https://www.sei.cmu.edu/blog/evaluating-llms-for-text-summarization-introduction/) | Carnegie Mellon University Software Engineering Institute | Helpful for translating abstract evaluation ideas into deployment-grade assessment practices. |
| Code translation workflow | [Scaling Code Translation](https://www.sei.cmu.edu/library/scaling-code-translation/) | Carnegie Mellon University Software Engineering Institute | Relevant if the project later includes controlled code migration, structured prompt decomposition, or human-in-the-loop transformation workflows. |

## How These Sources Map to This Project

### Trust model and policy rigor

- Stanford CRFM foundation-model report
- Stanford HAI HELM brief
- CMU SEI high-stakes assessment

These should inform future edits to:

- `Foundations/LLM System Trust Model.md`
- `Foundations/Trust Boundaries in LLM Pipelines.md`
- `Governance/Human-in-the-Loop Governance.md`

### Coding and software engineering evaluation

- Princeton SWE-bench
- Princeton AI Agents That Matter
- MIT execution-based program synthesis
- Berkeley SAFIM
- CMU SEI software-engineering fitness paper

These should inform future edits to:

- `pipeline/validator_runner.py` design
- `pipeline/tests/` benchmark strategy
- `strategy/GOLDEN_CORPUS_COVERAGE_MAP.md`
- `Program-Management/Program Management for Technical Infrastructure.md`

### Agent architecture and safety

- Berkeley System Architecture for Agentic Large Language Models
- Berkeley secret-leaking defense
- Princeton agent evaluation work

These are the best academic sources for any later move from a validator into a broader agentic control plane.

### Retrieval and evidence access

- Stanford IR book
- CMU external-knowledge dissertation

These are the best current academic anchors if the project later adds:

- retrieval over policy and governance docs
- evidence-grounded evaluation prompts
- corpus search and provenance-aware context assembly

## Recommended Reading Order

1. Stanford CRFM foundation-model report
2. Stanford HAI HELM brief
3. Princeton SWE-bench
4. CMU SEI software-engineering fitness paper
5. Berkeley SAFIM
6. Princeton AI Agents That Matter
7. Berkeley agentic systems architecture
8. Berkeley secret-leaking defense
9. Stanford IR book
10. CMU external-knowledge dissertation

## Immediate Use In This Repository

If we keep moving the project forward from the current handoff point, the most immediately useful sources are:

1. Stanford HAI HELM brief
2. Princeton SWE-bench
3. Berkeley SAFIM
4. CMU SEI software-engineering fitness paper
5. Princeton AI Agents That Matter

Those five best match the next likely work:

- production `validator_runner.py`
- stronger benchmark design
- corpus expansion
- evaluation-metric discipline
- more defensible portfolio claims

## Continuation Note

Reviewed on April 7, 2026.

The project's actual continuation point remains the same as the April 6, 2026 ledger entry: the bootstrap runtime is present, the tests and smoke checks have passed, and the next engineering step is still promoting the bootstrap validator into `pipeline/validator_runner.py`.
