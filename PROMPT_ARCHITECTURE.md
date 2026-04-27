# LLM-Wiki Content Pipeline — Prompt Architecture
**Human-facing reference: how the prompt system works and why**
*Owner: Josh Hillard | Created: April 6, 2026 | Bound to: Strategy Kit Rev 3.4*

---

## What This Document Is

Design document for the LLM-Wiki prompt system. Explains architecture, rationale, and maintenance protocol. NOT pasted into AI sessions — the runtime prompts live in RUNTIME_PROMPTS.md.

---

## Architecture: Core Contract + Task Card + Mode Pack

```
CORE CONTRACT (~350 tokens)
  Pipeline components, stack, exit code contract, key paths, hard rules.
  Changes: when a component is added, a rule is adopted, or a path moves.

TASK CARD (per task, ~150-250 tokens)
  Goal, scope, out-of-scope, inspect-first symbols, acceptance, verify.
  Uses path::symbol references (durable across refactors).

MODE PACK (optional, ~80-120 tokens)
  Domain-specific rules. Available: identity, evaluation, promotion, config, product.
```

**Optional: SNAPSHOT block** (~50-100 tokens)
Attach only when the task depends on current branch, tag, or failing tests.

**Token budget:**
- Typical task: Core (~350) + Task Card (~200) = ~550 tokens
- With mode: + ~100 = ~650 tokens
- With snapshot: + ~80 = ~730 tokens

---

## Mode Pack Mapping to Pipeline Components

| Mode | Primary Component | Strategy Kit Reference |
|------|-------------------|----------------------|
| identity | parse_identity.py | P0-1, P0-10, Part 4 § S3 |
| evaluation | validator_runner.py | P0-4, P0-12, P0-13, Part 7 § NOW |
| promotion | Promote-ToVerified.ps1 | P0-5, P0-7, P0-8, P0-11 |
| config | ops/validator_config.json | P0-9, Part 7 § validator_config.json |
| product | Success metrics, stakeholder updates | Part 1 § Success Metrics |

---

## Design Decisions

### path::symbol over line numbers
Line numbers shift with every commit. `pipeline/parse_identity.py::extract_frontmatter` survives refactors and is greppable.

### Mode Packs over Persona Bindings
Personas (PERSONA_LIBRARY.md) are human-facing thinking frameworks. At runtime, models need domain rules, not narrative. Mode Packs deliver rules in 80–120 tokens. Each Mode Pack maps to one pipeline component.

### Exit code contract in Core, not Mode
The 0–5 exit code contract is in the Core Contract because every task touches it — identity extraction, evaluation, promotion, and testing all depend on the same contract.

### Hybrid deployment as Core rule, not Mode-only
The context digest rule in Core Contract covers the hybrid model because switching model paths invalidates cached evaluations. This is a cross-cutting concern, not evaluation-specific.

---

## Maintenance Protocol

### After every sprint:
1. Update SNAPSHOT template values in RUNTIME_PROMPTS.md
2. Append to PROJECT_LEDGER.md (timeline, retro, any new ADRs)
3. If a new hard rule was adopted, add to Core Contract
4. If a Mode Pack needs a new rule, add it

### After stack changes:
1. Update Core Contract's stack line and key paths
2. Update relevant Mode Packs

### After model config changes:
1. Update ops/validator_config.json
2. Verify context digest rotates (all cached evaluations invalidated)
3. If a new field is added, update MODE: config and P0-9 in strategy kit

---

## Document Map

| Document | Type | Purpose |
|----------|------|---------|
| PROMPT_ARCHITECTURE.md | Human reference | This doc — explains the system |
| RUNTIME_PROMPTS.md | Copy-paste runtime | Core, Task Card, Mode Packs, Snapshot |
| PERSONA_LIBRARY.md | Human reference | 6 project-bound personas with component ownership |
| PROJECT_LEDGER.md | Living record | Timeline, decisions, retrospectives |
| strategy/LLM-Wiki_Strategy_Kit.md | Authoritative plan | PRD, ADR, Roadmap, Code Review, FMEA, LLM Infrastructure |

---

*Bound to: LLM-Wiki Strategy Kit Rev 3.4*
*Last updated: April 6, 2026*
