from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.domain import domain_app
from routes.user import user
from routes.answer import ans_app
from routes.slots import slot_app
from config import initialize
from fastapi.responses import JSONResponse

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

# Optional: Additional preflight handler if needed
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",  # Dynamic based on request origin
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Mount your routers
app.mount("/user", user)
app.mount("/domain", domain_app)
app.mount("/answer", ans_app)
app.mount("/slots", slot_app)
