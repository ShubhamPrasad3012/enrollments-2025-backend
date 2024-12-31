from fastapi import APIRouter, HTTPException
import boto3
from typing import List

# Initialize APIRouter
users_router = APIRouter()

# DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
user_table = dynamodb.Table("enrollments-site-users")


@users_router.get("/", response_model=List[dict])
async def get_all_users():
    """
    Fetch all users from the DynamoDB table and return as formatted JSON.
    """
    try:
        # Use the scan operation to retrieve all items from the table
        response = user_table.scan()
        items = response.get("Items", [])

        # Handle pagination if there are more items than the scan limit
        while "LastEvaluatedKey" in response:
            response = user_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        return items

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
