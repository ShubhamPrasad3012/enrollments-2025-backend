from fastapi import FastAPI
from routes.users import users_router
from routes.slots import slots_router

# Main FastAPI application
app = FastAPI()

# Mount the routes
app.include_router(users_router, prefix="/getdata", tags=["Users"])
app.include_router(slots_router, prefix="/book-slot", tags=["Slots"])
