"""Application settings (pydantic-settings).

Ported from Go ``internal/config/config.go`` and env usage across
``cmd/*`` binaries. All secrets come from the environment / .env file;
nothing secret is ever committed (only .env.example is in git).
"""

from datetime import timedelta
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Root settings, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_name: str = "canning-erp"
    log_level: str = "INFO"

    # --- Database (maintenance / super admin DB) ---
    super_admin_dsn: str
    db_host: str = "localhost"
    db_port: int = 5432
    maintenance_user: str = "canning"
    maintenance_password: str = ""

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Security ---
    #: 64 hex chars = 32 bytes (AES-256-GCM key for tenant DB passwords).
    encryption_key: str
    jwt_secret: str
    access_ttl_min: int = 15
    refresh_ttl_days: int = 30

    # --- Tenant cache (Go: TenantCacheSettings) ---
    tenant_cache_size: int = 1000
    tenant_cache_ttl_seconds: int = 60

    # --- Rate limiting (Go: RateLimiterSettings) ---
    rate_limit_type: str = "memory"  # memory | redis
    rate_limit_requests_per_min: int = 120
    rate_limit_login_per_min: int = 10

    # --- Pool sizing (Go pool.go defaults) ---
    pool_max_open: int = 25
    pool_max_idle: int = 5
    pool_lifetime_min: int = 30
    pool_idle_timeout_min: int = 5

    @field_validator("encryption_key")
    @classmethod
    def _validate_encryption_key(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("ENCRYPTION_KEY must be 64 hex chars (32 bytes)")
        int(v, 16)  # raises ValueError if not hex
        return v

    @property
    def access_ttl(self) -> timedelta:
        return timedelta(minutes=self.access_ttl_min)

    @property
    def refresh_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_ttl_days)

    @property
    def tenant_cache_ttl(self) -> timedelta:
        return timedelta(seconds=self.tenant_cache_ttl_seconds)


@lru_cache
def get_settings() -> Settings:
    """Cached accessor (composition root may also build Settings directly)."""
    return Settings()
