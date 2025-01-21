from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel, Field
from middleware.verifyToken import get_access_token
from firebase_admin import auth
from config import initialize
from botocore.exceptions import ClientError

ans_app = FastAPI()

resources = initialize()
user_table = resources['user_table']
firebase_app = resources['firebase_app']  

class AnswerStruct(BaseModel):
    domain: str = Field(..., title="Domain for the answers")
    questions: List[str] = Field(..., title="List of questions")
    answers: List[str] = Field(..., title="List of answers")

@ans_app.post("/post-answer")
async def post_answers(answerReq: AnswerStruct, idToken: str = Depends(get_access_token)):
    try:
        # Validate token and fetch user records
        decoded_token = auth.verify_id_token(idToken, app=resources["firebase_app"])
        email = decoded_token.get("email")
        print(answerReq)

        if not email:
            raise HTTPException(status_code=401, detail="Invalid or missing email in token.")

        response = user_table.get_item(Key={"uid": email})
        user = response.get("Item")

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Validate input lengths
        if len(answerReq.questions) != len(answerReq.answers):
            raise HTTPException(
                status_code=400,
                detail="Questions and answers lists must have the same length."
            )

        # Check for existing domain
        existing_qna = user.get("qna", {})
        if answerReq.domain in existing_qna:
            raise HTTPException(
                status_code=400,
                detail=f"Answers for domain '{answerReq.domain}' have already been submitted."
            )

        # Convert Pydantic model to dictionary (array of question/answer pairs)
        answers_dict = [
            {"question": q, "answer": a} for q, a in zip(answerReq.questions, answerReq.answers)
        ]

        # Add answers for the new domain
        existing_qna[answerReq.domain] = {"answers": answers_dict}

        # Update the table with the new answers
        user_table.update_item(
            Key={"uid": email},
            UpdateExpression="SET #qna = :updated_qna",
            ExpressionAttributeNames={"#qna": "qna"},
            ExpressionAttributeValues={":updated_qna": existing_qna},
            ReturnValues="UPDATED_NEW",
        )

        return {"message": f"Answers for domain '{answerReq.domain}' submitted successfully."}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error posting answers: {str(e)}")