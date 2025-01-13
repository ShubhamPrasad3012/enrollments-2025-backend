from fastapi import FastAPI
from firebase_admin import auth
from fastapi.middleware.cors import CORSMiddleware
from config import user_table, quiz_table, get_firebase_app
from routes.domain import domain_app
from routes.user import user
from routes.answer import ans_app
from routes.slots import slot_app
from routes.quiz_progress import quiz_app
from routes.quiz_status import quiz_status


origins = [
    "http://localhost:5173",  
    "https://yourfrontenddomain.com",  
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

app.mount("/user", user)
app.mount("/domain", domain_app)
app.include_router(quiz_status_router, prefix="/quiz-status")
app.mount("/answer", ans_app)
app.mount("/slots", slot_app)
app.mount("/quiz", quiz_app)
app.mount("/quiz-status", quiz_status)

