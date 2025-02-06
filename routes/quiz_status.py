from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_admin import auth

from config import initialize

quiz_status = FastAPI()

resources = initialize()
user_table = resources['user_table']

# Request model (including token in body)
class QuizStatusRequest(BaseModel):
    token: str

@quiz_status.post("/", response_model=dict)
async def get_quiz_status(request: QuizStatusRequest):
    """
    Endpoint to fetch and update the quiz status of a user based on their domain and QnA data.
    """
    try:
        # Verify the Firebase token
        decoded_token = auth.verify_id_token(request.token, app=resources["firebase_app"])
        email = decoded_token.get("email")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid or missing email in token.")

        # Fetch user data from DynamoDB using the email (assuming it's stored as UID)
        response = user_table.get_item(Key={"uid": email})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = response["Item"]

        # Extract domain information
        domain_data = user_data.get("domain", {})  # Get domain map
        management_domains = domain_data.get("Management", [])  # List of Management domains
        technical_domains = domain_data.get("Technical", [])  # List of Technical domains
        design_domains = domain_data.get("Design", [])  # Fetch Design domains

        # Combine domains into one list
        domain = management_domains + technical_domains + design_domains

        # Extract QnA data
        qna = user_data.get("qna", {})

        # Initialize pending and completed domain lists
        pending = {"tech": [], "management": [], "design": []}
        completed = {"tech": [], "management": [], "design": []}

        # Domain categories
        tech_domains = {"web", "iot", "ai/ml", "Research"}
        management_domains = {"Events", "pnm"}
        design_domains = {"ui/ux", "graphic design", "video editing"}

        # Categorize domains into pending or completed
        for d in domain:
            domain_qna = qna.get(d)
            has_answers = domain_qna and "answers" in domain_qna and domain_qna["answers"]

            if not has_answers:
                if d in tech_domains:
                    pending["tech"].append(d)
                elif d in management_domains:
                    pending["management"].append(d)
                elif d in design_domains:
                    pending["design"].append(d)
            else:
                if d in tech_domains:
                    completed["tech"].append(d)
                elif d in management_domains:
                    completed["management"].append(d)
                elif d in design_domains:
                    completed["design"].append(d)

        # Determine overall quiz status
        quiz_status = "pending" if any(pending.values()) else "completed"

        # Update the quizStatus field in DynamoDB
        user_table.update_item(
            Key={"uid": email},
            UpdateExpression="SET quizstatus = :status",
            ExpressionAttributeValues={":status": quiz_status}
        )

        # Return the response
        return {
            "user": {
                "domainSelection": {
                    "pending": pending,
                    "completed": completed
                },
                "quizStatus": quiz_status
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
