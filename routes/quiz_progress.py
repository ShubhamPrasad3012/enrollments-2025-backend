from fastapi import FastAPI, HTTPException, Depends
from typing import Dict, List
from pydantic import BaseModel
from middleware.verifyToken import get_access_token
from config import user_table
from firebase_admin import auth

quiz_app=FastAPI()

#Struct for quiz progress
class QuizProgress(BaseModel):
    completed_quizzes: List[str]
    pending_quizzes: List[str]


#Route for getting quiz progress
@quiz_app.get("/get-progress")
async def get_progress(idToken:str=Depends(get_access_token)):
    try:
        #Validating token and fetching user
        decoded_token=auth.verify_id_token(idToken, app=get_firebase_app())
        email=decoded_token.get('email')
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404,detail="User not found")
        
        #get the users domains
        domains = user.get('domain', [])  # Assuming 'domains' contains a list of domains selected by the user
        completed_quizzes = []
        pending_quizzes = []

        #checking in each qna record if that domain is present
        for domain in domains:
            qna=user.get('qna',{}).get(domain,[])
            if qna:
                completed_quizzes.append(domain)
            else:
                pending_quizzes.append(domain)

        return{
            "message":"Progress fetched succ",
            "completed_quizzes":completed_quizzes,
            "pending_quizzes":pending_quizzes
        }
    
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Error fetching progress: {str(e)}")
    