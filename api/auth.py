import os
from typing import Optional

from fastapi import HTTPException, Query, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(
    header_key: Optional[str] = Security(_api_key_header),
    query_key: Optional[str] = Query(None, alias="api_key"),
) -> str:
    expected = os.getenv("NAVY_API_KEY", "")
    if not expected:
        return ""
    provided = header_key or query_key
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return provided
