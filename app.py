from fastapi import FastAPI, Request
from fastapi.responses import Response

from channels.telegram import router as telegram_router, webhook_router as telegram_webhook_router
from channels.wati import router as wati_router
from channels.twilio import router as twilio_router, process_twilio_update


app = FastAPI(title="Tailorsin Backend")
app.include_router(telegram_router)
app.include_router(telegram_webhook_router)
app.include_router(wati_router)
app.include_router(twilio_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


# Catch-all route for Twilio webhooks (backward compatibility)
@app.post("/webhook")
async def twilio_webhook_root(request: Request) -> Response:
    """Handle Twilio webhooks sent to /webhook (backward compatibility)."""
    form_data = await request.form()
    form_dict = dict(form_data)
    twiml_response = await process_twilio_update(form_dict)
    return Response(content=twiml_response, media_type="text/xml")
