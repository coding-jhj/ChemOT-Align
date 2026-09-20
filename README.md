# ChemOT-Align

Chemical Process OT Security Post-Training Research Platform.

ChemOT-Align is an offline research platform for analyzing combined chemical-process and IT/OT security incidents with evidence-first structured outputs. It does not control real plants or industrial networks, and its initial tool policy is read-only.

## Current status

Task 1 establishes the repository contract, environment declaration, immutable project configuration, and healthcheck CLI. Training, live Lab collection, and external-system integration are not part of this bootstrap step.

## Repository contract

- Python target: 3.12.3-compatible environment
- Tool mode: `read_only`
- Evidence statuses: `executed`, `official_checked`, `synthetic`, `inferred`, `unverified`, `redacted`
- Raw Lab output, credentials, checkpoints, and generated private artifacts stay outside public Git
- Public data must pass validation and secret scanning before export

## Local commands

After creating the declared environment and installing the local package, use:

```text
chemot-align healthcheck --config configs/project.yaml
chemot-align print-config --config configs/project.yaml
```

The healthcheck reports unavailable optional resources as unavailable or probe-failed. It does not infer CUDA or model readiness from package presence alone.
