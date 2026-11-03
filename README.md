# GraphLens

GraphLens is a policy-driven GraphQL authorization regression testing harness for detecting seeded Broken Object Level Authorization (BOLA) and Broken Object Property Level Authorization (BOPLA) defects. It evaluates returned GraphQL data against explicit authorization policy; HTTP 200 and successful GraphQL execution alone do not establish that access was authorized.

The project is a controlled synthetic API demonstration, not a production vulnerability scanner. The current repository is an initial scaffold; the API, policy evaluator, fixed query corpus, mutants, benchmark engine, reports, and dashboard are not yet implemented. Do not treat placeholder output as benchmark evidence.

## Technology and planned scope

- Python 3.11+
- `graphql-core` for the synthetic GraphQL schema and query execution
- `pytest` for deterministic authorization regression tests
- `requests` for optional HTTP-based synthetic API integration
- Flask only if a dashboard is justified after the CLI works

The planned benchmark uses Alice (invoice owner), Bob (authenticated non-owner), and Anonymous identities. Twelve fixed tests cover root-level BOLA, nested-object BOLA, and property-level BOPLA. Six configurations comprise the patched baseline, four independently switchable mutants, and the combined mutant configuration. The target size is 72 test/configuration units; result distributions must be measured from execution, not hardcoded.

## Repository structure

```text
api/        Synthetic GraphQL schema, resolvers, and deterministic data
policies/   Machine-readable access rules and evaluator
tests/      Fixed query corpus and pytest checks
mutants/    Independent seeded security mutants
engine/     Query execution, verdicts, and benchmark orchestration
reports/    Terminal and JSON reporting
dashboard/  Optional future interface; CLI comes first
results/    Generated benchmark output (not committed)
docs/       Integration contracts, status, and design decisions
main.py     Planned CLI entry point
```

Exactly three verdicts are planned: `PASS`, `POLICY_VIOLATION`, and `INCONCLUSIVE`. A violation requires evidence of an unauthorized object or restricted property in the returned data. Missing or unreliable evidence is inconclusive.

## Team ownership

| Teammate | Responsibility | Branch |
| --- | --- | --- |
| Aniket Gautam (`aniketgit-hub101`) | Project lead, core engine, integration | `main`, `feature/engine` |
| Adeel Ahmad (`adeelad726`) | GraphQL API | `feature/graphql-api` |
| Abhay Shukla (`abhyashukla16`) | Security tests and mutants | `feature/security-tests` |
| Akash Bajpai | QA, documentation, and demonstration preparation | — |

Coordinate shared interfaces in `docs/` before parallel implementation. Keep module ownership clear and review changes to shared contracts together. Akash coordinates QA and documentation without requiring a development laptop.

## Setup

Clone the central repository and install dependencies in a virtual environment:

```powershell
git clone https://github.com/aniketgit-hub101/graphlens.git
cd graphlens
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The current scaffold does not yet provide a working benchmark command. Once implemented, the intended checks are `python -m pytest -q` and `python main.py`.

## Branch workflow

Each developer works on their assigned branch, commits only their changes, and opens a pull request to `main`. Before starting, fetch the latest refs and switch to the assigned branch:

```powershell
git fetch origin
git switch --track origin/feature/engine
```

Use `feature/graphql-api` for Adeel or `feature/security-tests` for Abhay. Before committing, inspect `git status` and stage only the files you changed. Keep `main` stable for integration and demonstration. Do not force-push shared branches.

To propose work, open a pull request from the assigned branch to `main`; review and merge it before treating it as integrated. After `main` advances, update the feature branch with `git fetch origin` and `git merge origin/main`, resolve conflicts, and push the feature branch.
