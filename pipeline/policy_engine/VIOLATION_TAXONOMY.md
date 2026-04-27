# Policy Violation Taxonomy

**Version:** 1.0
**Source:** Strategy Kit Rev 3.4, Parts 1, 4, 5 (quality criteria, security posture, stakeholder feedback)

This taxonomy defines the `rule_id` values that appear in the `policy_violations` array of `validation_result.schema.json`. Every violation ID follows the pattern `{CATEGORY}-{NNN}`.


## ACCURACY — Factual Correctness

| rule_id | Description | Severity | Example |
|---------|-------------|----------|---------|
| ACCURACY-001 | Inverted or swapped factual claims | critical | TCP described as connectionless; UDP described as connection-oriented |
| ACCURACY-002 | Outdated information (EOL tools, deprecated APIs, stale versions) | major | Recommending Python 2.7, easy_install, or archived editors |
| ACCURACY-003 | Misleading oversimplification that contradicts established consensus | major | "Cache invalidation is straightforward" without caveats |
| ACCURACY-004 | Unverifiable quantitative claims without source attribution | minor | "Reduces database load by 80-90%" with no context or citation |
| ACCURACY-005 | Internally inconsistent claims within the same article | critical | Article states two contradictory things about the same concept |


## COMPLETENESS — Content Sufficiency

| rule_id | Description | Severity | Example |
|---------|-------------|----------|---------|
| COMPLETENESS-001 | Explicit TODO/placeholder text in article body | major | "TODO: Add installation instructions" |
| COMPLETENESS-002 | Empty section (heading with no content below it) | major | Section heading followed immediately by next heading or EOF |
| COMPLETENESS-003 | Stub content ("This section will be filled in later") | major | Placeholder prose indicating incomplete drafting |
| COMPLETENESS-004 | Missing critical section for the article type | minor | A setup guide with no installation steps; an API doc with no examples |


## SECURITY — Sensitive Content

| rule_id | Description | Severity | Example |
|---------|-------------|----------|---------|
| SECURITY-001 | Hardcoded credentials (passwords, API keys, tokens) | critical | Plaintext password or AWS access key in article content |
| SECURITY-002 | Internal infrastructure details (hostnames, IPs, ports of production systems) | major | Production database hostname and port in a wiki article |
| SECURITY-003 | PII or protected data in article content | critical | Employee SSNs, customer emails, or health information |


## FORMATTING — Structural Standards

| rule_id | Description | Severity | Example |
|---------|-------------|----------|---------|
| FORMATTING-001 | Missing top-level heading (H1) | minor | Article body starts without a `# Title` heading |
| FORMATTING-002 | Broken markdown (unclosed code blocks, malformed tables) | minor | Triple-backtick code block without closing backticks |


## NEUTRALITY — Objectivity Standards

| rule_id | Description | Severity | Example |
|---------|-------------|----------|---------|
| NEUTRALITY-001 | Product/vendor recommendation without alternatives or trade-off analysis | info | "Use Prometheus and Grafana" stated as the only option |


## PARSER — Frontmatter Enforcement Rules

These are enforced by parse_identity.py before the article reaches the LLM. They produce exit code 4 (SYSTEM_FAULT) or exit code 0 (success with sanitization).

| Enforcement | Behavior | Exit Code |
|-------------|----------|-----------|
| source_id missing | Hard error, structured error JSON | 4 |
| source_id fails `^[a-zA-Z0-9-]{1,36}$` | Hard error, structured error JSON | 4 |
| Non-identity frontmatter value > 256 bytes | **Truncated silently** to 256 bytes, parse succeeds | 0 |
| Invalid YAML | Hard error, structured error JSON | 4 |
| No frontmatter delimiter | Hard error, structured error JSON | 4 |
| Empty file | Hard error, structured error JSON | 4 |

**Design rationale:** source_id is the identity field — if it's invalid, the pipeline cannot construct a transaction key, so rejection is mandatory. Non-identity fields (title, category, etc.) are informational. Truncating them preserves pipeline liveness while preventing unbounded memory consumption. This is consistent with parse_identity.py's `sanitize_frontmatter_values()` implementation.


## Severity Levels

| Level | Meaning | Pipeline Behavior |
|-------|---------|------------------|
| critical | Clear policy violation, article must not be promoted | REJECT — any critical violation forces rejection |
| major | Significant quality issue that requires remediation | REJECT — unless counterbalanced by otherwise strong content (edge case for ESCALATE) |
| minor | Improvement opportunity, does not block promotion alone | APPROVE with recommendations, or ESCALATE if combined with other minor issues |
| info | Observation, no action required | APPROVE — noted in recommendations array |
