import os
import shlex
import subprocess  # nosec B404

def hot_reload_wgconf(wireguard_config_path):
    conf_file = os.path.basename(os.path.splitext(wireguard_config_path)[0])
    proc_str = "wg syncconf {0} <(wg-quick strip {0})".format(shlex.quote(conf_file))
    try:
        subprocess.run(  # nosec B602
            proc_str, shell=True, executable="/bin/bash", check=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
