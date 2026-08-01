from fastapi import FastAPI

app = FastAPI(title="TurbineTwin API")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
