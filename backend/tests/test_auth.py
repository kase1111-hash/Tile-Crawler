"""Tests for authentication system."""

import os
import tempfile
import pytest
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.models import UserCreate, UserLogin, User, Token, TokenData
from auth.service import AuthService, get_auth_service, reset_auth_service


class TestAuthModels:
    """Tests for authentication models."""

    def test_user_create_valid(self):
        """Test creating a valid UserCreate."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="secret123"
        )
        assert user.username == "testuser"
        assert user.password == "secret123"

    def test_user_create_no_email(self):
        """Test UserCreate without email."""
        user = UserCreate(
            username="testuser",
            password="secret123"
        )
        assert user.email is None

    def test_user_login(self):
        """Test UserLogin model."""
        login = UserLogin(
            username="testuser",
            password="secret123"
        )
        assert login.username == "testuser"

    def test_user_model(self):
        """Test User model."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(),
            is_active=True
        )
        assert user.id == 1
        assert user.is_active is True


class TestAuthService:
    """Tests for authentication service."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def auth_service(self, temp_db):
        """Create an auth service with temp database."""
        return AuthService(db_path=temp_db)

    def test_initialize(self, auth_service):
        """Test service initialization."""
        auth_service.initialize()
        assert auth_service._initialized is True

    def test_register_user(self, auth_service):
        """Test user registration."""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="secret123"
        )
        user = auth_service.register(user_data)

        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_register_duplicate_username(self, auth_service):
        """Test that duplicate usernames are rejected."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        auth_service.register(user_data)

        # Try to register again with same username
        result = auth_service.register(user_data)
        assert result is None

    def test_register_duplicate_email(self, auth_service):
        """Test that duplicate emails are rejected."""
        user1 = UserCreate(
            username="user1",
            email="test@example.com",
            password="secret123"
        )
        user2 = UserCreate(
            username="user2",
            email="test@example.com",
            password="secret456"
        )

        auth_service.register(user1)
        result = auth_service.register(user2)
        assert result is None

    def test_login_success(self, auth_service):
        """Test successful login."""
        # Register user
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        auth_service.register(user_data)

        # Login
        token = auth_service.login("testuser", "secret123")

        assert token is not None
        assert token.access_token is not None
        assert token.token_type == "bearer"
        assert token.user.username == "testuser"

    def test_login_wrong_password(self, auth_service):
        """Test login with wrong password."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        auth_service.register(user_data)

        token = auth_service.login("testuser", "wrongpassword")
        assert token is None

    def test_login_nonexistent_user(self, auth_service):
        """Test login with nonexistent user."""
        token = auth_service.login("nonexistent", "password")
        assert token is None

    def test_verify_token(self, auth_service):
        """Test token verification."""
        # Register and login
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        auth_service.register(user_data)
        token = auth_service.login("testuser", "secret123")

        # Verify token
        token_data = auth_service.verify_token(token.access_token)

        assert token_data is not None
        assert token_data.username == "testuser"

    def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token."""
        token_data = auth_service.verify_token("invalid_token")
        assert token_data is None

    def test_get_user(self, auth_service):
        """Test getting user by ID."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        registered = auth_service.register(user_data)

        user = auth_service.get_user(registered.id)

        assert user is not None
        assert user.username == "testuser"

    def test_get_user_by_username(self, auth_service):
        """Test getting user by username."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        auth_service.register(user_data)

        user = auth_service.get_user_by_username("testuser")

        assert user is not None
        assert user.username == "testuser"

    def test_change_password(self, auth_service):
        """Test changing password."""
        user_data = UserCreate(
            username="testuser",
            password="oldpassword"
        )
        user = auth_service.register(user_data)

        # Change password
        success = auth_service.change_password(
            user.id,
            "oldpassword",
            "newpassword"
        )
        assert success is True

        # Verify old password no longer works
        token = auth_service.login("testuser", "oldpassword")
        assert token is None

        # Verify new password works
        token = auth_service.login("testuser", "newpassword")
        assert token is not None

    def test_change_password_wrong_old(self, auth_service):
        """Test changing password with wrong old password."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        user = auth_service.register(user_data)

        success = auth_service.change_password(
            user.id,
            "wrongpassword",
            "newpassword"
        )
        assert success is False

    def test_delete_user(self, auth_service):
        """Test soft deleting a user."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        user = auth_service.register(user_data)

        success = auth_service.delete_user(user.id)
        assert success is True

        # Verify user can't login
        token = auth_service.login("testuser", "secret123")
        assert token is None

    def test_update_playtime(self, auth_service):
        """Test updating user playtime."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        user = auth_service.register(user_data)

        auth_service.update_playtime(user.id, 3600)

        updated_user = auth_service.get_user(user.id)
        assert updated_user.total_playtime == 3600

    def test_increment_games_played(self, auth_service):
        """Test incrementing games played."""
        user_data = UserCreate(
            username="testuser",
            password="secret123"
        )
        user = auth_service.register(user_data)

        auth_service.increment_games_played(user.id)
        auth_service.increment_games_played(user.id)

        updated_user = auth_service.get_user(user.id)
        assert updated_user.games_played == 2


class TestAuthAPI:
    """Tests for authentication API endpoints."""

    @pytest.fixture
    def test_client(self):
        """Create a test client with clean database."""
        # Use temp database - set env BEFORE resetting auth service
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        os.environ["DB_PATH"] = temp_db.name

        # Now reset auth service so it picks up the new DB_PATH
        reset_auth_service()

        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        yield client

        # Cleanup
        temp_db.close()
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)
        reset_auth_service()

    def test_register_endpoint(self, test_client):
        """Test registration endpoint."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "secret123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["username"] == "testuser"

    def test_register_duplicate(self, test_client):
        """Test registration with duplicate username."""
        # First registration
        test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret123"}
        )

        # Second registration with same username
        response = test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret456"}
        )

        assert response.status_code == 400

    def test_login_endpoint(self, test_client):
        """Test login endpoint."""
        # Register first
        test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret123"}
        )

        # Login
        response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "secret123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid(self, test_client):
        """Test login with invalid credentials."""
        response = test_client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "wrong"}
        )

        assert response.status_code == 401

    def test_get_me_authenticated(self, test_client):
        """Test getting current user when authenticated."""
        # Register and get token
        register_resp = test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret123"}
        )
        token = register_resp.json()["access_token"]

        # Get current user
        response = test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

    def test_get_me_unauthenticated(self, test_client):
        """Test getting current user when not authenticated."""
        response = test_client.get("/api/auth/me")
        assert response.status_code == 401

    def test_save_with_auth(self, test_client):
        """Test saving game when authenticated."""
        # Register and get token
        register_resp = test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret123"}
        )
        token = register_resp.json()["access_token"]

        # Start a new game
        test_client.post("/api/game/new", json={})

        # Save game
        response = test_client.post(
            "/api/game/save?save_name=mysave",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_list_saves_with_auth(self, test_client):
        """Test listing saves when authenticated."""
        # Register and get token
        register_resp = test_client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "secret123"}
        )
        token = register_resp.json()["access_token"]

        # Start a new game and save
        test_client.post("/api/game/new", json={})
        test_client.post(
            "/api/game/save?save_name=mysave",
            headers={"Authorization": f"Bearer {token}"}
        )

        # List saves
        response = test_client.get(
            "/api/game/saves",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user"] == "testuser"
        assert data["count"] >= 1


class TestSingleton:
    """Tests for singleton management."""

    def test_get_auth_service_returns_same_instance(self):
        """Test that get_auth_service returns singleton."""
        reset_auth_service()
        service1 = get_auth_service()
        service2 = get_auth_service()
        assert service1 is service2

    def test_reset_auth_service(self):
        """Test that reset creates new instance."""
        service1 = get_auth_service()
        reset_auth_service()
        service2 = get_auth_service()
        assert service1 is not service2

    def teardown_method(self):
        """Clean up after each test."""
        reset_auth_service()
