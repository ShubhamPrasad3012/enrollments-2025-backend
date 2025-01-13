from fastapi import FastAPI, HTTPException, Depends
from firebase_admin import auth
from pydantic import BaseModel
from config import user_table
from middleware.verifyToken import get_access_token

user = FastAPI()

class LoginRequest(BaseModel):
    idToken: str

class UsernameRequest(BaseModel):
    username: str

@user.post("/login")
async def login(authorization: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(authorization)
        email = decoded_token.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in ID token")

        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')
        if user is not None:
            username = user.get("username")
            if username not in [None, ""]:
                return {"status": "success", "message": "Username exists", "email": email, "username": username}
            else:
                return {"status": "success", "message": "Username does not exist", "email": email}
        else:
            raise HTTPException(status_code=401, detail="User not registered on VTOP")

    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@user.get("/profile")
async def login(authorization: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(authorization)
        email = decoded_token.get('email')
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')
        return {"email": email, "username": user.get("username"), "mobile": user.get("mobile"), "name": user.get("name"), "domain": user.get("domain") }
        
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")

@user.post("/username")
async def submit_username(
    username_request: UsernameRequest,
    id_token: str = Depends(get_access_token)
    ):
    try:
        username = username_request.username
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")

        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Invalid ID token: missing email")

        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, detail="User not found in DynamoDB")

        if user.get('username') not in [None, ""]:
            raise HTTPException(status_code=409, detail="Username already exists for this user")

        scan_response = user_table.scan(
            FilterExpression="username = :username",
            ExpressionAttributeValues={":username": username}
        )
        if scan_response['Items']:
            raise HTTPException(status_code=409, detail="Username already taken")

        user['username'] = username
        user_table.put_item(Item=user)

        return {"message": "Username added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
