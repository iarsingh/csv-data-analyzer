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
    M2 -->|imports| M1
```

For Python repositories, arrows show resolved local imports, not network calls or deployment order. Otherwise the diagram is a repository component map; containment arrows do not assert runtime integration.

## Components and responsibilities

| Component | Responsibility |
| --- | --- |
| [`src/csvtool/main.py`](src/csvtool/main.py) | HTTP handlers: `GET /healthz`, `POST /analyze`, `POST /group` |
| [`src/csvtool/analyze.py`](src/csvtool/analyze.py) | Functions: `read`, `number`, `infer`, `median`, `profile`, `analyze`, `group_by` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/csvtool/__init__.py`](src/csvtool/__init__.py) | Implementation or supporting configuration |
| [`tests/test_analyze.py`](tests/test_analyze.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |

## Request interface

| Method and path | Handler | Source |
| --- | --- | --- |
| `GET /healthz` | `healthz` | [`src/csvtool/main.py`](src/csvtool/main.py#L28) |
| `POST /analyze` | `post_analyze` | [`src/csvtool/main.py`](src/csvtool/main.py#L33) |
| `POST /group` | `post_group` | [`src/csvtool/main.py`](src/csvtool/main.py#L38) |

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
| `HTTPException(status_code=422, detail=str(exc))` | [`src/csvtool/main.py`](src/csvtool/main.py#L24) |

These are explicit exceptions in the inspected source, rather than a claim that every failure is handled. Follow the calling handler to see whether the exception becomes an HTTP response or propagates.

## Data and state

- [`src/csvtool/analyze.py`](src/csvtool/analyze.py) defines module-level containers: `BOOLEANS`.

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

## Setup and verification

The following commands are derived from the checked-in dependency/test contracts. Execute them from the repository root; the block prepares a local environment, not a cloud deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Python dependencies: [`requirements.txt`](requirements.txt).

Test entry points: [`tests/test_analyze.py`](tests/test_analyze.py).

Automation definitions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Read their triggers and job steps to determine what CI actually runs.

## Operating boundaries and design review

Before turning this checkout into a customer deployment, establish the input contract, data ownership, access controls, failure response, evaluation criteria, and rollback owner. Repository fixtures and unit tests demonstrate local behavior; they do not establish throughput, uptime, compliance, or business impact.

A useful architecture review starts with the linked implementation: identify where input enters, where a decision is made, which state can change, and which external dependency can fail. Add a deployment view only for infrastructure that is actually configured and exercised.
