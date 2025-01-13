from fastapi import FastAPI,HTTPException,Depends
from typing import List,Dict 
from pydantic import BaseModel
from middleware.verifyToken import get_access_token
from config import user_table, get_firebase_app
from firebase_admin import auth

ans_app=FastAPI()

#Strucutre for answers and questions
class QuestionAnswer(BaseModel):
    question: str
    answer: str

#Structure definition for answers with respect to questions and domain
class answerStruct(BaseModel):
    domain: str
    questions: List[str]
    answers: List[str]
    
# Route for posting answers
@ans_app.post("/post-answer")
async def post_answers(answerReq: answerStruct, idToken: str = Depends(get_access_token)):
    try:
        # Validate token and fetch user records
        decoded_token = auth.verify_id_token(idToken, app=get_firebase_app())
        email = decoded_token.get("email")

        response = user_table.get_item(Key={"uid": email})
        user = response.get("Item")

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Extract existing Q&A data
        existing_qna = user.get("qna", {})

        if answerReq.domain in existing_qna:
            raise HTTPException(
                status_code=400,
                detail=f"Answers for domain '{answerReq.domain}' have already been submitted."
            )

        # Convert Pydantic model to dictionary (array of question/answer pairs)
        answers_dict = [{"question": q, "answer": a} for q, a in zip(answerReq.questions, answerReq.answers)]

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

        return {"message": f"Answers for domain '{answerReq.domain}' submitted successfully.", "qna": existing_qna}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error posting answers: {str(e)}")
