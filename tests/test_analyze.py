from fastapi.testclient import TestClient
from csvtool.main import app

def test_means_and_nulls():
    csv = "region,revenue\nnorth,10\nsouth,\nnorth,30\n"
    payload = TestClient(app).post("/analyze", json={"csv": csv}).json()
    assert payload["rows"] == 3
    assert payload["nulls"]["revenue"] == 1
    assert payload["means"]["revenue"] == 20
