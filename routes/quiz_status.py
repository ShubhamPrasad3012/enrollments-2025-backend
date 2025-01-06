from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from decimal import Decimal

# Sub-application for quiz status
quiz_status_app = FastAPI()

# DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
user_table = dynamodb.Table("enrollments-site-quiz")

REQUIRED_QUESTIONS = 10  # Replace with your actual number of questions

# Pydantic model to parse the request body
class UserRequest(BaseModel):
    qid: str  # Use qid instead of uid

@quiz_status_app.post("/quiz-status")
async def quiz_status(request: UserRequest):
    qid = request.qid  # Extract qid from the request body

    try:
        # Retrieve the user data from DynamoDB using the qid
        response = user_table.get_item(Key={'qid': qid})
        user = response.get('Item')

        # If user doesn't exist, return an error
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Debug: Print the user data for troubleshooting
        print("User Data Retrieved:", user)

        # Check if the `qs` field exists and is a list
        questions = user.get('qs', [])
        if not questions:
            # If no questions have been answered yet, set status as pending
            user_table.update_item(
                Key={'qid': qid},
                UpdateExpression="SET #quiz_status = :status",
                ExpressionAttributeNames={"#quiz_status": "quizstatus"},
                ExpressionAttributeValues={":status": "pending"}
            )
            return {"status": "pending", "message": "No questions answered. Quiz is pending."}

        # Debug: Print the structure of the questions
        print("Questions Structure:", questions)

        # Count the number of answered questions by checking for a Decimal value in the third position
        answered_questions = 0
        for question in questions:
            # Debug: Print each question's data
            print("Question Data:", question)

            # The third element in each question array is a Decimal indicating if answered
            if isinstance(question[2], Decimal) and question[2] != Decimal('0'):
                answered_questions += 1

        # Debug: Print the number of answered questions
        print("Answered Questions:", answered_questions)

        # Check if the user has completed the required number of answers
        if answered_questions < REQUIRED_QUESTIONS:
            # Set quiz status to pending
            user_table.update_item(
                Key={'qid': qid},
                UpdateExpression="SET #quiz_status = :status",
                ExpressionAttributeNames={"#quiz_status": "quizstatus"},
                ExpressionAttributeValues={":status": "pending"}
            )
            return {
                "status": "pending",
                "message": f"Quiz is in progress. {answered_questions} out of {REQUIRED_QUESTIONS} questions answered."
            }

        # Quiz is completed, update status to completed
        user_table.update_item(
            Key={'qid': qid},
            UpdateExpression="SET #quiz_status = :status",
            ExpressionAttributeNames={"#quiz_status": "quizstatus"},
            ExpressionAttributeValues={":status": "completed"}
        )

        return {"status": "completed", "message": "Quiz is completed."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching quiz status: {str(e)}")
