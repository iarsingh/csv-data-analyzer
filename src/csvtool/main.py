from fastapi import FastAPI
from csvtool.analyze import analyze

app = FastAPI()

@app.post("/analyze")
def post_analyze(body: dict):
    return analyze(body["csv"])
