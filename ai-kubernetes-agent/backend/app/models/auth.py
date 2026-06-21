from uuid import UUID

from pydantic import BaseModel


class AuthContext(BaseModel):
    user_id: UUID
    email: str | None = None
    access_token: str
