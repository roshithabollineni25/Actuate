"""Authentication service providing token issuance and credential verification."""

from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, Token, UserRead



class AuthService:
    """Service handling user authentication and token creation."""

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Create a new registered user."""
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role,
            phone_number=user_in.phone_number,
            is_active=user_in.is_active,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> Optional[User]:
        """Authenticate user by email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def issue_token_for_user(user: User) -> Token:
        """Issue a standard JWT access token for an authenticated user."""
        token_str = create_access_token(subject=user.id, role=user.role.value)
        return Token(
            access_token=token_str,
            token_type="bearer",
            role=user.role,
            user=UserRead.model_validate(user),
        )

    @staticmethod
    def create_mock_session(role: UserRole, email: str) -> Token:
        """
        Create a development/demonstration token for the requested role.
        Used during development to test role-specific dashboards.
        """
        token_str = create_access_token(subject=f"mock-{email}", role=role.value)
        return Token(
            access_token=token_str,
            token_type="bearer",
            role=role,
        )
