from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.deps import load_config_raw, save_config_raw

router = APIRouter()


@router.get("/config", dependencies=[Depends(require_auth)])
def get_config():
    config = load_config_raw()
    return config


@router.put("/config", dependencies=[Depends(require_auth)])
def update_config(data: dict):
    save_config_raw(data)
    return {"message": "Config updated", "config": data}
