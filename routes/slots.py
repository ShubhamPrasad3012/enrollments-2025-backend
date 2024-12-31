from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3

# Initialize APIRouter
slots_router = APIRouter()

# DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
user_table = dynamodb.Table("enrollments-site-users")

# Time slots data
time_slots = [
    {"slot_id": "1", "start_time": "09:00 AM", "end_time": "10:00 AM", "bookedBy": []},
    {"slot_id": "2", "start_time": "10:00 AM", "end_time": "11:00 AM", "bookedBy": []},
    {"slot_id": "3", "start_time": "11:00 AM", "end_time": "12:00 PM", "bookedBy": []},
    {"slot_id": "4", "start_time": "01:00 PM", "end_time": "02:00 PM", "bookedBy": []},
    {"slot_id": "5", "start_time": "02:00 PM", "end_time": "03:00 PM", "bookedBy": []},
]


class SlotRequest(BaseModel):
    uid: str
    slot_id: str


@slots_router.post("/")
async def book_slot(slot_request: SlotRequest):
    """
    Book a slot for a user.
    """
    try:
        # Step 1: Query DynamoDB to check if the user exists
        response = user_table.get_item(Key={"uid": slot_request.uid})
        user = response.get("Item")

        # Step 2: If the user is not found, return a 404 error
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with UID {slot_request.uid} not found."
            )

        # Step 3: Check if the user has already booked the slot
        if "slots" in user and slot_request.slot_id in user["slots"]:
            raise HTTPException(
                status_code=400,
                detail=f"User {user['name']} (Domain: {user.get('domain', 'N/A')}) has already booked slot {slot_request.slot_id}."
            )

        # Step 4: Append the new slot to their slots
        updated_slots = user.get("slots", [])
        updated_slots.append(slot_request.slot_id)

        # Step 5: Update the user's slots in DynamoDB
        user_table.update_item(
            Key={"uid": user["uid"]},
            UpdateExpression="SET slots = :slots",
            ExpressionAttributeValues={":slots": updated_slots},
        )

        # Step 6: Find the slot by slot_id and update its bookedBy list
        slot = next((s for s in time_slots if s["slot_id"] == slot_request.slot_id), None)
        if not slot:
            raise HTTPException(status_code=400, detail="Invalid slot ID.")

        slot["bookedBy"].append(f"{user['name']} (Domain: {user.get('domain', 'N/A')})")

        # Step 7: Return success response
        return {
            "message": f"Slot {slot_request.slot_id} booked successfully by user {user['name']} (Domain: {user.get('domain', 'N/A')}).",
            "bookedBy": slot["bookedBy"],
            "userDetails": user,
        }

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while booking the slot: {str(e)}"
        )
