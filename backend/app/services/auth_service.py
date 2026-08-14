from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.schemas.v1 import UserOut


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        role_name: str = "Operator",
    ) -> User:
        """Create a new user."""
        password_hash = hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role_name=role_name,
            is_active=True,
        )
        session.add(user)
        await session.flush()  # Flush to get the ID but don't commit yet
        return user

    @staticmethod
    async def authenticate_user(
        session: AsyncSession, email: str, password: str
    ) -> User | None:
        """Authenticate user by email and password."""
        user = await AuthService.get_user_by_email(session, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    async def change_password(
        session: AsyncSession, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """Change user password."""
        user = await AuthService.get_user_by_id(session, user_id)
        if not user:
            return False
        if not verify_password(old_password, user.password_hash):
            return False
        
        user.password_hash = hash_password(new_password)
        await session.flush()
        return True

    @staticmethod
    def user_to_schema(user: User) -> UserOut:
        """Convert User model to UserOut schema."""
        return UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            role_name=user.role_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
