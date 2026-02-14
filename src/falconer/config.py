"""Configuration management for Falconer."""

import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Main configuration class for Falconer."""

    # Environment
    env: str = Field(default="dev", env="ENV")

    # Bitcoin Knots Configuration
    bitcoind_scheme: str = Field(default="http", env="BITCOIND_SCHEME")
    bitcoind_host_local: str = Field(default="127.0.0.1", env="BITCOIND_HOST_LOCAL")
    bitcoind_host_ip: str = Field(default="127.0.0.1", env="BITCOIND_HOST_IP")
    bitcoind_port: int = Field(default=8332, env="BITCOIND_PORT")
    bitcoind_rpc_user: str = Field(default="bitcoin", env="BITCOIND_RPC_USER")
    bitcoind_rpc_pass: str = Field(default="", env="BITCOIND_RPC_PASS")

    # Electrs Configuration
    electrs_scheme: str = Field(default="http", env="ELECTRS_SCHEME")
    electrs_host_local: str = Field(default="127.0.0.1", env="ELECTRS_HOST_LOCAL")
    electrs_host_ip: str = Field(default="127.0.0.1", env="ELECTRS_HOST_IP")
    electrs_port: int = Field(default=50001, env="ELECTRS_PORT")

    # LNbits Configuration
    lnbits_scheme: str = Field(default="http", env="LNBITS_SCHEME")
    lnbits_host_local: str = Field(default="127.0.0.1", env="LNBITS_HOST_LOCAL")
    lnbits_host_ip: str = Field(default="127.0.0.1", env="LNBITS_HOST_IP")
    lnbits_port: int = Field(default=5000, env="LNBITS_PORT")
    lnbits_api_key: str = Field(default="", env="LNBITS_API_KEY")
    lnbits_wallet_id: str = Field(default="", env="LNBITS_WALLET_ID")

    # Policy Configuration
    policy_path: str = Field(default="policy/dev.policy.json", env="POLICY_PATH")

    # Spending Limits (can be overridden by policy file)
    max_daily_spend_sats: int = Field(default=100000, env="MAX_DAILY_SPEND_SATS")
    max_single_tx_sats: int = Field(default=50000, env="MAX_SINGLE_TX_SATS")
    allowed_destinations: List[str] = Field(default=[], env="ALLOWED_DESTINATIONS")

    # AI Configuration (vLLM, OpenAI-compatible API)
    vllm_model: str = Field(default="llama3.1:8b", env="VLLM_MODEL")
    vllm_base_url: str = Field(default="http://localhost:8000/v1", env="VLLM_BASE_URL")
    ai_risk_tolerance: str = Field(default="medium", env="AI_RISK_TOLERANCE")  # low, medium, high
    ai_confidence_threshold: float = Field(default=0.6, env="AI_CONFIDENCE_THRESHOLD")
    ai_decision_interval_minutes: int = Field(default=5, env="AI_DECISION_INTERVAL_MINUTES")

    # Funding Proposal Configuration
    funding_proposal_enabled: bool = Field(default=False, env="FUNDING_PROPOSAL_ENABLED")
    funding_proposal_threshold_sats: int = Field(default=50000, env="FUNDING_PROPOSAL_THRESHOLD_SATS")
    funding_proposal_default_amount_sats: int = Field(default=500000, env="FUNDING_PROPOSAL_DEFAULT_AMOUNT_SATS")
    funding_proposal_max_pending: int = Field(default=3, env="FUNDING_PROPOSAL_MAX_PENDING")
    funding_proposal_expiry_hours: int = Field(default=24, env="FUNDING_PROPOSAL_EXPIRY_HOURS")

    # n8n Integration Configuration
    n8n_webhook_url: str = Field(default="", env="N8N_WEBHOOK_URL")
    n8n_webhook_auth_token: Optional[str] = Field(default=None, env="N8N_WEBHOOK_AUTH_TOKEN")
    n8n_webhook_secret: str = Field(default="", env="N8N_WEBHOOK_SECRET")
    n8n_webhook_timeout_seconds: int = Field(default=30, env="N8N_WEBHOOK_TIMEOUT_SECONDS")

    # Webhook Server Configuration
    webhook_server_enabled: bool = Field(default=True, env="WEBHOOK_SERVER_ENABLED")
    webhook_server_host: str = Field(default="0.0.0.0", env="WEBHOOK_SERVER_HOST")
    webhook_server_port: int = Field(default=8080, env="WEBHOOK_SERVER_PORT")
    webhook_server_reload: bool = Field(default=False, env="WEBHOOK_SERVER_RELOAD")

    # Wallet Configuration
    change_address: Optional[str] = Field(default=None, env="CHANGE_ADDRESS")

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

<<<<<<< HEAD
    # OpenClaw Integration (PoC)
    openclaw_enabled: bool = Field(default=False, env="OPENCLAW_ENABLED")
    openclaw_api_key: str = Field(default="", env="OPENCLAW_API_KEY")
    openclaw_webhook_url: str = Field(default="", env="OPENCLAW_WEBHOOK_URL")
=======
    # Ollama AI Configuration
    ollama_model: str = Field(default="llama3.1:8b", env="OLLAMA_MODEL")
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")

    # Funding Proposal Configuration
    funding_proposal_enabled: bool = Field(default=False, env="FUNDING_PROPOSAL_ENABLED")
    funding_proposal_threshold_sats: int = Field(default=50000, env="FUNDING_PROPOSAL_THRESHOLD_SATS")
    funding_proposal_max_pending: int = Field(default=3, env="FUNDING_PROPOSAL_MAX_PENDING")
    funding_proposal_default_amount_sats: int = Field(default=100000, env="FUNDING_PROPOSAL_DEFAULT_AMOUNT_SATS")
    funding_proposal_expiry_hours: int = Field(default=24, env="FUNDING_PROPOSAL_EXPIRY_HOURS")

    # n8n Integration Configuration
    n8n_webhook_url: Optional[str] = Field(default=None, env="N8N_WEBHOOK_URL")
    n8n_webhook_secret: Optional[str] = Field(default=None, env="N8N_WEBHOOK_SECRET")
>>>>>>> b1a116d3a98b001a8622efcbb26f8c7486c0b6b6

    @field_validator("max_single_tx_sats")
    @classmethod
    def single_tx_less_than_daily(cls, v, info):
        """Ensure single transaction limit is less than daily limit."""
        if (
            info.data
            and "max_daily_spend_sats" in info.data
            and v > info.data["max_daily_spend_sats"]
        ):
            raise ValueError(
                "max_single_tx_sats must be less than or equal to max_daily_spend_sats"
            )
        return v

    @field_validator("allowed_destinations", mode="before")
    @classmethod
    def parse_allowed_destinations(cls, v):
        """Parse comma-separated allowed destinations from environment."""
        if isinstance(v, str):
            return [dest.strip() for dest in v.split(",") if dest.strip()]
        return v or []

    @field_validator("funding_proposal_threshold_sats")
    @classmethod
    def validate_funding_threshold(cls, v):
        """Ensure funding threshold is positive."""
        if v <= 0:
            raise ValueError("funding_proposal_threshold_sats must be positive")
        return v

    @field_validator("funding_proposal_default_amount_sats")
    @classmethod
    def validate_funding_default_amount(cls, v):
        """Ensure default funding amount is positive."""
        if v <= 0:
            raise ValueError("funding_proposal_default_amount_sats must be positive")
        return v

    @field_validator("funding_proposal_max_pending")
    @classmethod
    def validate_max_pending(cls, v):
        """Ensure max pending proposals is positive."""
        if v <= 0:
            raise ValueError("funding_proposal_max_pending must be positive")
        return v

    @field_validator("funding_proposal_expiry_hours")
    @classmethod
    def validate_expiry_hours(cls, v):
        """Ensure expiry hours is positive."""
        if v <= 0:
            raise ValueError("funding_proposal_expiry_hours must be positive")
        return v

    @field_validator("n8n_webhook_url")
    @classmethod
    def validate_n8n_webhook_url(cls, v, info):
        """Validate n8n webhook URL when funding proposals are enabled."""
        if info.data and info.data.get("funding_proposal_enabled", False):
            if not v or not v.startswith(("http://", "https://")):
                raise ValueError("n8n_webhook_url must be a valid HTTP/HTTPS URL when funding_proposal_enabled is True")
        return v

    @field_validator("webhook_server_port")
    @classmethod
    def validate_webhook_port(cls, v):
        """Ensure webhook server port is valid."""
        if not (1 <= v <= 65535):
            raise ValueError("webhook_server_port must be between 1 and 65535")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def bitcoind_url(self) -> str:
        """Get Bitcoin Knots RPC URL."""
        return f"{self.bitcoind_scheme}://{self.bitcoind_host_ip}:{self.bitcoind_port}"

    @property
    def electrs_url(self) -> str:
        """Get Electrs base URL."""
        return f"{self.electrs_scheme}://{self.electrs_host_ip}:{self.electrs_port}"

    @property
    def lnbits_url(self) -> str:
        """Get LNbits base URL."""
        return f"{self.lnbits_scheme}://{self.lnbits_host_ip}:{self.lnbits_port}"
