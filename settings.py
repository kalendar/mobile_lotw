from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_connection: str
    lotw_login_url: str
    QSO_url: str
    database_key: str = Field(min_length=16, max_length=16)
    session_key: str
