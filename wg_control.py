import os
import shlex
import subprocess  # nosec B404

from config import conf


def hot_reload_wgconf():
    conf_file = os.path.basename(os.path.splitext(conf.wireguard_config_path)[0])
    proc_str = "wg syncconf {0} <(wg-quick strip {0})".format(shlex.quote(conf_file))
    try:
        subprocess.run(  # nosec B603
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
