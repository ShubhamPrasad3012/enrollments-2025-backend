from fastapi import Request, HTTPException, Header, Depends
from typing import Optional

def get_access_token(request: Request, authorization: Optional[str] = Header(None)) -> Optional[str]:

    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    
    token_prefix = "Bearer "
    if not authorization.startswith(token_prefix):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    return authorization[len(token_prefix):]
