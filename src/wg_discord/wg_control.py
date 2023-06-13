import shlex
import subprocess  # nosec B404
from pathlib import Path

from wgconfig import WGConfig
from wgconfig.wgexec import generate_keypair

from wg_discord.settings import get_wireguard_config, settings


def initialize_wireguard_config():
    Path(settings.wireguard_config_dir).mkdir(
        parents=True, exist_ok=True
    )
    try:
        guild_conf = WGConfig(settings.wireguard_config_filepath)
    except PermissionError as e:
        raise e

    if not settings.guild_private_key:
        settings.guild_private_key, settings.guild_public_key = generate_keypair()

    guild_conf.initialize_file()
    guild_conf.add_attr(None, "Address", settings.guild_ip_interface.ip)
    guild_conf.add_attr(None, "ListenPort", settings.guild_interface_listen_port)
    guild_conf.add_attr(None, "PrivateKey", settings.guild_private_key)
    # if settings.guild_interface_dns:
    #     guild_conf.add_attr(None, "DNS", settings.guild_interface_dns)
    # if settings.guild_interface_table:
    #     guild_conf.add_attr(None, "Table", settings.guild_interface_table)
    # if settings.guild_interface_mtu:
    #     guild_conf.add_attr(None, "MTU", settings.guild_interface_mtu)
    # if settings.guild_pre_up and settings.guild_pre_up != "":
    #     guild_conf.add_attr(None, "PreUp", settings.guild_pre_up)
    if settings.guild_post_up and settings.guild_post_up != "":
        guild_conf.add_attr(None, "PostUp", settings.guild_post_up[1:-1])
    # if settings.guild_pre_down and settings.guild_pre_down != "":
    #     guild_conf.add_attr(None, "PreDown", settings.guild_pre_down)
    if settings.guild_post_down and settings.guild_post_down != "":
        guild_conf.add_attr(None, "PostDown", settings.guild_post_down[1:-1])

    guild_conf.write_file()


def update_wireguard_config_private_key(key):
    if not key:
        return

    try:
        guild_conf = get_wireguard_config(settings.wireguard_config_filepath)
    except PermissionError as e:
        raise e

    guild_conf.del_attr(None, "PrivateKey")
    guild_conf.add_attr(None, "PrivateKey", key)
    guild_conf.write_file()


def start_wireguard():
    proc_str = "wg-quick up {0}".format(shlex.quote(settings.wireguard_config_filepath))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)


def stop_wireguard():
    proc_str = "wg-quick down {0}".format(shlex.quote(settings.wireguard_config_filepath))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)


def hot_reload_wgconf():
    proc_str = "wg syncconf {0} <(wg-quick strip {0})".format(shlex.quote(settings.wireguard_config_filepath))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
