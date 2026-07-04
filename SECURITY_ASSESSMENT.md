# Security Assessment – Weekly AI Digest Automation

**Document owner:** Alexandra | Service Desk Team Lead
**System:** Weekly AI Digest Generator (GitHub Actions + Python)
**Date:** 2026-07-03
**Classification:** Internal use – low-risk automation
**Review cycle:** Annually, or on material change to sources/dependencies

## 1. Purpose and Scope

This automation retrieves publicly published RSS content from a curated list
of official AI research labs, academic press, and regulatory bodies, and
compiles it into a weekly PDF digest for internal circulation to the AI
Champions initiative. This assessment covers the GitHub Actions workflow,
its dependencies, and the data it processes.

## 2. Architecture Summary

```
GitHub-hosted runner (ephemeral, isolated container)
        |
        v
Outbound HTTPS GET  --->  Public RSS endpoints (labs, press, regulators)
        |
        v
Local processing (feedparser, reportlab) — no external calls, no code
execution from retrieved content
        |
        v
PDF written to workspace  --->  Published as a GitHub Release (same repo)
```

No inbound connections. No persistent infrastructure. No connection to
company network, endpoints, or internal systems. Runner is destroyed after
each execution.

## 3. Data Classification

| Data type | Present? | Notes |
|---|---|---|
| Personal data / PII | No | Only public RSS content (titles, dates, descriptions, links) |
| Company confidential data | No | No internal systems or data sources are queried |
| Credentials / secrets | No | No API key, no login, no stored credential of any kind |
| Authentication tokens | Yes (minimal) | `GITHUB_TOKEN`, auto-issued per run, scoped to `contents: write`, expires at job end |

No GDPR-relevant processing occurs; no data subject information is handled.

## 4. Risk Register

| # | Risk | CC Domain | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|---|
| 1 | Unpinned dependency versions pulled from PyPI at runtime (supply chain / typosquatting exposure) | Security Operations | Low | Medium | Dependencies pinned to exact versions in `requirements.txt` | Closed |
| 2 | Third-party GitHub Action (`softprops/action-gh-release`) referenced by mutable tag rather than immutable commit SHA | Security Operations / Access Control | Low | Medium | Documented pinning procedure in README; to be applied on first deployment | Open — action required on setup |
| 3 | Malicious or compromised RSS source delivering manipulated content (e.g. DNS hijack, domain takeover) | Security Principles (Integrity) | Very low | Low | Source list restricted to established, reputable publishers; script performs no code execution or active-content rendering from feed input; content is stripped to plain text before rendering | Accepted residual risk |
| 4 | Over-privileged automation credential | Access Control | Very low | Low | Workflow permissions explicitly scoped to `contents: write` only; no other permissions granted; token is ephemeral (job-scoped) | Closed |
| 5 | Exposure of sensitive data via public repository | Security Principles (Confidentiality) | N/A | N/A | No secrets, credentials, or confidential data are stored or referenced anywhere in the codebase | Not applicable |
| 6 | Third-party RSS-generation service (rss.app), if adopted for sources lacking a native feed | Business Continuity / Vendor Risk | Low | Low | Service only observes which public pages are being monitored; no confidential data is shared; recommend routing through standard vendor-risk process if formally required | Open — pending business decision |
| 7 | Service disruption from a dead or malformed feed | Availability | Medium | Very low | Per-feed exception handling; a single failed source is reported inline in the PDF and does not interrupt the run | Closed |
| 8 | Anthropic content sourced via a third-party mirror (Alan Turing Institute's `ai-rss-feeds` project) rather than directly from Anthropic, since Anthropic publishes no native RSS feed | Security Principles (Integrity / Provenance) | Low | Low | Maintainer is a named, reputable, non-anonymous institution (UK's national AI institute) with a public, auditable generation process; content is scraped verbatim from the original page, not summarized or altered | Accepted residual risk |

## 5. Residual Risk Statement

Overall residual risk is assessed as **Low**. The automation has no inbound
network exposure, processes no personal or confidential data, and holds no
standing credentials beyond a job-scoped, minimally permissioned token. The
one open item (Action SHA-pinning) is a hardening step with no exploitation
path identified to date; it is tracked for completion at deployment rather
than blocking rollout.

## 6. Recommendations

1. Pin `softprops/action-gh-release` to a commit SHA at deployment (see README).
2. Re-run this assessment if additional feed sources are added outside the
   currently vetted list, particularly any source requiring authentication
   or a third-party aggregation service.
3. Review dependency pins (`requirements.txt`) periodically for known CVEs.

## 7. Sign-off

| Role | Name | Date |
|---|---|---|
| Author | Alexandra | 2026-07-03 |
| Reviewed by | | |
