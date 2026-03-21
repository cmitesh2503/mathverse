from fastapi import FastAPI
from backend.app.api.routes import session

app = FastAPI(title="MathVerse API")

app.include_router(session.router)