# ChemOT-Align

## Evidence-first incident analysis for chemical process and IT/OT security

ChemOT-Align is an offline research platform for building and evaluating an LLM that analyzes chemical-process and IT/OT security incidents from auditable evidence.

It connects three concerns in one reproducible workflow:

- chemical-process dynamics, operating bounds, alarms, and safety reasoning;
- network, Linux, web/DB, IDS, and provenance-aware security evidence;
- SFT, preference optimization, Secure RAG, and adversarial evaluation.

The product boundary is deliberately clear: ChemOT-Align is an analysis and research system, not a plant controller, network operator, or autonomous security agent.

## What is available now

| Capability | Status | Entry point |
| --- | --- | --- |
| Read-only project contract and healthcheck | Ready | `chemot-align healthcheck` |
| Typed evidence, incident, and model-output contracts | Ready | `src/chemot_align/schemas/` |
| Provenance records and sensitive-text redaction | Ready | `src/chemot_align/provenance/`, `src/chemot_align/safety/` |
| Deterministic bounded CSTR simulator | Ready | `src/chemot_align/process_sim/` |
| ALEPH-scoped Lab adapters | Planned | Task 5 |
| Secure local RAG | Planned | Task 7 |
| Baseline model and evaluation harness | Planned | Tasks 8–9 |
| SFT, preference optimization, Reward/RLAIF | Planned | Tasks 10–12 |
| Offline incident-analysis demo | Planned | Task 15 |

## How the platform works

```text
Process simulator ─┐
                   ├─> typed evidence ─> incident case ─> analysis ─> evaluation report
Security Lab ──────┘             │              │                 │
                                 └─ provenance ──┴─ read-only boundary
```

Packet Tracer, VirtualBox, and the Python simulator remain separate producers. They are connected through normalized evidence rather than an assumed real-time bridge.

## Safety boundary

ChemOT-Align does not:

- connect to a real chemical plant, industrial network, or enterprise system;
- autonomously change PLCs, firewalls, accounts, services, or files;
- collect or publish credentials, private keys, flags, or sensitive logs;
- generate chemical synthesis instructions or hazardous operating procedures;
- treat a failed, empty, stale, or conflicted observation as normal evidence.

Security experiments are limited to an owned or explicitly authorized isolated Lab. The initial tool policy is read-only, and public artifacts must pass provenance and secret checks.

## Quickstart

The repository targets Python 3.12.x. The current development environment uses a local `.venv` and keeps it out of Git.

### Verify the environment

```powershell
\.venv\Scripts\python.exe -m pytest -q
\.venv\Scripts\ruff.exe check src tests
```

### Run the project healthcheck

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m chemot_align healthcheck --config configs/project.yaml
```

The healthcheck reports observed Python, package, directory, CUDA, and model-probe states. An unavailable optional resource is not reported as ready.

### Run the CSTR simulator

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -c "from pathlib import Path; from chemot_align.process_sim import CSTRConfig, ProcessSimulator; c=CSTRConfig.from_yaml(Path('configs/process/cstr_baseline.yaml')); o=ProcessSimulator(c).simulate(steps=3, seed=42); print([(x.step, round(x.state.temperature, 3), x.alarms) for x in o])"
```

The simulator is deterministic for a fixed seed, rejects invalid controls instead of silently clamping them, and emits safety violations with synthetic provenance.

## Research workflow

```text
1. Generate bounded process or Lab observations
2. Preserve source, seed, trust, integrity, and execution status
3. Normalize observations into IncidentCase records
4. Analyze with a structured evidence-first output contract
5. Evaluate usefulness, grounding, safety, and adversarial robustness
6. Publish only reproducible, redacted artifacts
```

The planned model comparison is:

```text
M0 Baseline
M1 Domain SFT
M2 SFT + Preference
M3 Secure Alignment
M4 Secure RAG
M5 Reward Model / RLAIF
```

Every experiment must preserve the model identity, dataset and split hashes, seed, environment, command, runtime, memory, output artifact, and failure state.

## Repository map

```text
configs/                 versioned project and process configuration
docs/                    specification, threat model, cards, and reports
src/chemot_align/
  schemas/               typed evidence and incident contracts
  provenance/            execution and source traceability
  safety/                redaction and safety boundaries
  process_sim/           bounded chemical-process simulation
scenarios/               future process and Lab scenario definitions
data/                    raw/interim/private and processed/public data roots
tests/                   focused unit and integration tests
```

Raw Lab output, checkpoints, credentials, and private generated data must remain outside public Git. `data/manifests/` is reserved for reproducibility metadata.

## Development status

The project is being built as vertical slices. A later stage may add a feature only after its focused tests and provenance contract are in place. A model failure, parser failure, CUDA OOM, unavailable Lab, or non-computable metric remains a recorded failure rather than a fabricated success.

## Documentation

- [Approved project specification](docs/superpowers/specs/2026-09-20-chemot-align-design.md)
- [Project configuration](configs/project.yaml)
- [CSTR baseline configuration](configs/process/cstr_baseline.yaml)
- [SHA-256 source manifest](docs/superpowers/specs/SHA256SUMS)

## License and provenance

The repository source is intended for research and education. Third-party models, datasets, documents, and Lab outputs retain their own licenses and provenance requirements. This project must not be presented as an industrial safety certification or real-time operational control system.
