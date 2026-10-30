import secrets

from fastapi import Depends, Header, HTTPException, status

from config import Settings, get_settings


def require_master(
    x_master_password: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Shared master password from the X-Master-Password header. An empty setting disables the check."""
    expected = settings.MASTER_PASSWORD.get_secret_value()
    if not expected:
        return
    given = x_master_password or ""
    if not secrets.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or wrong master password")
