"""Configuration management for Supply Chain Agents."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure OpenAI Configuration
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_deployment_name: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-02-15-preview"

    # MCP Server URLs
    mcp_supplier_url: str = "http://supplier-data-server:8000"
    mcp_inventory_url: str = "http://inventory-mgmt-server:8001"
    mcp_finance_url: str = "http://finance-data-server:8002"
    mcp_analytics_url: str = "http://analytics-forecast-server:8003"
    mcp_integrations_url: str = "http://integrations-server:8004"

    # Server Configuration
    port: int = 8000
    log_level: str = "INFO"

    # Database (existing)
    database_url: Optional[str] = None


# Global settings instance
settings = Settings()
