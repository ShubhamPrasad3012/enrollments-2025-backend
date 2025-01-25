from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
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
    score: Optional[int] = Field(None, title="Score for the domain, not compulsory")
    round: int

@ans_app.post("/submit")
async def post_answers(answerReq: AnswerStruct, idToken: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(idToken, app=resources["firebase_app"])
        email = decoded_token.get("email")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid or missing email in token.")

        response = user_table.get_item(Key={"uid": email})
        user = response.get("Item")

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if len(answerReq.questions) != len(answerReq.answers):
            raise HTTPException(
                status_code=400,
                detail="Questions and answers lists must have the same length."
            )

        existing_round = user.get(f"round {answerReq.round}", {})

        if answerReq.domain in existing_round:
            raise HTTPException(
                status_code=400,
                detail=f"Answers for domain '{answerReq.domain}' have already been submitted for round {answerReq.round}."
            )

        answers_dict = [
            {"question": q, "answer": a}
            for q, a in zip(answerReq.questions, answerReq.answers)
        ]

        domain_data = {"answers": answers_dict}
        if answerReq.score is not None:
            domain_data["score"] = answerReq.score

        existing_round[answerReq.domain] = domain_data

        user_table.update_item(
            Key={"uid": email},
            UpdateExpression="SET #round = :updated_round",
            ExpressionAttributeNames={"#round": f"round {answerReq.round}"},
            ExpressionAttributeValues={":updated_round": existing_round},
            ReturnValues="UPDATED_NEW",
        )

        return {"message": f"Answers for domain '{answerReq.domain}' submitted successfully for round {answerReq.round}."}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error posting answers: {str(e)}")