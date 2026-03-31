from __future__ import annotations

from fastapi import APIRouter

from api.deps import load_config_raw, save_config_raw

router = APIRouter()


@router.get("/config")
def get_config():
    config = load_config_raw()
    return config


@router.put("/config")
def update_config(data: dict):
    save_config_raw(data)
    return {"message": "Config updated", "config": data}
