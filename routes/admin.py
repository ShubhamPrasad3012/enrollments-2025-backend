from fastapi import FastAPI, Depends, Body
from middleware.verifyToken import get_access_token
from config import initialize
from fastapi.responses import JSONResponse
from firebase_admin import auth
from typing import Optional
from pydantic import BaseModel

admin_app = FastAPI()

resources = initialize()
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

async def verify_admin(authorization: str, required_domain: str):
    try:
        decoded_token = auth.verify_id_token(authorization, app=resources['firebase_app'])
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
            
        if required_domain:
            allowed_domains = admin.get('allowed_domains', [])
            print(allowed_domains)
            if required_domain not in allowed_domains:
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

class FetchRequest(BaseModel):
    domain: str
    round: int
    status: str
    limit: int = 3
    last_evaluated_key: Optional[str] = None

@admin_app.get('/fetch')
async def fetch_domains(request: FetchRequest, authorization: str = Depends(get_access_token)):
    try:

        admin_result = await verify_admin(authorization, request.domain)
        if isinstance(admin_result, JSONResponse):
            return admin_result
        if request.round < 1:
            return JSONResponse(
                status_code=400,
                content={"detail": "Round number must be greater than 0"}
            )

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

        qualification_attr = f'qualification_status{request.round}'
        filter_expression = None
        expression_values = {}

        if request.status.lower() == "unmarked":
            filter_expression = f"attribute_not_exists(#{qualification_attr}) OR #{qualification_attr} = :empty"
            expression_values = {':empty': None}
        else:
            filter_expression = f"#{qualification_attr} = :status"
            expression_values = {':status': request.status}

        scan_params = {
            'FilterExpression': filter_expression,
            'ExpressionAttributeNames': {f'#{qualification_attr}': qualification_attr},
            'ExpressionAttributeValues': expression_values
        }

        if request.last_evaluated_key:
            scan_params['ExclusiveStartKey'] = {'email': request.last_evaluated_key}

        collected_items = []
        last_key = None

        while len(collected_items) < request.limit:
            scan_params['Limit'] = request.limit - len(collected_items)
            response = domain_table.scan(**scan_params)

            items = response.get('Items', [])
            collected_items.extend(items)

            last_key = response.get('LastEvaluatedKey', {}).get('email')

            if not last_key or len(collected_items) >= request.limit:
                break

            scan_params['ExclusiveStartKey'] = {'email': last_key}

        results = {
            mapped_domain: {
                'items': collected_items[:request.limit],  # Ensure we don't exceed the limit
                'last_evaluated_key': last_key
            }
        }

        return {"status_code": 200, "content": results}

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Error processing request: {str(e)}"}
        )

class AddRequest(BaseModel):
    domain: str
    round: int
    question_data: dict = Body(...)

@admin_app.post('/questions')
async def add_question(request: AddRequest, authorization: str = Depends(get_access_token)):

    try:
        admin_result = await verify_admin(authorization, request.domain)
        if isinstance(admin_result, JSONResponse):
            return admin_result
        
        quiz_table = resources['quiz_table']
        request.round = f"{request.round}"
        
        response = quiz_table.get_item(Key={'qid': request.domain})
        field = response.get('Item')

        if not field:
            field = {
                'qid': request.domain,
                request.round: [request.question_data]
            }
        else:
            if request.round not in field or field[request.round] is None:
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
    status: str
    round: int

@admin_app.post('/qualify')
async def mark_qualification(request: QualificationRequest, authorization: str = Depends(get_access_token)):

    try:
        if request.status not in {"qualified", "unqualified", "pending"}:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid status. Must be 'qualified', 'unqualified', or 'pending'."}
            )
        
        admin_result = await verify_admin(authorization, request.domain)
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
            if prev_status and prev_status.lower() != "qualified":
                return JSONResponse(
                    status_code=409,
                    content={"detail": f"User {request.user_email} did not qualify in round {request.round-1}"}
                )
        
        user[f'qualification_status{request.round}'] = request.status
        domain_table.put_item(Item=user)
        
        return JSONResponse(
            status_code=200,
            content={"detail": f"User {request.user_email} marked as {request.status} for round {request.round}"}
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Error processing request: {str(e)}"}
        )