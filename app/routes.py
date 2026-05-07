from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

router = APIRouter()

# Prometheus metrics
REQUEST_COUNTER = Counter(
    "app_requests_total",
    "Total HTTP requests handled by the todo app",
    ["endpoint"],
)


# Pydantic models for request/response validation
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


class Todo(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    created_at: str


# In-memory storage
class TodoStorage:
    def __init__(self):
        self.todos = {}
        self.next_id = 1

    def create(self, title: str, description: Optional[str] = None) -> Todo:
        todo_id = self.next_id
        self.next_id += 1
        todo = Todo(
            id=todo_id,
            title=title,
            description=description,
            completed=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.todos[todo_id] = todo
        return todo

    def get(self, todo_id: int) -> Optional[Todo]:
        return self.todos.get(todo_id)

    def list_all(self) -> list[Todo]:
        return list(self.todos.values())

    def update(self, todo_id: int, **kwargs) -> Optional[Todo]:
        todo = self.todos.get(todo_id)
        if not todo:
            return None

        # Update fields if provided
        if "title" in kwargs and kwargs["title"] is not None:
            todo.title = kwargs["title"]
        if "description" in kwargs and kwargs["description"] is not None:
            todo.description = kwargs["description"]
        if "completed" in kwargs and kwargs["completed"] is not None:
            todo.completed = kwargs["completed"]

        self.todos[todo_id] = todo
        return todo

    def delete(self, todo_id: int) -> bool:
        if todo_id in self.todos:
            del self.todos[todo_id]
            return True
        return False

    def clear(self):
        self.todos = {}
        self.next_id = 1


# Global storage instance
storage = TodoStorage()


# Routes
@router.get("/todos")
def list_todos():
    REQUEST_COUNTER.labels(endpoint="/todos").inc()
    return storage.list_all()


@router.post("/todos")
def create_todo(todo_data: TodoCreate):
    REQUEST_COUNTER.labels(endpoint="/todos").inc()
    return storage.create(title=todo_data.title, description=todo_data.description)


@router.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    REQUEST_COUNTER.labels(endpoint="/todos/{todo_id}").inc()
    todo = storage.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo_data: TodoUpdate):
    REQUEST_COUNTER.labels(endpoint="/todos/{todo_id}").inc()
    todo = storage.update(
        todo_id,
        title=todo_data.title,
        description=todo_data.description,
        completed=todo_data.completed,
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    REQUEST_COUNTER.labels(endpoint="/todos/{todo_id}").inc()
    if not storage.delete(todo_id):
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}


@router.delete("/todos")
def reset_todos():
    REQUEST_COUNTER.labels(endpoint="/todos").inc()
    storage.clear()
    return {"message": "All todos cleared"}


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
