from fastapi.testclient import TestClient

from csvtool.main import app

client = TestClient(app)

SALES = "region,revenue,active,closed_on\nnorth,10,yes,2026-10-01\nsouth,,no,2026-10-03\nnorth,30,yes,2026-10-02\nwest,20,yes,\n"


def analyze(text):
    return client.post("/analyze", json={"csv": text})


def test_means_and_nulls():
    payload = analyze("region,revenue\nnorth,10\nsouth,\nnorth,30\n").json()
    assert payload["rows"] == 3
    assert payload["nulls"]["revenue"] == 1
    assert payload["means"]["revenue"] == 20


def test_types_are_inferred_per_column():
    profiles = analyze(SALES).json()["profiles"]
    assert profiles["region"]["type"] == "text"
    assert profiles["revenue"]["type"] == "integer"
    assert profiles["active"]["type"] == "boolean"
    assert profiles["closed_on"]["type"] == "date"


def test_numeric_profile_has_median_and_stddev():
    revenue = analyze(SALES).json()["profiles"]["revenue"]
    assert revenue["min"] == 10
    assert revenue["max"] == 30
    assert revenue["median"] == 20
    assert revenue["stddev"] == 8.165


def test_even_count_median_is_the_midpoint():
    revenue = analyze("revenue\n1\n2\n3\n4\n").json()["profiles"]["revenue"]
    assert revenue["median"] == 2.5


def test_text_profile_has_top_values():
    top = analyze(SALES).json()["profiles"]["region"]["top"]
    assert top[0] == {"value": "north", "count": 2}


def test_semicolon_delimiter_is_detected():
    payload = analyze("region;revenue\nnorth;10\nsouth;20\n").json()
    assert payload["delimiter"] == ";"
    assert payload["means"]["revenue"] == 15


def test_group_by_sums_and_skips_blanks():
    body = client.post("/group", json={"csv": SALES, "key": "region", "value": "revenue"}).json()
    assert body["groups"] == {"north": 40.0, "west": 20.0}
    assert body["skipped"] == 1


def test_group_by_count_keeps_blank_rows():
    body = client.post("/group", json={"csv": SALES, "key": "region", "value": "revenue", "operation": "count"}).json()
    assert body["groups"] == {"north": 2, "south": 1, "west": 1}


def test_unknown_column_and_operation_are_refused():
    assert client.post("/group", json={"csv": SALES, "key": "city", "value": "revenue"}).status_code == 422
    assert client.post("/group", json={"csv": SALES, "key": "region", "value": "revenue", "operation": "median"}).status_code == 422


def test_empty_and_duplicate_headers_are_refused():
    assert analyze("   ").status_code == 422
    assert analyze("a,a\n1,2\n").status_code == 422
