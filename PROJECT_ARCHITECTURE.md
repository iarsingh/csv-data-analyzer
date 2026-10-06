# csv-data-analyzer — project architecture

[README](README.md) · [Interview questions and answers](INTERVIEW_QA.md)

## Purpose and scope

Paste a CSV. The API detects the delimiter (comma, semicolon, tab, or pipe), infers each column's type, and profiles it.

This document describes files and symbols in this checkout. Deployment templates and statements in the original overview are distinguished from a verified running environment.

## Component diagram

```mermaid
flowchart LR
    M0["src/csvtool/__init__.py"]
    M1["src/csvtool/analyze.py"]
    M2["src/csvtool/main.py"]
    M3["src/csvtool/ops.py"]
    M2 -->|imports| M1
    M2 -->|imports| M3
```

For Python repositories, arrows show resolved local imports, not network calls or deployment order. Otherwise the diagram is a repository component map; containment arrows do not assert runtime integration.

## Components and responsibilities

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

## Existing design and operating guides

These checked-in guides provide the project’s detailed design, operational context, or deployment view:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Request interface

| Method and path | Handler | Source |
| --- | --- | --- |
| `GET /healthz` | `healthz` | [`src/csvtool/main.py`](src/csvtool/main.py#L30) |
| `POST /analyze` | `post_analyze` | [`src/csvtool/main.py`](src/csvtool/main.py#L35) |
| `POST /group` | `post_group` | [`src/csvtool/main.py`](src/csvtool/main.py#L40) |
| `GET /readyz` | `readyz` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L74) |
| `POST /workspaces` | `create_workspace` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L80) |
| `GET /workspaces` | `list_workspaces` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L98) |
| `POST /workspaces/{workspace_id}/jobs` | `create_job` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L106) |
| `GET /jobs/{job_id}` | `get_job` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L130) |
| `POST /jobs/{job_id}/approve` | `approve_job` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L140) |
| `GET /audit` | `audit` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L160) |
| `GET /metrics` | `metrics` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L176) |

The table lists literal route decorators found in the inspected Python modules. Router prefixes and middleware can add behavior; check the linked handler and application setup before calling an endpoint.

## Implementation walkthrough

### `group_by(text, key, value, operation='sum')`

Source: [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104).

Calls visible in this function: `CsvError`, `groups.items`, `groups.setdefault`, `groups.setdefault(str(row[key]).strip(), []).append`, `len`, `max`, `min`, `number`, `read`, `round`, `sorted`, `str`.

```python
def group_by(text, key, value, operation="sum"):
    rows, columns, _ = read(text)
    for column in (key, value):
        if column not in columns:
            raise CsvError(f"column {column} is not in the CSV")
    if operation not in {"sum", "mean", "count", "min", "max"}:
        raise CsvError("operation must be sum, mean, count, min, or max")
    groups = {}
    skipped = 0
    for row in rows:
        raw = str(row[value] or "").strip()
        parsed = number(raw) if raw else None
        if operation != "count" and parsed is None:
            skipped += 1
            continue
        groups.setdefault(str(row[key]).strip(), []).append(parsed)
    result = {}
    for name, values in sorted(groups.items()):
        if operation == "count":
            result[name] = len(values)
        elif operation == "sum":
            result[name] = round(sum(values), 4)
```

The excerpt is truncated; the linked source contains the full implementation.

### `profile(values)`

Source: [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L66).

Calls visible in this function: `Counter`, `Counter(present).most_common`, `column.update`, `float`, `infer`, `len`, `math.sqrt`, `max`, `median`, `min`, `round`, `set`.

```python
def profile(values):
    present = [value for value in values if value != ""]
    kind = infer(values)
    column = {"type": kind, "nulls": len(values) - len(present), "distinct": len(set(present))}
    if kind in {"integer", "float"}:
        numbers = sorted(float(value) for value in present)
        mean = sum(numbers) / len(numbers)
        variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
        column.update(
            {
                "min": numbers[0],
                "max": numbers[-1],
                "mean": round(mean, 4),
                "median": round(median(numbers), 4),
                "stddev": round(math.sqrt(variance), 4),
            }
        )
    elif kind in {"text", "boolean", "date"}:
        column["top"] = [{"value": value, "count": count} for value, count in Counter(present).most_common(3)]
        if kind == "date":
            column["min"] = min(present)
            column["max"] = max(present)
```

The excerpt is truncated; the linked source contains the full implementation.

### `read(text)`

Source: [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L16).

Calls visible in this function: `(name or '').strip`, `CsvError`, `any`, `body.splitlines`, `csv.DictReader`, `csv.Sniffer`, `csv.Sniffer().sniff`, `io.StringIO`, `len`, `list`, `rows.append`, `set`.

```python
def read(text):
    body = text.strip()
    if not body:
        raise CsvError("CSV is empty")
    try:
        dialect = csv.Sniffer().sniff(body.splitlines()[0], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(body), dialect=dialect)
    if not reader.fieldnames or any(not (name or "").strip() for name in reader.fieldnames):
        raise CsvError("every column needs a header")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise CsvError("column headers must be unique")
    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > MAX_ROWS:
            raise CsvError(f"CSV has more than {MAX_ROWS} rows")
    return rows, list(reader.fieldnames), dialect.delimiter
```

### `infer(values)`

Source: [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L44).

Calls visible in this function: `DATE.fullmatch`, `all`, `number`, `re.fullmatch`, `value.lower`.

```python
def infer(values):
    present = [value for value in values if value != ""]
    if not present:
        return "empty"
    if all(value.lower() in BOOLEANS for value in present):
        return "boolean"
    if all(re.fullmatch(r"-?\d+", value) for value in present):
        return "integer"
    if all(number(value) is not None for value in present):
        return "float"
    if all(DATE.fullmatch(value) for value in present):
        return "date"
    return "text"
```

## Validation and failure paths

| Explicit exception | Source |
| --- | --- |
| `CsvError('CSV is empty')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L19) |
| `CsvError('every column needs a header')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L26) |
| `CsvError('column headers must be unique')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L28) |
| `CsvError('operation must be sum, mean, count, min, or max')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L110) |
| `CsvError(f'CSV has more than {MAX_ROWS} rows')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L33) |
| `CsvError(f'column {column} is not in the CSV')` | [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L108) |
| `HTTPException(status_code=422, detail=str(exc))` | [`src/csvtool/main.py`](src/csvtool/main.py#L26) |
| `HTTPException(status_code=404, detail='workspace not found')` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L77) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L100) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L109) |
| `HTTPException(status_code=403, detail='production apply is disabled in this lab')` | [`src/csvtool/ops.py`](src/csvtool/ops.py#L113) |

These are explicit exceptions in the inspected source, rather than a claim that every failure is handled. Follow the calling handler to see whether the exception becomes an HTTP response or propagates.

## Data and state

- [`src/csvtool/analyze.py`](src/csvtool/analyze.py) defines module-level containers: `BOOLEANS`.
- [`src/csvtool/ops.py`](src/csvtool/ops.py) defines module-level containers: `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`.

Module-level dictionaries/lists live in a Python process. They can be fixtures or mutable state; inspect writes before treating them as persistent storage. A production extension would need to define persistence and concurrency behavior explicitly.

## Data flow and design decisions

### What is the input-to-output contract of `group_by`

In [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104), `group_by(text, key, value, operation='sum')` receives the inputs. The function computes these intermediate values:

- `rows, columns, _ = read(text)`
- `groups = {}`
- `skipped = 0`
- `result = {}`

Its result is defined by:

- `{'key': key, 'value': value, 'operation': operation, 'groups': result, 'skipped': skipped}`

### Which decision rules or boundary conditions should an interviewer challenge

The implementation in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104) branches on:

- `operation not in {'sum', 'mean', 'count', 'min', 'max'}`
- `column not in columns`
- `operation != 'count' and parsed is None`
- `operation == 'count'`
- `operation == 'sum'`
- `operation == 'mean'`
- `operation == 'min'`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

### What does the operations plane add, and where is its limit

[`src/csvtool/ops.py`](src/csvtool/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.

## Setup and verification

The following commands are derived from the checked-in dependency/test contracts. Execute them from the repository root; the block prepares a local environment, not a cloud deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Python dependencies: [`requirements.txt`](requirements.txt).

Test entry points: [`tests/test_analyze.py`](tests/test_analyze.py), [`tests/test_ops.py`](tests/test_ops.py).

Automation definitions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Read their triggers and job steps to determine what CI actually runs.

## Operating boundaries and design review

Before turning this checkout into a customer deployment, establish the input contract, data ownership, access controls, failure response, evaluation criteria, and rollback owner. Repository fixtures and unit tests demonstrate local behavior; they do not establish throughput, uptime, compliance, or business impact.

A useful architecture review starts with the linked implementation: identify where input enters, where a decision is made, which state can change, and which external dependency can fail. Add a deployment view only for infrastructure that is actually configured and exercised.
