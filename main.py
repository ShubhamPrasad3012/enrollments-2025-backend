from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.domain import domain_app
from routes.user import user
from routes.answer import ans_app
from routes.slots import slot_app
from config import initialize
from fastapi.responses import FileResponse
import os

origins = [
    "*"
]

app = FastAPI()

# CORS middleware configuration with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use specific origins instead of wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI!"}

@app.get("/favicon.ico")
def get_favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), "favicon.svg")
    return FileResponse(favicon_path)


app.mount("/user", user)
app.mount("/domain", domain_app)
app.mount("/answer", ans_app)
app.mount("/slots", slot_app)
