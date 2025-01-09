from fastapi import FastAPI
from routes.quiz_status import quiz_status_app

# Main application
app = FastAPI()

# Mount the route
app.mount("/", quiz_status_app)
