import inspect
import os

import pytest
import wgconfig
import wgconfig.wgexec

from wg_discord.__main__ import main
from wg_discord.config import get_wireguard_config, settings


def create_wg_config(wireguard_config_path, guild_private_key):
    """Helper function to generate WireGuard config"""
    wg_conf_content = inspect.cleandoc(
        f"""
    [Interface]
    Address = 192.168.1.1
    ListenPort = 51820
    PrivateKey = {guild_private_key}
    """
    )

    with open(wireguard_config_path, "w") as f:
        f.write(wg_conf_content)


def test_key_init_privkey_no_conf_yes():
    """
    Scenario:
        The env var "GUILD_PRIVATE_KEY" is not set and there is an existing wg.conf
        file

    Expectation:
        The settings.guild_private_key and settings.guild_public_key will populate upon
        validation, based on the key saved in our existing wg.conf
    """
    ### Setup ###
    # Create a wg-quick config with a new, random private key
    test_key = wgconfig.wgexec.generate_privatekey()
    create_wg_config(settings.wireguard_config_path, test_key)

    # Check that PrivateKey was set correctly in our wg.conf
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] == test_key

    ### Test ###
    # Force re-read and validation of settings with existing wg.conf
    settings.__init__()

    # Check that private key has not changed and public key is correct
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] == test_key
    assert settings.guild_public_key == wgconfig.wgexec.get_publickey(test_key)


def test_key_init_privkey_no_conf_no():
    """
    Scenario:
        The env var "GUILD_PRIVATE_KEY" is not set and there is no wg.conf file

    Expectation:
        The settings.guild_private_key and settings.guild_public_key will populate
        with new keys, and a wg.conf will be created with a matching PrivateKey
    """
    ### Setup ###
    # Check file does not exist yet
    assert not os.path.isfile(settings.wireguard_config_path)

    # Force re-read and validation of settings
    settings.__init__()

    ### Test ###
    # Start app
    with pytest.raises(SystemExit):
        main()

    # Check that file created and has key set correctly
    assert os.path.isfile(settings.wireguard_config_path)
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] == settings.guild_private_key


def test_key_init_privkey_yes_conf_yes():
    """
    Scenario:
        The env var "GUILD_PRIVATE_KEY" is set and there is an existing wg.conf file

    Expectation:
        The wg.conf will have its Interface's PrivateKey updated to match the value in
        settings.guild_private_key
    """
    ### Setup ###
    # Create "previous" WireGuard config with a unique private key
    create_wg_config(
        settings.wireguard_config_path, wgconfig.wgexec.generate_privatekey()
    )

    # Create private key for settings as well
    test_key = wgconfig.wgexec.generate_privatekey()
    os.environ["GUILD_PRIVATE_KEY"] = test_key
    # Force re-read and validation of settings
    settings.__init__()

    # Check initial settings.guild_private_key is unique from the one set in wg.conf
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] != settings.guild_private_key

    ### Test ###
    # Start app
    with pytest.raises(SystemExit):
        main()

    # Check that wg.conf has had its key updated has been updated
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] == settings.guild_private_key
    assert settings.guild_private_key == test_key


def test_key_init_privkey_yes_conf_no():
    """
    Scenario:
        The env var "GUILD_PRIVATE_KEY" is set and there is no wg.conf file

    Expectation:
        A wg.conf will be created with a PrivateKey to match settings.guild_private_key
    """
    ### Setup ###
    # Check file does not exist yet
    assert not os.path.isfile(settings.wireguard_config_path)

    # Create random new private key for settings
    test_key = wgconfig.wgexec.generate_privatekey()
    os.environ["GUILD_PRIVATE_KEY"] = test_key
    # Force re-read and validation of settings
    settings.__init__()

    ### Test ###
    # Start app
    with pytest.raises(SystemExit):
        main()

    # Check that file created and has key set correctly
    assert os.path.isfile(settings.wireguard_config_path)
    wg_config = get_wireguard_config(settings.wireguard_config_path)
    assert wg_config.interface["PrivateKey"] == settings.guild_private_key
    assert settings.guild_public_key == wgconfig.wgexec.get_publickey(test_key)
