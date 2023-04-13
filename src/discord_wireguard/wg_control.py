import os
import shlex
import subprocess  # nosec B404
from pathlib import Path

from wgconfig import WGConfig

from discord_wireguard.config import conf


def initialize_wireguard_config():
    Path(os.path.dirname(conf.wireguard_config_path)).mkdir(parents=True, exist_ok=True)
    try:
        guild_conf = WGConfig(conf.wireguard_config_path)
    except PermissionError as e:
        raise e

    guild_conf.initialize_file()
    guild_conf.add_attr(None, "Address", conf.guild_interface_address)
    guild_conf.add_attr(None, "ListenPort", conf.guild_interface_listen_port)
    guild_conf.add_attr(None, "PrivateKey", conf.guild_private_key)
    # if conf.guild_interface_dns:
    #     guild_conf.add_attr(None, "DNS", conf.guild_interface_dns)
    # if conf.guild_interface_table:
    #     guild_conf.add_attr(None, "Table", conf.guild_interface_table)
    # if conf.guild_interface_mtu:
    #     guild_conf.add_attr(None, "MTU", conf.guild_interface_mtu)
    # if conf.guild_pre_up and conf.guild_pre_up != "":
    #     guild_conf.add_attr(None, "PreUp", conf.guild_pre_up)
    # if conf.guild_post_up and conf.guild_post_up != "":
    #     guild_conf.add_attr(None, "PostUp", conf.guild_post_up)
    # if conf.guild_pre_down and conf.guild_pre_down != "":
    #     guild_conf.add_attr(None, "PreDown", conf.guild_pre_down)
    # if conf.guild_post_down and conf.guild_post_down != "":
    #     guild_conf.add_attr(None, "PostDown", conf.guild_post_down)

    guild_conf.write_file()


def start_wireguard():
    conf_file = os.path.basename(os.path.splitext(conf.wireguard_config_path)[0])
    proc_str = "wg-quick up {0}".format(shlex.quote(conf_file))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)


def hot_reload_wgconf():
    conf_file = os.path.basename(os.path.splitext(conf.wireguard_config_path)[0])
    proc_str = "wg syncconf {0} <(wg-quick strip {0})".format(shlex.quote(conf_file))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
