from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "cloudops-console"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"

    openrouter_api_key: str = ""
    openrouter_model: str = ""
    cost_analysis_model: str = "openai/gpt-4o"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 45.0
    openrouter_max_retries: int = 2
    openrouter_max_tokens: int = 1200
    insforge_url: str = ""
    insforge_api_key: str = ""
    insforge_timeout_seconds: float = 15.0
    cloud_scan_timeout_seconds: int = 60
    gcp_project_id: str = ""
    kubeconfig_path: str = ""
    kubectl_timeout_seconds: int = 30
    kubectl_log_tail_lines: int = 200
    container_creating_timeout_seconds: int = 300
    vulnerability_scan_timeout_seconds: int = 600
    agent_heartbeat_seconds: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
