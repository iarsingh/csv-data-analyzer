import csv
import io
import math
import re
from collections import Counter

MAX_ROWS = 100_000
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BOOLEANS = {"true", "false", "yes", "no"}


class CsvError(ValueError):
    pass


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


def number(raw):
    try:
        return float(raw)
    except ValueError:
        return None


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


def median(sorted_values):
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2


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
    return column


def analyze(text):
    rows, columns, delimiter = read(text)
    profiles = {column: profile([str(row[column] or "").strip() for row in rows]) for column in columns}
    return {
        "rows": len(rows),
        "columns": columns,
        "delimiter": delimiter,
        "profiles": profiles,
        "nulls": {column: profiles[column]["nulls"] for column in columns},
        "means": {column: profiles[column]["mean"] for column in columns if "mean" in profiles[column]},
    }


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
        elif operation == "mean":
            result[name] = round(sum(values) / len(values), 4)
        elif operation == "min":
            result[name] = min(values)
        else:
            result[name] = max(values)
    return {"key": key, "value": value, "operation": operation, "groups": result, "skipped": skipped}
