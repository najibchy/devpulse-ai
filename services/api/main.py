import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.webhook import router as webhook_router

logging.basicConfig(level=logging.INFO)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")

app = FastAPI(
    title="DevPulse AI",
    description="Intelligent Code Review & PR Summary Agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(webhook_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "devpulse-api"}
