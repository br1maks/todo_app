from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, todos, categories

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})
app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(categories.router)

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok"}