import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import storage


@pytest.fixture()
def client():
    """TestClient fixture that resets todos before each test."""
    storage.clear()
    with TestClient(app) as c:
        yield c
    storage.clear()


class TestTodoCRUD:
    """Tests for basic CRUD operations."""

    def test_create_todo(self, client):
        response = client.post(
            "/todos",
            json={"title": "Buy groceries", "description": "Milk, eggs, bread"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Buy groceries"
        assert data["description"] == "Milk, eggs, bread"
        assert data["completed"] is False
        assert "created_at" in data

    def test_create_todo_minimal(self, client):
        response = client.post("/todos", json={"title": "Simple task"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Simple task"
        assert data["description"] is None
        assert data["completed"] is False

    def test_list_todos_empty(self, client):
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_todos_multiple(self, client):
        # Create multiple todos
        client.post("/todos", json={"title": "Task 1"})
        client.post("/todos", json={"title": "Task 2"})
        client.post("/todos", json={"title": "Task 3"})

        response = client.get("/todos")
        assert response.status_code == 200
        todos = response.json()
        assert len(todos) == 3
        assert todos[0]["title"] == "Task 1"
        assert todos[1]["title"] == "Task 2"
        assert todos[2]["title"] == "Task 3"

    def test_get_todo(self, client):
        # Create a todo first
        create_response = client.post("/todos", json={"title": "Test todo"})
        todo_id = create_response.json()["id"]

        # Get the todo
        response = client.get(f"/todos/{todo_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == todo_id
        assert data["title"] == "Test todo"

    def test_update_todo_title(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Old title"})
        todo_id = create_response.json()["id"]

        # Update the title
        response = client.put(f"/todos/{todo_id}", json={"title": "New title"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New title"

    def test_update_todo_completed(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Task"})
        todo_id = create_response.json()["id"]

        # Mark as completed
        response = client.put(
            f"/todos/{todo_id}", json={"completed": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True

    def test_update_todo_description(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Task"})
        todo_id = create_response.json()["id"]

        # Update description
        response = client.put(
            f"/todos/{todo_id}",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

    def test_update_todo_multiple_fields(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Task"})
        todo_id = create_response.json()["id"]

        # Update multiple fields
        response = client.put(
            f"/todos/{todo_id}",
            json={
                "title": "Updated task",
                "description": "Updated description",
                "completed": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated task"
        assert data["description"] == "Updated description"
        assert data["completed"] is True

    def test_delete_todo(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Task to delete"})
        todo_id = create_response.json()["id"]

        # Delete the todo
        response = client.delete(f"/todos/{todo_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Todo deleted successfully"

        # Verify it's deleted
        response = client.get(f"/todos/{todo_id}")
        assert response.status_code == 404

    def test_sequential_ids(self, client):
        """Test that todo IDs are sequential."""
        id1 = client.post("/todos", json={"title": "Task 1"}).json()["id"]
        id2 = client.post("/todos", json={"title": "Task 2"}).json()["id"]
        id3 = client.post("/todos", json={"title": "Task 3"}).json()["id"]

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3


class TestErrorHandling:
    """Tests for error cases and edge cases."""

    def test_get_nonexistent_todo(self, client):
        response = client.get("/todos/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Todo not found"

    def test_update_nonexistent_todo(self, client):
        response = client.put("/todos/999", json={"title": "New title"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Todo not found"

    def test_delete_nonexistent_todo(self, client):
        response = client.delete("/todos/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Todo not found"

    def test_create_todo_missing_title(self, client):
        response = client.post("/todos", json={"description": "No title"})
        assert response.status_code == 422  # Validation error


class TestHealthAndMetrics:
    """Tests for health check and metrics endpoints."""

    def test_healthz_returns_ok(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_endpoint_exists(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"app_requests_total" in response.content
        assert b"# HELP app_requests_total" in response.content


class TestResetFunctionality:
    """Tests for the reset/clear endpoint."""

    def test_reset_todos(self, client):
        # Create some todos
        client.post("/todos", json={"title": "Task 1"})
        client.post("/todos", json={"title": "Task 2"})

        # Verify they exist
        response = client.get("/todos")
        assert len(response.json()) == 2

        # Reset
        response = client.delete("/todos")
        assert response.status_code == 200
        assert response.json()["message"] == "All todos cleared"

        # Verify they're gone
        response = client.get("/todos")
        assert response.json() == []

    def test_reset_resets_id_counter(self, client):
        # Create and delete todos
        client.post("/todos", json={"title": "Task 1"})
        client.post("/todos", json={"title": "Task 2"})
        client.delete("/todos")

        # After reset, next todo should have ID 1
        response = client.post("/todos", json={"title": "New task"})
        assert response.json()["id"] == 1
