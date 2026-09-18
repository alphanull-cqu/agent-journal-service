from fastapi import FastAPI


app = FastAPI(
    title="Agent Journal GitHub App Service",
    version="0.1.0",
)


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}