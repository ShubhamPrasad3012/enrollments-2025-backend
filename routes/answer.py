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
    answers: List[QuestionAnswer]




#Route for posting answers
@ans_app.post("/post-answer")
async def post_answers(answerReq:answerStruct, idToken:str=Depends(get_access_token)):
    try:

        #Validating token and fetching user records
        decoded_token = auth.verify_id_token(idToken, app=get_firebase_app())
        email = decoded_token.get('email')
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')
        
  
        if not user:
            raise HTTPException(status_code=404,detail="User not found")
        
        #prepping the answer record
        existing_qna = user.get("qna", {})
        existing_qna[answerReq.domain] = {
            "answers": answerReq.answers
        }

        #Updating the table with the answers
        user_table.update_item(
            Key={"uid": email},
            UpdateExpression="SET #qna = :updated_qna",
            ExpressionAttributeNames={
                "#qna": "qna",
            },
            ExpressionAttributeValues={
                ":updated_qna": existing_qna,
            },
            ReturnValues="UPDATED_NEW",
        )
       
        return{"message":"Answers submitted successfully", "qna":existing_qna}
    
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Error posting answers: {str(e)}")

