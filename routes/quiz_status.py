from fastapi import FastAPI,HTTPException,Depends
from pydantic import BaseModel
import boto3
from config import user_table
quiz_status = FastAPI()


# Request model
class QuizStatusRequest(BaseModel):
    uid: str

@quiz_status.post("/", response_model=dict)
async def get_quiz_status(request: QuizStatusRequest):
    """
    Endpoint to fetch and update the quiz status of a user based on their domain and QnA data.
    """
    try:
        # Fetch user data from DynamoDB using the provided UID
        response = user_table.get_item(Key={"uid": request.uid})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = response["Item"]

        # Extract the necessary fields with defaults
        domain = user_data.get("domain", [])
        qna = user_data.get("qna", {})
        pending = {"tech": [], "management": [], "design": []}
        completed = {"tech": [], "management": [], "design": []}

        # Domain categories
        tech_domains = {"app", "iot", "web", "ai/ml", "Research"}
        management_domains = {"event", "pnm"}
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
            Key={"uid": request.uid},
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
