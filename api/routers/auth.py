from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.manager import DBManager
from api.schemas import UserSignup, UserLogin, Token, UserResponse
from api.auth_utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from uuid import uuid4
import psycopg2
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])
db_manager = DBManager()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return customer_id

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup):
    conn = db_manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check if user already exists
                cur.execute("SELECT 1 FROM customers WHERE email = %s", (user_data.email,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )

                customer_id = uuid4()
                hashed_pw = get_password_hash(user_data.password)

                # Use JSONB for profile_info
                import json
                profile_json = json.dumps(user_data.profile_info) if user_data.profile_info else None

                cur.execute(
                    "INSERT INTO customers (customer_id, email, password_hash, profile_info) VALUES (%s, %s, %s, %s)",
                    (str(customer_id), user_data.email, hashed_pw, profile_json)
                )

                return UserResponse(customer_id=customer_id, email=user_data.email)
    finally:
        conn.close()

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm uses 'username' and 'password' fields
    email = form_data.username
    password = form_data.password

    conn = db_manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT customer_id, password_hash FROM customers WHERE email = %s", (email,))
                result = cur.fetchone()

                # Security best practice: generic error message
                if not result or not verify_password(password, result[1]):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect email or password"
                    )

                customer_id = result[0]

                # Create both tokens
                access_token = create_access_token(data={"sub": str(customer_id)})
                refresh_token = create_refresh_token(data={"sub": str(customer_id)})

                return Token(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer"
                )
    finally:
        conn.close()

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    customer_id = payload.get("sub")

    # Create new pair
    new_access_token = create_access_token(data={"sub": customer_id})
    new_refresh_token = create_refresh_token(data={"sub": customer_id})

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )
