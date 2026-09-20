# ChemOT-Align

## Evidence-first incident analysis for chemical process and IT/OT security

ChemOT-Align is an offline research platform for building and evaluating an LLM that analyzes chemical-process and IT/OT security incidents from auditable evidence.

The platform connects three concerns in one reproducible workflow:

- chemical-process dynamics, operating bounds, alarms, and safety reasoning;
- provenance-aware network, Linux, web/DB, and IDS evidence;
- baseline, post-training, Secure RAG, and adversarial evaluation.

ChemOT-Align is an analysis and research service. It is not a plant controller, network operator, autonomous security agent, or industrial safety certification.

## What is available now

| Capability | Status | Entry point |
| --- | --- | --- |
| Read-only project contract and healthcheck | Ready | `chemot-align healthcheck` |
| Typed evidence, incident, and model-output contracts | Ready | `src/chemot_align/schemas/` |
| Provenance records and sensitive-text redaction | Ready | `src/chemot_align/provenance/`, `src/chemot_align/safety/` |
| Deterministic bounded CSTR simulator | Ready | `src/chemot_align/process_sim/` |
| Bounded fault injection | Ready | `src/chemot_align/process_sim/faults.py` |
| Scenario generation, process evidence, and ground truth | Ready | `src/chemot_align/scenario_engine/` |
| ALEPH-scoped Lab adapters | Planned | Task 5 |
| Leakage-safe evidence normalization and splits | Planned | Task 6 |
| Secure local RAG | Planned | Task 7 |
| Baseline model and evaluation harness | Planned | Tasks 8-9 |
| SFT, preference optimization, Reward/RLAIF | Planned | Tasks 10-12 |
| Offline incident-analysis demo | Planned | Task 15 |

## How the service works

```text
process config -> CSTR simulator -> bounded faults -> scenario generator
                                               -> evidence + ground truth
                                               -> IncidentCase + provenance

future Lab fixtures ---------------------------> normalized IncidentCase
```

The process simulator, future Packet Tracer fixtures, and future VirtualBox Lab adapters remain separate producers. Their integration point is a validated, provenance-labeled evidence contract rather than an assumed real-time bridge.

## Safety boundary

ChemOT-Align does not:

- connect to a real chemical plant, industrial network, or enterprise system;
- autonomously change PLCs, firewalls, accounts, services, or files;
- collect or publish credentials, private keys, flags, or sensitive logs;
- generate chemical synthesis instructions or hazardous operating procedures;
- treat a failed, empty, stale, or conflicted observation as normal evidence.

Synthetic faults are limited to named, bounded fault families. Scenario files cannot execute shell commands, open URLs, or inject unbounded numeric values. Security experiments are limited to an owned or explicitly authorized isolated Lab, and the initial tool policy is read-only.

## Quickstart

The repository targets Python 3.12.x. The current development environment uses a local `.venv`, which is ignored by Git.

### Verify the environment

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
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

### Generate a reproducible process incident case

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -c "from pathlib import Path; from chemot_align.scenario_engine import ScenarioGenerator, ScenarioSpec; c=ScenarioGenerator().generate(ScenarioSpec.from_yaml(Path('scenarios/process/cooling_loss.yaml')), seed=42); print(c.case_id, c.ground_truth.incident_class.value, len(c.evidence), c.provenance.source_hash)"
```

This generates a schema-valid `IncidentCase` with a deterministic case ID, synthetic process evidence, fault-derived ground truth, the seed, and the scenario-file SHA-256.

## Scenario catalog

| Scenario | Purpose | Expected class |
| --- | --- | --- |
| `normal_cstr.yaml` | Stable baseline operation | `normal` |
| `sensor_drift.yaml` | Measurement drift without changing true state | `sensor_fault` |
| `valve_delay.yaml` | Delayed manipulated-valve response | `process_fault` |
| `cooling_loss.yaml` | Reduced cooling capacity | `process_fault` |

Every scenario uses the same bounded CSTR configuration, declares its fault window and target asset, and records the source hash in the generated case provenance.

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
scenarios/process/       bounded normal and fault scenario definitions
docs/                    specification, threat model, cards, and reports
src/chemot_align/
  schemas/               typed evidence and incident contracts
  provenance/            execution and source traceability
  safety/                redaction and safety boundaries
  process_sim/           bounded chemical-process simulation and faults
  scenario_engine/       scenario loading, generation, and ground truth
data/                    raw/interim/private and processed/public data roots
tests/                   focused unit and integration tests
```

Raw Lab output, checkpoints, credentials, and private generated data must remain outside public Git. `data/manifests/` is reserved for reproducibility metadata.

## Development status

The project is being built as vertical slices. A later stage may add a feature only after its focused tests and provenance contract are in place. A model failure, parser failure, CUDA OOM, unavailable Lab, or non-computable metric remains a recorded failure rather than a fabricated success.

Current verified local slice:

- Task 1: project contract, environment checks, and package bootstrap;
- Task 2: evidence/incident contracts, provenance, and redaction safeguards;
- Task 3: deterministic bounded CSTR simulation and safety checks;
- Task 4: bounded faults, process scenarios, synthetic evidence, and ground truth.

## Documentation

- [Approved project specification](docs/superpowers/specs/2026-09-20-chemot-align-design.md)
- [Project configuration](configs/project.yaml)
- [CSTR baseline configuration](configs/process/cstr_baseline.yaml)
- [Process scenario catalog](scenarios/process/)
- [SHA-256 source manifest](docs/superpowers/specs/SHA256SUMS)

## License and provenance

The repository source is intended for research and education. Third-party models, datasets, documents, and Lab outputs retain their own licenses and provenance requirements. This project must not be presented as an industrial safety certification or real-time operational control system.
