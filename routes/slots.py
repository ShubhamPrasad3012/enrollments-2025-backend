from fastapi import FastAPI,HTTPException,Depends
from typing import List,Dict 
from pydantic import BaseModel
from middleware.verifyToken import get_access_token
from config import user_table, get_firebase_app, interview_table
from firebase_admin import auth

slot_app=FastAPI()

#Route for getting slots from interview table
@app.get("/get-slots")
async def get_slots():
    try:
        #Fetching all slots from db
        response=interview_table.scan()
        slots=response.get('Items',[])

        if not slots:
            raise HTTPException(status_code=404,detail="No slots found")
    
        return{"message":"Slots have been fetched succ","slots":slots}

    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Error retrieving slots: {str(e)}")
    
#struct for slot
class Slot(BaseModel):
    iid:str
    time_slot:str

#Route for posting selected slots
@app.post("/post-slots")
async def post_slots(slot_req:Slot, idToken:str=Depends(get_access_token)):
    try:    

        #Validating token and fetching user records
        decoded_token = auth.verify_id_token(idToken, app=get_firebase_app())
        email = decoded_token.get('email')
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')

        if not user:
            raise HTTPException(status_code=404,detail="User not found")
        
        #Updating the table with the slots chosen
        user["slot"]=[{
                        "iid":slot_req.iid,
                        "time":slot_req.time_slot
                    }]
        
        result=user_table.put_item(Item=user)

        return{"message":"Answers submitted successfully","response":result}
    
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Error posting answers: {str(e)}")
    
