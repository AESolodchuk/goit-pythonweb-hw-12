""" Main file to run the FastAPI application. """

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from src.api import auth, contacts, users, utils
from src.conf import messages

app = FastAPI()
app.include_router(utils.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")

origins = ["<http://localhost:8000>"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": f"Перевищено ліміт запитів ({exc.detail}). Спробуйте пізніше."
        },
    )


@app.get("/")
async def root():
    """Return the welcome message for the API root endpoint."""
    return {"message": messages.WELCOME_MESSAGE}


if __name__ == "__main__":

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, workers=1)
