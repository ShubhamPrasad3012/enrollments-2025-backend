import boto3
import os
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

user_table_name = "enrollments-site-users"
quiz_table_name = "enrollments-site-quiz"
user_table = dynamodb.Table(user_table_name)
quiz_table = dynamodb.Table(quiz_table_name)
interview_table=dynamodb.Table("enrollments-site-interview")

cred = credentials.Certificate("./serviceAccountKey.json")
firebase_app = firebase_admin.initialize_app(cred)

firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")  
}

def get_firebase_app():
    return firebase_app
