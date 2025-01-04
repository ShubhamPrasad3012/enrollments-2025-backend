from fastapi import FastAPI,HTTPException,Depends
from typing import List,Dict 
from pydantic import BaseModel
from middleware.verifyToken import get_access_token
from config import user_table, get_firebase_app
from firebase_admin import auth

ans_app=FastAPI()

#Structure definition for answers with respect to questions
class answerStruct(BaseModel):
    answers: List[Dict[str,str]]

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
        
        #Updating the table with the answes 
        user['qna']= answerReq.answers
        result=user_table.put_item(Item=user)
       
        return{"message":"Answers submitted successfully","response":result}
    
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Error posting answers: {str(e)}")

