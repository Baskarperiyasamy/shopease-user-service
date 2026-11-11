from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ShopEase User Management Service"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "user_service"
    mysql_password: str = ""
    mysql_database: str = "shopease_user_db"
    database_url: str | None = None

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    token_verification_mode: Literal["local", "remote"] = "local"
    auth_service_url: str = "http://host.docker.internal:8001"
    auth_request_timeout: float = 5.0

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        url = URL.create(
            drivername="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )
        return url.render_as_string(hide_password=False)


settings = Settings()
