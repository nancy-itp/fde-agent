from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://fde_user:fde_password@localhost:5432/fde_platform"
    environment: str = "development"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480
    cors_allow_origins_raw: str = Field(default="http://localhost:5173", validation_alias="CORS_ALLOW_ORIGINS")

    # PRIO MCP connector (docs/PRIO_MCP_CONNECTOR.md). Left unset by default so
    # the rest of the app runs without it; PrioMcpClient raises a typed
    # configuration error if used before these are set. Per CLAUDE.md §3, the
    # real staging/production token belongs in the secrets manager, never a
    # committed .env — local dev is the only place a real value goes in .env.
    # prio_mcp_base_url is the full MCP endpoint (already includes the /mcp
    # path per the connector doc's "Endpoint" entry) — client.py posts to it
    # directly and does not append a path.
    prio_mcp_base_url: str | None = Field(default=None, validation_alias="PRIO_MCP_BASE_URL")
    prio_mcp_token: str | None = Field(default=None, validation_alias="PRIO_MCP_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_allow_origins(self) -> list[str]:
        """CORS_ALLOW_ORIGINS as a comma-separated env var, split into a list."""
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]


settings = Settings()
