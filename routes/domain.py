from fastapi import FastAPI, HTTPException, Header, Depends
from firebase_admin import auth
from config import user_table, quiz_table, get_firebase_app
from typing import List, Dict
from middleware.verifyToken import get_access_token

domain_app = FastAPI()

@domain_app.post('/submit')
async def post_domain(domain: Dict[str, List[int]], id_token: str = Depends(get_access_token)):
    try:
        decoded_token = auth.verify_id_token(id_token, app=get_firebase_app())
        email = decoded_token.get('email')
        
        response = user_table.get_item(Key={'uid': email})
        user = response.get('Item')
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not domain:
            raise HTTPException(status_code=400, detail="Domain list cannot be empty")
        
        for key, domain_list in domain.items():
            if len(domain_list) > 2:
                raise HTTPException(status_code=400, detail=f"Domain array for key {key} cannot have more than 2 entries")

        print(domain)
        
        user['domain'] = domain
        result = user_table.put_item(Item=user)
        
        return {"message": "Domain added successfully", "selected": domain}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
  
@domain_app.get('/quiz')
async def get_qs(domain: str):
    try:
        response = quiz_table.get_item(Key={'qid': domain})
        field = response.get('Item')

        if not field:
            raise HTTPException(status_code=404, detail="Item not found")
        
        qs = field.get('qs')
        if not qs:
            raise HTTPException(status_code=404, detail="Questions not found")
        
        return {"questions": qs}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
