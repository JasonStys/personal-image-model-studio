# CodeQL security analysis

By Jason Stys. Workflow: [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml).

## Purpose and scope

CodeQL builds a source database and executes GitHub's `security-extended` queries for
**Python**, **JavaScript/TypeScript** and **GitHub Actions workflows**. These are the supported
languages present in this repository. `security-extended` includes the default security
queries and additional lower-precision checks; every result requires context and review.
There are no repository-defined path exclusions, query exclusions or dismissed alerts.

The original baseline on 2026-11-09 had default setup `not-configured`, and the code-scanning
API reported `no analysis found`. That is missing scan evidence, not a zero-vulnerability
result. The first genuine hosted results and any corrections are recorded in the
[dated scan report](reports/codeql-2026-11-09.md).

## Workflow and trust boundary

- Trigger on pushes to `main`, pull requests targeting `main`, a weekly staggered schedule,
  and explicit manual dispatch. Pull requests use GitHub's merge ref; no
  `pull_request_target` or execution with a privileged base-branch token is used.
- Run one language per isolated Ubuntu job, with a 25-minute deadline and `fail-fast: false`.
  `build-mode: none` reads source without installing the application or executing submitted
  programs, dataset imports, model training or private account workflows.
- Pin CodeQL action **v4.39.3** to `33d7b85da1a04171e211befe2c739303b9a4c066`, resolved through the
  official annotated release tag. `tools: linked` selects its associated CodeQL bundle.
  Review and update the pin when GitHub publishes a supported security update.
- Grant `contents: read` globally; grant `security-events: write` only to the analysis job
  so genuine SARIF can enter GitHub code scanning. Checkout persists no credentials.
  No extra secrets, `contents: write`, deployment, publishing or admin scope is requested.
- Wait for SARIF processing; retain per-language categories. Upload no CodeQL database,
  Actions artifact or cache. The code-scanning SARIF upload is deliberate and separate
  from Actions artifact storage. Failed extraction/query/upload must remain failed.

The action's tag was resolved to a full immutable commit; that pin identifies reviewed
source, rather than claiming the unsigned annotated tag independently authenticates a
publisher. No local/private account data or ignored datasets are sent by this workflow;
its inputs are the repository checkout already available on GitHub.

## Read and act on a result

Open **Security → Code scanning** or the CodeQL check on the pull request. Confirm the
workflow source, language/category, completed extraction and successful result processing.
A passing job does not mean it found no alerts: inspect the actual alerts and source paths.
For each alert record the rule, exact file/line, data-flow context, affected trust boundary
and disposition in the dated report. Correct a demonstrated defect and add a focused
negative regression before scanning the revised commit again. Do not silence a class of
findings with blanket paths, filters, broad suppressions or a fabricated empty SARIF file.

A defensible false positive needs documented source/data-flow evidence. Any proposed
narrow suppression or alert dismissal requires explicit review; none was added in the
initial configuration. API permission failures, incomplete analyses or missing baseline
results remain unknown, never a clean finding.

## Limits and existing checks

SQL, CSS, HTML and packaging/container instructions are not separate CodeQL language scans. Existing model, browser, private-account and native acceptance gates remain required; static extraction is not proof of safe processing for arbitrary untrusted files.

Static queries can miss framework-specific behavior, dynamic values and runtime state.
They do not replace fuzzing, dependency audits, encryption/isolation checks, human review,
manual accessibility checks or operational validation. A clean scan is not a security
certification. CI/docs-only configuration does not rebuild or retarget an existing public
application release, modify installed apps, or migrate private stores.

## Official references

- [Advanced setup and prerequisites](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning).
- [Workflow languages, triggers and categories](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options).
- [Built-in query-suite scope and precision](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-query-suites).
- [Supported languages and unsupported PHP](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-code-scanning).
- [Pinned initialization inputs](https://github.com/github/codeql-action/blob/33d7b85da1a04171e211befe2c739303b9a4c066/init/action.yml)
  and [SARIF upload behavior](https://github.com/github/codeql-action/blob/33d7b85da1a04171e211befe2c739303b9a4c066/analyze/action.yml).
