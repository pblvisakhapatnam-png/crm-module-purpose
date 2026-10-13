from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("username", "password")
    @classmethod
    def _storable_text(cls, value: str) -> str:
        # A NUL character cannot reach PostgreSQL and a lone surrogate is not UTF-8: either made the sign-in answer 500
        # (TB-1 TB1-204 part a). Refused as a malformed request instead, before anything is counted or checked.
        if "\x00" in value:
            raise ValueError("must not contain a NUL character")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("must be valid UTF-8 text") from exc
        return value


class AuthUser(BaseModel):
    public_id: str
    username: str
    display_name: str
    roles: list[str]
    role_codes: list[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class RoleSummary(BaseModel):
    role_code: str
    role_name: str