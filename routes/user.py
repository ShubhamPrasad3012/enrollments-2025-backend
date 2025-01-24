from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from firebase_admin import auth
from pydantic import BaseModel
from middleware.verifyToken import get_access_token
from config import get_resources

user = FastAPI()

class LoginRequest(BaseModel):
    idToken: str

class UsernameRequest(BaseModel):
    username: str

@user.post("/login")
async def login(authorization: str = Depends(get_access_token), resources: dict = Depends(get_resources)):
    try:
        if not authorization:
            raise HTTPException(status_code=400, detail="Authorization token missing")

        try:
            decoded_token = auth.verify_id_token(authorization)
        except Exception as token_error:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(token_error)}")

        email = decoded_token.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in ID token")

        try:
            user_table = resources.get("user_table")
            response = user_table.get_item(Key={'uid': email})
            user = response.get('Item')

        except Exception as db_error:
            raise HTTPException(status_code=500, detail=f"Database lookup failed: {str(db_error)}")

        if user is None:
            return JSONResponse(status_code=404, content="User not registered on VTOP")

        if 'username' not in user:
            return JSONResponse(status_code=201, content="Logged In Successfully")
        else:
            return JSONResponse(status_code=200, content="Logged In Successfully")

    except HTTPException:
        raise
    except Exception as unexpected_error:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(unexpected_error)}")

@user.get("/profile")
async def get_profile(authorization: str = Depends(get_access_token), resources: dict = Depends(get_resources)):
    try:
        decoded_token = auth.verify_id_token(authorization)
        email = decoded_token.get('email')
        response = resources['user_table'].get_item(Key={'uid': email})
        user = response.get('Item')
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "email": email, 
            "username": user.get("username"), 
            "mobile": user.get("mobile"), 
            "name": user.get("name"), 
            "domain": user.get("domain")
        }

    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")

@user.post("/username")
async def submit_username(
    username_request: UsernameRequest,
    authorization: str = Depends(get_access_token), resources: dict = Depends(get_resources)
):
    try:
        username = username_request.username.strip()
        if not username:
            return JSONResponse(status_code=400, content={"detail": "Username cannot be empty"})

        decoded_token = auth.verify_id_token(authorization)
        email = decoded_token.get('email')

        user_table = resources['user_table']
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, content="User not registered on VTOP")

        if user.get('username'):
            return JSONResponse(status_code=409, content= "Username already exists for this user")

        gsi_response = user_table.query(
            IndexName="username-index",
            KeyConditionExpression="username = :username",
            ExpressionAttributeValues={":username": username}
        )
        if gsi_response.get('Items'):
            return JSONResponse(status_code=201, content= "Username already taken")

        user['username'] = username
        user_table.put_item(Item=user)

        return JSONResponse(status_code=200, content= "Username added successfully")

    except HTTPException as e:
        raise e
    except Exception as e:
        return JSONResponse(status_code=500, content= f"Internal Server Error: {str(e)}")
