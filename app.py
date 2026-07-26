from fastapi import FastAPI

from channels.telegram import router as telegram_router, webhook_router as telegram_webhook_router
from channels.wati import router as wati_router
from channels.twilio import router as twilio_router


app = FastAPI(title="Tailorsin Backend")
app.include_router(telegram_router)
app.include_router(telegram_webhook_router)
app.include_router(wati_router)
app.include_router(twilio_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
