from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from firebase_admin import auth
from middleware.verifyToken import get_access_token
from config import initialize

quiz_app = FastAPI()
resources = initialize()
user_table = resources['user_table']

# Struct for quiz progress
class QuizProgress(BaseModel):
    completed_quizzes: List[str]
    pending_quizzes: List[str]

# Route for getting quiz progress
@quiz_app.get("/get-progress")
async def get_progress(idToken: str = Depends(get_access_token)):
    try:
        # Decoding the token and fetching user email
        decoded_token = auth.verify_id_token(idToken)
        email = decoded_token.get('email')
        
        # Fetch user from the database using email
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get the user's domains
        domains = user.get('domain', [])  # Assuming 'domain' contains a list of domains selected by the user
        completed_quizzes = []
        pending_quizzes = []

        for domain in domains:
            qna = user.get('qna', {}).get(domain, [])
            if qna:
                completed_quizzes.append(domain)
            else:
                pending_quizzes.append(domain)

        return {
            "message": "Progress fetched successfully",
            "completed_quizzes": completed_quizzes,
            "pending_quizzes": pending_quizzes
        }

    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching progress: {str(e)}")
