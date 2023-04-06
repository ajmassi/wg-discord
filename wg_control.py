import os
import shlex
import subprocess  # nosec B404

from config import conf


def hot_reload_wgconf():
    conf_file = os.path.basename(conf.wireguard_config_path)
    try:
        subprocess.run(  # nosec B603
            shlex.split(f"wg syncconf {conf_file} <(wg-quick strip {conf_file})"),
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(e)
