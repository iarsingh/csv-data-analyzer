# CSV Data Analyzer

<!-- project-guide:start -->
## Project guide

[Project architecture](PROJECT_ARCHITECTURE.md) · [Interview questions and answers](INTERVIEW_QA.md)

Use the architecture document for the component diagram, implementation boundaries, and verification entry points. The interview guide includes source-backed answers and project walkthroughs.

### Implementation map

| Component | Responsibility |
| --- | --- |
| [`src/csvtool/main.py`](src/csvtool/main.py) | HTTP handlers: `GET /healthz`, `POST /analyze`, `POST /group` |
| [`src/csvtool/ops.py`](src/csvtool/ops.py) | HTTP handlers: `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}` |
| [`src/csvtool/analyze.py`](src/csvtool/analyze.py) | Functions: `read`, `number`, `infer`, `median`, `profile`, `analyze`, `group_by` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/csvtool/__init__.py`](src/csvtool/__init__.py) | Implementation or supporting configuration |
| [`Dockerfile`](Dockerfile) | Container build/service configuration |
| [`Makefile`](Makefile) | Implementation or supporting configuration |
| [`docker-compose.yml`](docker-compose.yml) | Container build/service configuration |
| [`tests/test_analyze.py`](tests/test_analyze.py) | Executable checks and regression examples |
| [`tests/test_ops.py`](tests/test_ops.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Project explanations or operating notes |

### Local setup and verification

From the repository root (the commands follow the checked-in manifests):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

To serve the FastAPI application locally, install the server separately if it is not already available:

```bash
python -m pip install uvicorn
PYTHONPATH=src python -m uvicorn csvtool.main:app --reload
```

<!-- project-guide:end -->

Level: 1 — Python fundamentals

Skills: Python, CSV, type inference, summary statistics, group-by

Paste a CSV. The API detects the delimiter (comma, semicolon, tab, or pipe), infers each column's type, and profiles it.

| Column type | Profile |
| --- | --- |
| integer, float | nulls, distinct, min, max, mean, median, population standard deviation |
| text, boolean | nulls, distinct, the three most common values |
| date (`YYYY-MM-DD`) | the same as text, plus the earliest and latest date |

`POST /group` aggregates one column by another with `sum`, `mean`, `count`, `min`, or `max`. Rows whose value is blank or not a number are skipped and counted, except for `count`.

```bash
pip install -r requirements.txt
pytest -q
PYTHONPATH=src uvicorn csvtool.main:app --reload
```

```bash
curl -s -X POST localhost:8000/group -H 'content-type: application/json' \
  -d '{"csv":"region,revenue\nnorth,10\nnorth,30\nwest,20\n","key":"region","value":"revenue"}'
```

## What it refuses

- An empty CSV, a blank header, or two columns with the same header.
- A group-by on a column that does not exist, or an operation outside the five.
- More than 100,000 rows in one request.

It does not write a file.

## Ops plane

Workspaces, tenant isolation, job approval, and audit live under `/v1`. Production apply is refused. See `docs/ARCHITECTURE.md`.

## Documentation checks

Project architecture, interview guides, and local source links are checked automatically on pushes and pull requests. Run the same check locally:

```bash
python3 .github/scripts/validate_project_docs.py
```

See [service improvements and local run instructions](docs/UPGRADES.md).
