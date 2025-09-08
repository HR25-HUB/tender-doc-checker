import os

import requests

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")


def post_comment(task_id: str, message: str):
    url = f"{BITRIX_WEBHOOK_URL}/task.comment.add"
    data = {"taskId": task_id, "fields": {"POST_MESSAGE": message}}
    r = requests.post(url, json=data)
    return r.status_code == 200


def create_bitrix_task(title: str, description: str) -> int:
    url = f"{BITRIX_WEBHOOK_URL}/task.item.add.json"
    payload = {
        "fields": {
            "TITLE": title,
            "DESCRIPTION": description,
            "RESPONSIBLE_ID": 1,
            "CREATED_BY": 1,
        }
    }
    response = requests.post(url, json=payload)
    try:
        return response.json()["result"]
    except Exception:
        return -1
