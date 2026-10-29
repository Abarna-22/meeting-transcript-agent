import hashlib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    bearer_scheme,
    get_current_user,
    hash_password,
    issue_session,
    normalize_email,
    valid_email,
    verify_password,
)
from ..db import get_db
from ..models import AuthSession, Meeting, User
from ..schemas import SignInIn, SignUpIn

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _session_response(user: User, token: str, expires_at) -> dict:
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@router.post("/signup", status_code=201)
def sign_up(body: SignUpIn, db: Session = Depends(get_db)):
    email = normalize_email(body.email)
    if not valid_email(email):
        raise HTTPException(422, "Enter a valid email address.")
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    username = body.username.strip()
    if not username:
        raise HTTPException(422, "Enter a username.")

    is_first_user = db.scalar(select(User.id).limit(1)) is None
    user = User(username=username, email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    if is_first_user:
        db.query(Meeting).filter(Meeting.owner_id.is_(None)).update(
            {Meeting.owner_id: user.id}, synchronize_session=False
        )
    token, expires_at = issue_session(db, user)
    return _session_response(user, token, expires_at)


@router.post("/signin")
def sign_in(body: SignInIn, db: Session = Depends(get_db)):
    email = normalize_email(body.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    token, expires_at = issue_session(db, user)
    return _session_response(user, token, expires_at)


@router.get("/me")
def current_account(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/signout", status_code=204)
def sign_out(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    session = db.get(AuthSession, token_hash)
    if session and session.user_id == user.id:
        db.delete(session)
        db.commit()
