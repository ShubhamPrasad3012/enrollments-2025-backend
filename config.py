import boto3
import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv
load_dotenv()

def initialize():
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
    )

    domain_tables = {
        "ai": dynamodb.Table("domain-ai"),
        "app": dynamodb.Table("domain-app"),
        "events": dynamodb.Table("domain-events"),
        "graphic": dynamodb.Table("domain-graphic"),
        "iot": dynamodb.Table("domain-iot"),
        "pnm": dynamodb.Table("domain-pnm"),
        "rnd": dynamodb.Table("domain-rnd"),
        "ui": dynamodb.Table("domain-ui"),
        "video": dynamodb.Table("domain-video"),
        "web": dynamodb.Table("domain-web")
    }

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
        'interview_table': interview_table,
        'domain_tables': domain_tables
    }

resources = None

def get_resources():
    global resources
    if resources is None:
        resources = initialize()
    return resources
