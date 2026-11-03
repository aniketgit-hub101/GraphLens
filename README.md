# GraphLens

GraphLens is a Python project scaffold for a GraphQL authorization regression testing harness. Its planned purpose is to detect seeded Broken Object Level Authorization (BOLA) and Broken Object Property Level Authorization (BOPLA) defects in a deterministic synthetic API.

This repository currently contains the initial structure only. The API, authorization policies, test corpus, mutants, benchmark engine, and reporting behavior have not been implemented. No benchmark results are included.

## Requirements

- Python 3.11 or newer
- `graphql-core`
- `pytest`
- `requests`

Install dependencies and inspect the scaffold:

```bash
python -m venv .venv
# Activate the environment, then:
python -m pip install -r requirements.txt
```

The application entry point is reserved at `main.py`; running it reports that the CLI is not implemented yet.

## Project layout

```text
api/        Synthetic GraphQL schema, resolvers, and deterministic data
policies/   Machine-readable authorization rules and policy evaluation
tests/      Fixed GraphQL regression corpus and pytest checks
mutants/    Independently switchable seeded security defects
engine/     Query execution, verdicts, and benchmark orchestration
reports/    Terminal and JSON report formatting
dashboard/  Optional future interface; CLI comes first
results/    Local benchmark output (generated files are ignored by Git)
docs/       Design notes and developer coordination
main.py     Future CLI entry point
```

## Three-developer split

To work independently, agree on the shared case, configuration, and result interfaces in `docs/` before implementation:

1. **API and mutants:** own `api/` and `mutants/`; provide a deterministic executable GraphQL schema and documented mutant switches.
2. **Policies and corpus:** own `policies/` and `tests/`; define expected access and stable test-case identifiers without tuning cases to fit mutant output.
3. **Engine and reports:** own `engine/`, `reports/`, and `main.py`; consume the shared interfaces, run each test/configuration pair once, and serialize measured output.

`dashboard/` can be picked up after the CLI and report contract are stable. Coordinate changes to shared interfaces through `docs/` and review them together before merging parallel work.

## Git setup

This opened workspace is already a Git repository. To create the first commit from its root after reviewing the files:

```bash
git status
git add .
git commit -m "Initialize GraphLens project scaffold"
```

For a fresh copy that has no `.git` directory, run `git init` from the project root before those commands.
