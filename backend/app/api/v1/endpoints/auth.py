"""Authentication endpoints for session management and role access."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import LoginRequest, Token, UserCreate, UserRead
from app.services.auth_service import AuthService


router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    summary="User Login",
    description="Authenticate user credentials and issue a role-based JWT.",
)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate a registered user and issue a JWT."""

    user = AuthService.authenticate_user(
        db,
        login_data.email,
        login_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthService.issue_token_for_user(user)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new citizen, admin, or rescue team account.",
)
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Create a new user account."""

    try:
        user = AuthService.create_user(db, user_in)
        return UserRead.model_validate(user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to register user: {str(e)}",
        )