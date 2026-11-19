# EV Charging Infrastructure Gap Analysis

Cloud Native Data Engineering (CNDE) Final Project, Group 3: Norah Alshahrani, Avinash Sriram, Marwa Alsleebi, Zhehao (Jack) Zhang.

**Business question:** where should a charging network operator build its next public stations? We combine existing charger supply (NREL/AFDC stations API), EV demand (AFDC state registrations), and operating-cost proxy (EIA electricity prices) into an explainable, state-level gap score, delivered through a Tableau dashboard.

> **Status:** scaffold only (K2, 2026-11-19). Sections marked *TBD* are filled in by the owning Part as work lands. Scope is the MVP (five mandatory layers); extensions are future work.

## Architecture

```
NREL/AFDC stations API ─┐
AFDC registrations file ├─> Python ingestion (Docker) ─> GCS raw zone  raw/YYYY-MM-DD/<source>/
EIA API v2 prices ──────┘                                   │
                                     ┌──────────────────────┴───────────────────┐
                                     ▼                                          ▼
                     PostgreSQL OLTP (3NF, Docker)             Databricks Medallion (Delta)
                                                               Bronze → Silver → Gold
                                                                                │
                                                                                ▼
                                                                    Tableau dashboard
CI: GitHub Actions (ruff, pytest, Postgres service container, docker build)
```

Analytical platform is Databricks Free Edition **pending the K5 Tableau connection test**; the decision and fallback are recorded in [`Docs/decisions.md`](Docs/decisions.md). A rendered diagram replaces this sketch in W2-11.

## Repository layout

| Path | Contents | Owner |
|---|---|---|
| `Docs/` | Scope approval, data contract, decisions log, profiling, cleaning rules, gap score, tradeoffs, recommendations, ERD, deck | All |
| `Scripts/ingestion/` | Source modules, shared HTTP client, GCS upload, Databricks push | Part A |
| `Scripts/common/` | Shared cleaning module (used by Postgres loader and Silver) | Part A |
| `Scripts/profiling/` | Profiling script, EDA notebook | Part A |
| `Scripts/sql/`, `Scripts/load/` | Postgres DDL/DML/analytics/assertions, loader | Part B |
| `Scripts/databricks/` | Bronze/Silver/Gold notebooks (source format), Gold assertions | Part C |
| `Scripts/deploy/` | gcloud bucket create/teardown, GitHub repo setup | Parts A, D |
| `Scripts/tests/` | pytest suites and small sample fixtures | All (wired by D) |
| `Docker/` | Dockerfile, docker-compose.yml, `.env.example` | Part D |
| `.github/workflows/` | CI | Part D |
| `BI/` | Wireframes, packaged `.twbx`, screenshots | Part D |
| `Video/` | Link to the recorded briefing | Part B |

## Team and ownership

Parts were assigned by random draw at kickoff (11/18). Each member commits their Part under their own GitHub account and presents it in the video.

| Part | Layer | Owner | Reviews PRs of |
|---|---|---|---|
| A | Data Acquisition and Quality | _TBD_ | B |
| B | Operational Store and Business Framing | _TBD_ | C |
| C | Lakehouse and Gap Analytics | _TBD_ | D |
| D | DevOps and Visual Delivery | _TBD_ | A |

Platform owners: GCP = Part A, Databricks = Part C, GitHub admin = Avinash (settings managed by Part D). Never share passwords; owners add teammates as users.

## Developer setup

```bash
git clone https://github.com/avinashsriram1/CNDE-Final-Project.git
cd CNDE-Final-Project
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp Docker/.env.example Docker/.env                      # fill in your own keys; never commit
ruff check . && ruff format --check . && pytest
```

## Contribution workflow

1. Branch per task: `<part>/<task-id>-<slug>`, e.g. `a/k3-data-contract`.
2. Small commits under your own account. Add tests for your own code.
3. Open a PR (template auto-fills). Request your rotating reviewer.
4. Merge only with 1 approval and green CI. A task is **done** when merged to `main`, not when it works on a laptop.

## Reproduction (end to end)

*TBD (W2-11, Part D).* Will cover: prerequisites and free accounts, `docker compose` one-command run (ingest → GCS → Postgres load → tests), Databricks notebook order, Tableau connection, and expected row counts. Verified by two fresh-clone tests (12/5, 12/8).

## Teardown and cost

Target spend is $0. After each session: stop containers (`docker compose down`), suspend/stop any Databricks compute, and keep the GCS bucket in us-central1. Final teardown script: `Scripts/deploy/teardown.sh` (*TBD*, Part A).

## Presentation

Video link: see [`Video/link.md`](Video/link.md) (*TBD*, 12/9).

## AI usage disclosure

We used generative AI (Claude) as an assistant for parts of this project. What it helped with, and who verified it, is logged in [`AI_USAGE.md`](AI_USAGE.md). The team is responsible for the correctness of everything submitted.

## References

See [`References.md`](References.md).
