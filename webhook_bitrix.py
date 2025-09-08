# webhook_bitrix.py
from fastapi import FastAPI, Request

from bitrix_api import post_comment

app = FastAPI()


@app.post("/bitrix-webhook/")
async def receive_webhook(request: Request):
    payload = await request.json()
    task_id = payload.get("data", {}).get("FIELDS_AFTER", {}).get("ID")
    if task_id:
        comment = "🔍 Проверка документации будет запущена автоматически."
        post_comment(task_id, comment)
    return {"status": "ok"}
