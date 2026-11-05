from fastapi import FastAPI

from incident_copilot.api.webhook import router as webhook_router

app = FastAPI(title="Incident Copilot")
app.include_router(webhook_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
