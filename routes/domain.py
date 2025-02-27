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

        mcq_data = field.get(f"mcq{round}", [])
        desc_data = field.get(f"desc{round}", [])

        if not mcq_data:
            return JSONResponse(status_code=204, content=f"Round {round} MCQ Questions not found")

        secret_key = os.environ.get('MY_SECRET_KEY')
        if not secret_key:
            raise HTTPException(status_code=500, detail="Secret key not found in environment variables")

        selected_mcq = random.sample(mcq_data, min(7, len(mcq_data)))

        selected_desc = desc_data[:3] if len(desc_data) >= 3 else desc_data
        remaining_mcq_needed = 3 - len(selected_desc)

        if remaining_mcq_needed > 0:
            extra_mcqs = [q for q in mcq_data if q not in selected_mcq]
            selected_mcq += random.sample(extra_mcqs, min(remaining_mcq_needed, len(extra_mcqs)))

        formatted_questions = []
        for q in selected_mcq + selected_desc:
            question_data = {"question": q["question"]}

            if "options" in q:
                question_data["options"] = q["options"]

            if "correctIndex" in q:
                correct_index_str = str(q["correctIndex"])
                import hashlib
                question_salt = hashlib.md5(q["question"].encode()).hexdigest()[:10]
                data_to_hash = f"{secret_key}{correct_index_str}{question_salt}"
                hashed_index = hashlib.sha256(data_to_hash.encode()).hexdigest()
                question_data["correctIndexHash"] = hashed_index
                question_data["salt"] = question_salt

            if "image_url" in q:
                question_data["image_url"] = str(q["image_url"])

            formatted_questions.append(question_data)

        return JSONResponse(content={"questions": formatted_questions})

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
