# CSV Data Analyzer

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
