from __future__ import annotations
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, health, support
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="GigSaathi AI Chatbot Service")

# Same-origin policy as the existing Node backend's CORS config
# (server.js) — credentialed requests from the same two dev origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(support.router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # noqa: ANN001, ANN201
    # Section 38: never leak a Python traceback to the end user.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return await http_exception_handler(
        request, HTTPException(status_code=500, detail="Something went wrong. Please try again.")
    )
