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

    # MCP Server URLs - Default to Azure, override via env for local dev
    # Azure deployed MCP servers (bluewave environment)
    mcp_supplier_url: str = "https://mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io"
    mcp_inventory_url: str = "https://mcp-inventory-mgmt.bluewave-ee01b5af.eastus.azurecontainerapps.io"
    mcp_finance_url: str = "https://mcp-finance-data.bluewave-ee01b5af.eastus.azurecontainerapps.io"
    mcp_analytics_url: str = "https://mcp-analytics-forecast.bluewave-ee01b5af.eastus.azurecontainerapps.io"
    mcp_integrations_url: str = "https://mcp-integrations.bluewave-ee01b5af.eastus.azurecontainerapps.io"

    # Server Configuration
    port: int = 8000
    log_level: str = "INFO"

    # Database (existing)
    database_url: Optional[str] = None


# Global settings instance
settings = Settings()
