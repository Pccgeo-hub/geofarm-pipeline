from __future__ import annotations
from fastapi import HTTPException
from typing import Any

def ok(data: Any) -> dict:
    return {"status": "ok", "data": data}

def fail(msg: str, code: int = 400):
    raise HTTPException(status_code=code, detail=msg)