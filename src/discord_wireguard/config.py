import base64
import binascii
import ipaddress
import logging
import shlex
from typing import Any, List, Optional

from pydantic import (
    BaseSettings,
    DirectoryPath,
    Field,
    FilePath,
    IPvAnyNetwork,
    validator,
)
from pydantic.fields import ModelField

log = logging.getLogger(__name__)


class WireGuardSettings(BaseSettings):
    # Discord
    bot_token: str

    # Discord Guild/Server WireGuard vars
    # Required
    wireguard_config_path: str
    wireguard_user_config_dir: str
    guild_private_key: str = Field(..., min_length=44, max_length=44)
    guild_public_key: str = Field(..., min_length=44, max_length=44)
    guild_interface_address: IPvAnyNetwork = Field(...)
    guild_interface_listen_port: int = Field(..., ge=1, le=65535)
    # Optional
    guild_save_config: bool = Field(default=False)
    guild_interface_reserved_network_addresses: Optional[List[IPvAnyNetwork]]
    guild_interface_dns: Optional[List[IPvAnyNetwork]]
    # TODO guild_interface_table:
    # TODO guild_interface_mtu:
    guild_pre_up: Optional[str]
    guild_post_up: Optional[str]
    guild_pre_down: Optional[str]
    guild_post_down: Optional[str]

    # Discord User Wireguard vars
    # Required
    user_endpoint: str
    user_allowed_ips: List[IPvAnyNetwork]
    # Optional
    # TODO user_persistent_keep_alive:

    @validator("guild_save_config", pre=True)
    def cover_guild_save_config_empty(cls, v):  # noqa: B902
        if str(v).lower() != "true":
            return False
        return v

    @validator("*")
    def shell_safe(cls, v: Any, field: ModelField) -> Any:  # noqa: B902
        if field.type_ is str:
            return shlex.quote(v)
        return v

    @validator("guild_private_key", "guild_public_key")
    def check_key(cls, key: str) -> str:  # noqa: B902
        try:
            if len(base64.b64decode(key)) == 32:
                return key
            else:
                raise ValueError(f"Invalid WireGuard key {key}, unable to start.")
        except binascii.Error:
            raise ValueError(  # noqa: B904
                f"Invalid WireGuard key {key}, unable to start."
            )

    @validator("user_endpoint")
    def check_endpoint(cls, endpoint: str) -> str:  # noqa: B902
        tokens = endpoint.split(":", 1)
        if 0 < int(tokens[1]) <= 65535:
            return endpoint
        else:
            raise ValueError(
                f"Invalid endpoint string [{endpoint}], make sure the format is <hostname/ip>:<port>"
            )

    class Config:
        @classmethod
        def cast_ip(
            cls, raw_ip: str
        ) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
            try:
                return ipaddress.ip_network(raw_ip, strict=False)
            except ValueError:
                log.error(
                    f"Unable to cast {raw_ip} as IPv6, verify the value is a valid network address."
                )
            return None

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name in (
                "guild_interface_reserved_network_addresses",
                "guild_interface_dns",
                "user_allowed_ips",
            ):
                # Cast each list member and create list of valid IPs
                return [
                    ip
                    for raw_ip in raw_val.strip().split(",")
                    if (ip := cls.cast_ip(raw_ip.strip())) is not None
                ]
            return cls.json_loads(raw_val)

        env_prefix = ""
        case_sensitive = False
        env_file = "../../.env"
        env_file_encoding = "utf-8"


conf = WireGuardSettings()