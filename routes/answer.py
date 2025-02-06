from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field
from middleware.verifyToken import get_access_token
from firebase_admin import auth
from config import initialize
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError

ans_app = FastAPI()

resources = initialize()
user_table = resources['user_table']
firebase_app = resources['firebase_app']  


class AnswerStruct(BaseModel):
    domain: str = Field(...)
    questions: List[str] = Field(...)
    answers: List[str] = Field(...)
    score: Optional[int] = Field(None)
    round: int

domain_mapping = {
    "UI/UX": "ui",
    "Graphic Design": "graphic",
    "Video Editing": "video",
    'Events':'events', 
    'PnM':'pnm',
    'WEB':'web', 
    'IOT':'iot', 
    'APP':'app',
    'AI/ML':'ai',
    'RND':'rnd'
}

@ans_app.post("/submit")
async def post_answers(answerReq: AnswerStruct, idToken: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(idToken, app=resources["firebase_app"])
        email = decoded_token.get("email")

        if not email:
            return JSONResponse(status_code=401, content="Invalid or missing email in token.")

        response = user_table.get_item(Key={"uid": email})
        user = response.get("Item")

        if not user:
            return JSONResponse(status_code=404, content="User not found.")

        if answerReq.domain not in user.get('domains', []):
            return JSONResponse(status_code=408, content="Domain was not selected")
        mapped_domain = domain_mapping.get(answerReq.domain)
        domain_tables = resources['domain_tables']
        domain_table = domain_tables.get(mapped_domain)

        if not domain_table:
            raise HTTPException(status_code=400, detail=f"Domain '{answerReq.domain}' not recognized.")

        if len(answerReq.questions) != len(answerReq.answers):
            raise HTTPException(status_code=400, detail="Questions and answers lists must have the same length.")

        answers_dict = [{"question": q, "answer": a} for q, a in zip(answerReq.questions, answerReq.answers)]
        response = domain_table.get_item(Key={'email': email})



        if answerReq.round == 1:
            if 'Item' in response:
                return JSONResponse(status_code=409, content="Answers already submitted")
            
            domain_table.put_item(
                Item={
                    "email": email,
                    f"round{answerReq.round}": answers_dict,
                    f"score{answerReq.round}": answerReq.score
                }
            )
        else:
            result = domain_table.get_item(Key={"email": email})
            domain_response = result.get('Item')
            if not domain_response or not domain_response.get(f"round{answerReq.round - 1}"):
                raise HTTPException(
                    status_code=400,
                    detail=f"User '{email}' has not completed round {answerReq.round - 1} in domain '{answerReq.domain}'."
                )
            domain_table.update_item(Key={"email": email},
                UpdateExpression="""
                SET #new_answers = if_not_exists(#new_answers, :new_answers),
                #new_score = if_not_exists(#new_score, :new_score)
                """,
            ExpressionAttributeNames={
                "#new_answers": f"round{answerReq.round}",
                "#new_score": f"score{answerReq.round}"
            },
            ExpressionAttributeValues={
                ":new_answers": answers_dict,
                ":new_score": answerReq.score
            },
            ReturnValues="UPDATED_NEW"
            )

        user_table.update_item(
                Key={'uid': email},
                UpdateExpression=f"SET round{answerReq.round} = list_append(if_not_exists(round{answerReq.round}, :empty_list), :new_value)",
                ExpressionAttributeValues={
                ':new_value': [answerReq.domain], 
                ':empty_list': []           
                },
            )
        return {"message": f"Answers for domain '{answerReq.domain}' submitted successfully for round {answerReq.round}."}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error posting answers: {str(e)}")
