import boto3
import firebase_admin
from firebase_admin import credentials
import os

def initialize():
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
    )
    user_table = dynamodb.Table("enrollments-site-users")
    quiz_table = dynamodb.Table("enrollments-site-quiz")
    interview_table = dynamodb.Table("enrollments-site-interview")

    if not firebase_admin._apps:
        cred = credentials.Certificate("./serviceAccountKey.json")
        firebase_app = firebase_admin.initialize_app(cred)
    else:
        firebase_app = firebase_admin.get_app()

    return {
        'firebase_app': firebase_app,
        'user_table': user_table,
        'quiz_table': quiz_table,
        'interview_table': interview_table
    }

def get_resources():
    return initialize()
