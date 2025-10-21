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
    allowed_destinations: List[str] = Field(
        default_factory=list, env="ALLOWED_DESTINATIONS"
    )

    # Wallet Configuration
    change_address: Optional[str] = Field(default=None, env="CHANGE_ADDRESS")

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

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
