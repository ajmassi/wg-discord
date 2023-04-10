from base64 import b64encode
from hashlib import sha512

import pytest
from dotenv import dotenv_values
from pydantic import BaseSettings

from config import WireGuardSettings

base_env = {
    "bot_token": sha512(b"BOT_TOKEN").hexdigest(),
    "wireguard_config_path": ".env.example",
    "wireguard_user_config_dir": ".",
    "guild_private_key": b64encode(
        bytes(sha512(b"GUILD_PRIVATE_KEY").hexdigest()[:32].encode())
    ),
    "guild_public_key": b64encode(
        bytes(sha512(b"GUILD_PUBLIC_KEY").hexdigest()[:32].encode())
    ),
    "guild_interface_address": "0.0.0.0",
    "guild_interface_listen_port": "11111",
    "user_endpoint": "test.endpoint.local:14142",
    "guild_save_config": False,
    "guild_interface_reserved_network_addresses": None,
    "guild_interface_dns": None,
    # TODO "user_allowed_ips": None,
    # TODO "guild_interface_mtu": None,
    # TODO "guild_interface_table": None,
    # TODO "user_persistent_keep_alive": None
}


@pytest.mark.parametrize(
    "value", ["FALSE", "", None, False, "FaLsE", "kajsbfjkabskfjbs", 1241]
)
def test_false_guild_save_config(value):
    test_env = base_env
    test_env.update({"guild_save_config": value})
    print(test_env)
    config = WireGuardSettings(**test_env)
    assert config.guild_save_config is False


@pytest.mark.parametrize("value", ["True", "true", "TrUe", True])
def test_true_guild_save_config(value):
    test_env = base_env
    test_env.update({"guild_save_config": value})
    print(test_env)
    config = WireGuardSettings(**test_env)
    assert config.guild_save_config is True
