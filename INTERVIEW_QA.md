# csv-data-analyzer — interview questions and answers

[README](README.md) · [Project architecture](PROJECT_ARCHITECTURE.md)

Answers below use this repository’s files and implementation. They distinguish existing behavior from suggested extensions; source links let you verify each walkthrough.

## 1. What problem does csv-data-analyzer address, and what can you demonstrate?

Paste a CSV. The API detects the delimiter (comma, semicolon, tab, or pipe), infers each column's type, and profiles it.

I would demonstrate the linked implementation or examples and distinguish that evidence from any planned production features. Start with [`README.md`](README.md).

## 2. How is this repository organized?

- [`src/csvtool/main.py`](src/csvtool/main.py): Implementation or supporting configuration.
- [`src/csvtool/ops.py`](src/csvtool/ops.py): Implementation or supporting configuration.
- [`src/csvtool/analyze.py`](src/csvtool/analyze.py): Implementation or supporting configuration.
- [`requirements.txt`](requirements.txt): Implementation or supporting configuration.
- [`src/csvtool/__init__.py`](src/csvtool/__init__.py): Implementation or supporting configuration.
- [`Dockerfile`](Dockerfile): Container build/service configuration.
- [`Makefile`](Makefile): Implementation or supporting configuration.
- [`docker-compose.yml`](docker-compose.yml): Container build/service configuration.

[PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) contains the component diagram and the implementation walkthrough.

## 3. Can you walk through `group_by` and explain the decision it makes?

The main walkthrough here is `group_by(text, key, value, operation='sum')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104).

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
```

This is an excerpt; follow the source link for the rest of the branches.

The implementation calls `CsvError`, `groups.items`, `groups.setdefault`, `groups.setdefault(str(row[key]).strip(), []).append`, `len`, `max`, `min`, `number`, `read`. In an interview, trace those calls in execution order using a fixture input.

## 4. What responsibility does `profile` have?

`profile(values)` is defined in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L66).

Its return expressions include:

- `column`

It uses `Counter`, `Counter(present).most_common`, `column.update`, `float`, `infer`, `len`, `math.sqrt`, `max`. This is the code path I would compare against the caller to explain responsibility boundaries.

## 5. What input validation and failure behavior are implemented?

Explicit failure paths include:

- `CsvError('CSV is empty')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L19).
- `CsvError('every column needs a header')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L26).
- `CsvError('column headers must be unique')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L28).
- `CsvError('operation must be sum, mean, count, min, or max')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L110).
- `CsvError(f'CSV has more than {MAX_ROWS} rows')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L33).
- `CsvError(f'column {column} is not in the CSV')` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L108).
- `HTTPException(status_code=422, detail=str(exc))` in [`src/csvtool/main.py`](src/csvtool/main.py#L26).

I would test both the condition that reaches each exception and the caller that translates it. An explicit raise does not mean every malformed input or dependency failure is handled.

## 6. Which test would you use to demonstrate correctness?

[`tests/test_analyze.py`](tests/test_analyze.py#L14) contains `test_means_and_nulls`:

```python
def test_means_and_nulls():
    payload = analyze("region,revenue\nnorth,10\nsouth,\nnorth,30\n").json()
    assert payload["rows"] == 3
    assert payload["nulls"]["revenue"] == 1
    assert payload["means"]["revenue"] == 20
```

This is a concrete regression example from the repository. Its assertions establish that case; they do not establish behavior for every input or under production load.

## 7. What HTTP interface does the code expose?

- `GET /healthz` → `healthz` in [`src/csvtool/main.py`](src/csvtool/main.py#L30).
- `POST /analyze` → `post_analyze` in [`src/csvtool/main.py`](src/csvtool/main.py#L35).
- `POST /group` → `post_group` in [`src/csvtool/main.py`](src/csvtool/main.py#L40).
- `GET /readyz` → `readyz` in [`src/csvtool/ops.py`](src/csvtool/ops.py#L44).
- `POST /workspaces` → `create_workspace` in [`src/csvtool/ops.py`](src/csvtool/ops.py#L49).
- `GET /workspaces` → `list_workspaces` in [`src/csvtool/ops.py`](src/csvtool/ops.py#L66).
- `POST /workspaces/{workspace_id}/jobs` → `create_job` in [`src/csvtool/ops.py`](src/csvtool/ops.py#L73).
- `GET /jobs/{job_id}` → `get_job` in [`src/csvtool/ops.py`](src/csvtool/ops.py#L96).

These are literal decorators. Application/router prefixes, authentication, and middleware must be checked in the corresponding setup code.

## 8. Where does state live, and what happens with multiple workers?

Module-level containers include `BOOLEANS` in [`src/csvtool/analyze.py`](src/csvtool/analyze.py); `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS` in [`src/csvtool/ops.py`](src/csvtool/ops.py).

These containers belong to a Python process. Inspect which are constant fixtures and which are mutated. Mutable process state needs an explicit shared-storage or synchronization strategy before multiple workers can provide consistent behavior.

## 9. How would another engineer reproduce your walkthrough?

Start from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands follow repository manifests; environment setup and command results still need to be checked on the target machine.

## 10. What does automation verify, and what does it not prove?

Inspect [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for triggers, permissions, and job commands. I would name the checks that those definitions run and show the latest run separately. A workflow definition alone does not establish a successful deployment, security review, or production SLO.

## 11. How would you present this project in a Forward Deployed Engineer interview?

Start with the user and operational problem described in [`README.md`](README.md). Explain one constraint that changes the implementation, show the linked code or example, and walk through a success case and a failure case. Agree on a measurable acceptance criterion before expanding the solution, and leave a handoff with data boundaries and rollback ownership. Any proposed production or business metric should be identified as a target until measured.

## 12. What is the input-to-output contract of `group_by`?

In [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104), `group_by(text, key, value, operation='sum')` receives the inputs. The function computes these intermediate values:

- `rows, columns, _ = read(text)`
- `groups = {}`
- `skipped = 0`
- `result = {}`

Its result is defined by:

- `{'key': key, 'value': value, 'operation': operation, 'groups': result, 'skipped': skipped}`

## 13. Which decision rules or boundary conditions should an interviewer challenge?

The implementation in [`src/csvtool/analyze.py`](src/csvtool/analyze.py#L104) branches on:

- `operation not in {'sum', 'mean', 'count', 'min', 'max'}`
- `column not in columns`
- `operation != 'count' and parsed is None`
- `operation == 'count'`
- `operation == 'sum'`
- `operation == 'mean'`
- `operation == 'min'`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

## 14. What does the operations plane add, and where is its limit?

[`src/csvtool/ops.py`](src/csvtool/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.
