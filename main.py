from fastapi import FastAPI
from firebase_admin import auth
from config import user_table, quiz_table, get_firebase_app
from typing import List
from routes.domain import domain_app
from routes.user import user

app = FastAPI()
app.mount("/login", user)
app.mount("/domain", domain_app)

