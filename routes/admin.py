from fastapi import FastAPI, Depends, Body
from middleware.verifyToken import get_access_token
from config import initialize
from fastapi.responses import JSONResponse
from firebase_admin import auth
from typing import Optional
from pydantic import BaseModel

admin_app = FastAPI()

resources = initialize()
#user_table = resources['user_table']
admin_table = resources['admin_table']

DOMAIN_MAPPING = {
    "UI/UX": "ui",
    "GRAPHIC DESIGN": "graphic",
    "VIDEO EDITING": "video",
    'EVENTS': 'events',
    'PNM': 'pnm',
    'WEB': 'web',
    'IOT': 'iot',
    'APP': 'app',
    'AI/ML': 'ai',
    'RND': 'rnd'
}

async def verify_admin(id_token: str, required_domains: str):
    try:
        decoded_token = auth.verify_id_token(id_token, app=resources['firebase_app'])
        email = decoded_token.get('email')
        if not email:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication failed: No email in token"}
            )
        
        admin_response = admin_table.get_item(Key={'email': email})
        admin = admin_response.get('Item')
        
        if not admin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: Not an admin"}
            )
            
        if required_domains:
            allowed_domains = admin.get('allowed_domains', [])
            if not any(domain in allowed_domains for domain in required_domains):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied: No permission for this domain"}
                )
                
        return admin
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"detail": f"Authentication failed: {str(e)}"}
        )

@admin_app.get('/fetch')
async def fetch_domains(
    domain: str,
    round: int,
    limit: int = 10,
    last_evaluated_key: Optional[str] = None,
    id_token: str = Depends(get_access_token)
):

    try:
        admin_result = await verify_admin(id_token, [domain])
        if isinstance(admin_result, JSONResponse):
            return admin_result
        
        
        if round < 1:
            return JSONResponse(
                status_code=400,
                content={"detail": "Round number must be greater than 0"}
            )
        
        mapped_domain = DOMAIN_MAPPING.get(domain)
        if not mapped_domain:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid domain specified"}
            )
        
        domain_table = resources['domain_tables'].get(mapped_domain)
        if not domain_table:
            return JSONResponse(
                status_code=500,
                content={"detail": "Domain table not configured"}
            )
        
        scan_params = {'Limit': limit}
            
        if round > 1:
            qualification_attr = f'qualification_status{round-1}'
            scan_params['FilterExpression'] = f'#{qualification_attr} = :qualified'
            scan_params['ExpressionAttributeNames'] = {
                f'#{qualification_attr}': qualification_attr
            }
            scan_params['ExpressionAttributeValues'] = {
                ':qualified': True
            }
        
        if last_evaluated_key:
            try:
                scan_params['ExclusiveStartKey'] = {
                    'email': last_evaluated_key
                }
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Invalid last_evaluated_key format: {str(e)}"}
                )

        response = domain_table.scan(**scan_params)
        items = response.get('Items', [])
        
        last_key = None
        if response.get('LastEvaluatedKey'):
            last_key = response['LastEvaluatedKey'].get('uid')
        
        results = {
            mapped_domain: {
                'items': items,
                'last_evaluated_key': last_key
            }
        }
        
        return {
            "status_code":200,
            "content":results
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Error processing request: {str(e)}"}
        )

from pydantic import BaseModel
from fastapi import Body

class AddRequest(BaseModel):
    domain: str
    round: str
    question_data: dict = Body(...)
    id_token: str = Depends(get_access_token)

@admin_app.post('/questions')
async def add_question(request: AddRequest):

    try:
        admin_result = await verify_admin(request.id_token, request.domain)
        if isinstance(admin_result, JSONResponse):
            return admin_result
        
        quiz_table = resources['quiz_table']

        response = quiz_table.get_item(Key={'qid': request.domain})
        field = response.get('Item')

        if not field:
            field = {
                'qid': request.domain,
                request.round: [request.question_data]
            }
        else:
            if request.round not in field:
                field[request.round] = []
            
            if field[request.round] is None:
                field[request.round] = []
            
            if not isinstance(field[request.round], list):
                field[request.round] = []
            
            field[request.round].append(request.question_data)

        quiz_table.put_item(Item=field)

        return JSONResponse(
            status_code=200, 
            content={
                "detail": "Question added successfully",
                "total_questions": len(field[request.round])
            }
        )
    
    except Exception as e:
        print(f"Error details: {str(e)}") 
        return JSONResponse(
            status_code=400, 
            content={"detail": f"Error processing request: {str(e)}"}
        )
    
class QualificationRequest(BaseModel):
    user_email: str
    domain: str
    status: bool
    round: int
    id_token: str = Depends(get_access_token)

@admin_app.post('/qualify')
async def mark_qualification(request: QualificationRequest):

    try:
        admin_result = await verify_admin(request.id_token, request.domain)
        if isinstance(admin_result, JSONResponse):
            return admin_result
        
        mapped_domain = DOMAIN_MAPPING.get(request.domain)
        if not mapped_domain:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid domain specified"}
            )
            
        domain_table = resources['domain_tables'].get(mapped_domain)
        if not domain_table:
            return JSONResponse(
                status_code=500,
                content={"detail": "Domain table not configured"}
            )
            
        user_response = domain_table.get_item(Key={'email': request.user_email})
        user = user_response.get('Item')
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"detail": "User not found"}
            )
            
        if request.round > 1:
            prev_status = user.get(f'qualification_status{request.round-1}')
            if not prev_status:
                return JSONResponse(
                    status_code=409,
                    content={"detail": f"User {request.user_email} did not qualify in round {request.round-1}"}
                )
        
        user[f'qualification_status{request.round}'] = request.status
        domain_table.put_item(Item=user)
        
        qualification = "qualified" if request.status else "disqualified"
        return JSONResponse(
            status_code=200,
            content={"detail": f"User {request.user_email} {qualification} for round {request.round}"}
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Error processing request: {str(e)}"}
        )