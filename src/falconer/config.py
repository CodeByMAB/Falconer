"""Configuration management for Falconer."""

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Main configuration class for Falconer."""

    # Environment
    env: str = Field(default="dev")

    # Bitcoin Knots / Core RPC
    bitcoind_scheme: str = Field(default="http")
    bitcoind_host_local: str = Field(default="127.0.0.1")
    bitcoind_host_ip: str = Field(default="127.0.0.1")
    bitcoind_port: int = Field(default=8332)
    bitcoind_rpc_user: str = Field(default="bitcoin")
    bitcoind_rpc_pass: str = Field(default="")

    # Bitcoin extra
    bitcoind_no_port: bool = Field(default=False)
    bitcoind_use_tor: bool = Field(default=False)

    # Electrs
    electrs_scheme: str = Field(default="http")
    electrs_host_local: str = Field(default="127.0.0.1")
    electrs_host_ip: str = Field(default="127.0.0.1")
    electrs_port: int = Field(default=3002)
    electrs_use_tor: bool = Field(default=False)
    # "" = direct Electrs REST; "/api" = Mempool/Esplora compatible
    electrs_api_prefix: str = Field(default="")

    # Tor
    tor_socks_proxy: str = Field(default="socks5://127.0.0.1:9050")

    # Mempool
    mempool_base_url: str = Field(default="https://mempool.space")
    mempool_use_tor: bool = Field(default=False)

    # LNbits
    lnbits_scheme: str = Field(default="http")
    lnbits_host_local: str = Field(default="127.0.0.1")
    lnbits_host_ip: str = Field(default="127.0.0.1")
    lnbits_port: int = Field(default=5000)
    lnbits_no_port: bool = Field(default=False)
    lnbits_api_key: str = Field(default="")
    lnbits_wallet_id: str = Field(default="")

    # Wallet
    change_address: Optional[str] = Field(default=None)

    # Policy
    policy_path: str = Field(default="policy/dev.policy.json")

    # Spending limits (overridable by policy file)
    max_daily_spend_sats: int = Field(default=100000)
    max_single_tx_sats: int = Field(default=50000)
    allowed_destinations: List[str] = Field(default=[])

    # AI — vLLM (OpenAI-compatible API)
    vllm_model: str = Field(default="llama3.1:8b")
    vllm_base_url: str = Field(default="http://localhost:8000/v1")
    vllm_api_key: str = Field(default="")
    ai_risk_tolerance: str = Field(default="medium")
    ai_confidence_threshold: float = Field(default=0.6)
    ai_decision_interval_minutes: int = Field(default=5)

    # AI — Ollama (legacy / alternative backend)
    ollama_model: str = Field(default="llama3.1:8b")
    ollama_host: str = Field(default="http://localhost:11434")

    # Funding proposals
    funding_proposal_enabled: bool = Field(default=False)
    funding_proposal_threshold_sats: int = Field(default=50000)
    funding_proposal_default_amount_sats: int = Field(default=100000)
    funding_proposal_max_pending: int = Field(default=3)
    funding_proposal_expiry_hours: int = Field(default=24)

    # n8n integration
    n8n_base_url: Optional[str] = Field(default=None)
    n8n_api_key: Optional[str] = Field(default=None)
    n8n_webhook_url: Optional[str] = Field(default=None)
    n8n_webhook_auth_token: Optional[str] = Field(default=None)
    n8n_webhook_secret: Optional[str] = Field(default=None)
    n8n_webhook_timeout_seconds: int = Field(default=30)

    # Webhook server
    webhook_server_enabled: bool = Field(default=True)
    webhook_server_host: str = Field(default="0.0.0.0")
    webhook_server_port: int = Field(default=8080)
    webhook_server_reload: bool = Field(default=False)

    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default=None)

    # OpenClaw integration (PoC)
    openclaw_enabled: bool = Field(default=False)
    openclaw_api_key: str = Field(default="")
    openclaw_webhook_url: str = Field(default="")

    # Dashboard credentials
    dashboard_user: str = Field(default="admin")
    dashboard_password: str = Field(default="falconer")

    # Setup wizard completion flag
    setup_complete: bool = Field(default=False)

    # ── Validators ────────────────────────────────────────────────────

    @field_validator("max_single_tx_sats")
    @classmethod
    def single_tx_less_than_daily(cls, v: int, info: object) -> int:
        data = getattr(info, "data", {})
        if data and "max_daily_spend_sats" in data and v > data["max_daily_spend_sats"]:
            raise ValueError(
                "max_single_tx_sats must be <= max_daily_spend_sats"
            )
        return v

    @field_validator("allowed_destinations", mode="before")
    @classmethod
    def parse_allowed_destinations(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return list(v) if v else []

    @field_validator("funding_proposal_threshold_sats")
    @classmethod
    def validate_funding_threshold(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("funding_proposal_threshold_sats must be positive")
        return v

    @field_validator("funding_proposal_default_amount_sats")
    @classmethod
    def validate_funding_default_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("funding_proposal_default_amount_sats must be positive")
        return v

    @field_validator("funding_proposal_max_pending")
    @classmethod
    def validate_max_pending(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("funding_proposal_max_pending must be positive")
        return v

    @field_validator("funding_proposal_expiry_hours")
    @classmethod
    def validate_expiry_hours(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("funding_proposal_expiry_hours must be positive")
        return v

    @field_validator("webhook_server_port")
    @classmethod
    def validate_webhook_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("webhook_server_port must be between 1 and 65535")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # ── Computed URL properties ───────────────────────────────────────

    @property
    def bitcoind_url(self) -> str:
        if self.bitcoind_no_port:
            return f"{self.bitcoind_scheme}://{self.bitcoind_host_ip}"
        return f"{self.bitcoind_scheme}://{self.bitcoind_host_ip}:{self.bitcoind_port}"

    @property
    def bitcoin_rpc_host(self) -> str:
        return self.bitcoind_host_ip

    @property
    def bitcoin_rpc_port(self) -> int:
        return self.bitcoind_port

    @property
    def bitcoin_rpc_user(self) -> str:
        return self.bitcoind_rpc_user

    @property
    def electrs_url(self) -> str:
        return f"{self.electrs_scheme}://{self.electrs_host_ip}:{self.electrs_port}"

    @property
    def mempool_url(self) -> str:
        return self.mempool_base_url.rstrip("/") + "/api"

    @property
    def lnbits_url(self) -> str:
        if self.lnbits_no_port:
            return f"{self.lnbits_scheme}://{self.lnbits_host_ip}"
        return f"{self.lnbits_scheme}://{self.lnbits_host_ip}:{self.lnbits_port}"

    @property
    def llm_base_url(self) -> str:
        return self.vllm_base_url

    @property
    def llm_model(self) -> str:
        return self.vllm_model
