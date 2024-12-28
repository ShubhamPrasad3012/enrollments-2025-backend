from fastapi import FastAPI, HTTPException
from firebase_admin import auth, initialize_app
import boto3
from config import user_table, get_firebase_app

firebase = get_firebase_app()
auth = auth
dynamodb = boto3.resource('dynamodb')

user = FastAPI()

@user.post("/login")
async def create_access_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token.get('email')

        if not email:
            raise HTTPException(status_code=400, detail="Email not found in ID token")

        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, detail="User not found in DynamoDB")

        if 'username' not in user:
            raise HTTPException(status_code=401, detail="Username not found for this user")

        return {"message": "User authenticated successfully", "user": user}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@user.post("/username")
async def submit_username(id_token: str, username: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token.get('email')

        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, detail="User not found in DynamoDB")

        if 'username' in user:
            raise HTTPException(status_code=409, detail="Username already exists for this user")

        scan_response = user_table.scan(
            FilterExpression="username = :username",
            ExpressionAttributeValues={":username": username}
        )

        if scan_response['Items']:
            raise HTTPException(status_code=409, detail="Username already taken")

        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")

        user['username'] = username
        result = user_table.put_item(Item=user)
        return {"message": "Username added successfully", "response": result}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
