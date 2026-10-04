from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from csvtool.analyze import CsvError, analyze, group_by

app = FastAPI()


class CsvBody(BaseModel):
    csv: str


class GroupBody(BaseModel):
    csv: str
    key: str
    value: str
    operation: str = "sum"


def guarded(action):
    try:
        return action()
    except CsvError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/analyze")
def post_analyze(body: CsvBody):
    return guarded(lambda: analyze(body.csv))


@app.post("/group")
def post_group(body: GroupBody):
    return guarded(lambda: group_by(body.csv, body.key, body.value, body.operation))
