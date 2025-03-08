from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class EmailSettings(BaseModel):
    sender_address: str
    SMTP_address: str
    SMTP_port: int


class Settings(BaseSettings):
    database_connection: str
    lotw_login_url: str

    # Award urls
    QSO_url: str
    DXCC_url: str
    WAS_url: str
    VUCC_url: str
    WPX_url: str
    WAZ_url: str

    database_key: str = Field(min_length=16, max_length=16)
    session_key: str

    email_settings: EmailSettings
