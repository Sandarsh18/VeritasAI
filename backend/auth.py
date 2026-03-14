from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import User

SECRET_KEY = "veritasai-secret-key-2026-rvce-mca"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER = 60 * 24 * 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
TOKEN_BLACKLIST = set()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    if not token or token in TOKEN_BLACKLIST:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_user(token: str, db: Session) -> Optional[User]:
    username = verify_token(token)
    if not username:
        return None
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None
    return user


def get_optional_user(token: str, db: Session) -> Optional[User]:
    return get_current_user(token, db)
