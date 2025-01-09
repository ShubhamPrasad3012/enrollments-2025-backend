from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional

def get_access_token(authorization: Optional[str] = Header(None)) -> str:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    token_prefix = "Bearer "
    if not authorization.startswith(token_prefix):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    return authorization[len(token_prefix):] 
