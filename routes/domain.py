from fastapi import FastAPI, HTTPException, Depends, Response
from firebase_admin import auth
from typing import List, Dict
from middleware.verifyToken import get_access_token
from config import initialize
from fastapi.responses import JSONResponse
from cryptography.fernet import Fernet
import base64
import os
import random

domain_app = FastAPI()

resources = initialize()
user_table = resources['user_table']
quiz_table = resources['quiz_table']

@domain_app.post('/submit')
async def post_domain(domain: Dict[str, List[str]], id_token: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(id_token, app=resources['firebase_app'])
        email = decoded_token.get('email')

        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, content="User not found")

        if not domain:
            raise HTTPException(status_code=400, content="Domain list cannot be empty")

        for key, domain_list in domain.items():
            limit = 3 if "CC" in domain_list else 2
            if len(domain_list) > limit:
                raise HTTPException(status_code=400, detail=f"Domain array for key {key} cannot have more than {limit} entries")

        user['domain'] = domain
        user_table.put_item(Item=user)

        return JSONResponse(status_code=200, content=domain)

    except Exception as e:
        raise HTTPException(status_code=400, content=f"Error: {str(e)}")


@domain_app.get('/questions')
async def get_qs(domain: str, round: str, id_token: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(id_token, app=resources['firebase_app'])
        email = decoded_token.get('email')
        response = quiz_table.get_item(Key={'qid': domain})
        field = response.get('Item')

        if not field:
            return JSONResponse(status_code=404, content="Invalid domain")

        round_data = field.get(round)
        if not round_data:
            return JSONResponse(status_code=401, content=f"Round {round} Questions not found")

        encryption_key = os.environ.get('MY_ENCRYPTION_KEY')
        encryption_key = encryption_key.encode()
        cipher_suite = Fernet(encryption_key)
        sampled_questions = random.sample(round_data, min(10, len(round_data)))

        formatted_questions = []
        for q in sampled_questions:
            question_data = {
                "question": q["question"]
            }
            
            if "options" in q:
                question_data["options"] = q["options"]
                
            if "correctIndex" in q:
                correct_index_str = str(q["correctIndex"])
                encrypted_index = cipher_suite.encrypt(correct_index_str.encode())
                question_data["correctIndex"] = base64.b64encode(encrypted_index).decode('utf-8')
                
            if "image_url" in q:
                question_data["image_url"] = str(q["image_url"])
                
            formatted_questions.append(question_data)

        return JSONResponse(content={"questions": formatted_questions})

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")