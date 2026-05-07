from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Todo App")
app.include_router(router)
