import csv
import io

def analyze(text):
    rows = list(csv.DictReader(io.StringIO(text.strip())))
    columns = list(rows[0]) if rows else []
    nulls = {column: sum(1 for row in rows if not str(row[column]).strip()) for column in columns}
    means = {}
    for column in columns:
        values = []
        numeric = True
        for row in rows:
            raw = str(row[column]).strip()
            if not raw:
                continue
            try:
                values.append(float(raw))
            except ValueError:
                numeric = False
                break
        if numeric and values:
            means[column] = round(sum(values) / len(values), 4)
    return {"rows": len(rows), "columns": columns, "nulls": nulls, "means": means}
