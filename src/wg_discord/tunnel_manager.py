import ipaddress
import logging
import shlex
import subprocess  # nosec B404
from pathlib import Path

import lightbulb
from wgconfig import WGConfig

from wg_discord.settings import get_wireguard_config, settings
from wg_discord.wg_control import hot_reload_wgconf

log = logging.getLogger(__name__)


class ConfigGenError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TunnelManager:
    def __init__(self):
        self.wg_config = get_wireguard_config(settings.wireguard_config_filepath)

    def get_claimed_ips(self) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """
        Collect IPs defined in WireGuard settings

        :return set[ipaddress.IPv4Address | ipaddress.IPv6Address]: all currently assigned IPs
        """
        claimed_ips = set()
        for _, v in self.wg_config.peers.items():
            claimed_ips.update(ipaddress.ip_network(v.get("AllowedIPs")).hosts())

        return claimed_ips

    def get_an_available_ip(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        """
        Calculates and returns an available IP address.

        :return ipaddress.IPv4Address | ipaddress.IPv6Address: Unclaimed ip address
        """
        reserved_ips = set().union(
            *[set(x) for x in settings.guild_interface_reserved_network_addresses]
        )

        available_ips = (
            set(settings.guild_ip_interface.network.hosts())
            - reserved_ips
            - self.get_claimed_ips()
        )

        if not available_ips:
            msg = "No IPs available!"
            log.error(msg)
            raise ConfigGenError(msg)

        return available_ips.pop()

    async def generate_user_config(
        self, user_id: str, user_address: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> None:
        """
        Creates config file for the user to connect to the Guild endpoint.

        :param user_id: Requesting Discord user's UUID
        :param user_address: IP address assigned to the user
        :return None:
        """
        wg_conf_filepath = Path(settings.wireguard_config_dir) / user_id
        try:
            user_conf = WGConfig(wg_conf_filepath)
        except PermissionError as e:
            raise e

        user_conf.add_attr(None, "Address", user_address)

        user_conf.add_peer(settings.guild_public_key)
        user_conf.add_attr(
            settings.guild_public_key,
            "AllowedIPs",
            ",".join(map(str, settings.user_allowed_ips)),
        )
        user_conf.add_attr(
            settings.guild_public_key, "Endpoint", settings.user_endpoint
        )

        user_conf.write_file()
        # Remove leading "[Interface]" line
        with open(wg_conf_filepath, "r") as wg:
            contents = wg.read().splitlines(True)
        with open(wg_conf_filepath, "w") as wg:
            wg.writelines(contents[1:])
        log.info(f"Wrote conf file for {user_id}")

    async def verify_user_owns_key(
        self, ctx: lightbulb.Context, user_id: str, key: str
    ) -> bool:
        """
        Verify that <key> belongs to <user>.
        We don't want a user to be able to take over an existing connection.

        :param ctx: Discord context used to send messages to user
        :param user_id: Requesting Discord user's UUID
        :param key: Requested WireGuard key for the user
        :return bool:
        """
        if (
            peer_id := self.wg_config.get_peer(key, include_details=True).get(
                "_rawdata"
            )[0]
        ) and peer_id.startswith("#"):
            if peer_id[1::] == user_id:
                await ctx.author.send("Your public key is already configured.")
                return True
            else:
                log.warning(
                    f'User "{user_id}" provided Key "{key}" that was already in use.'
                )
                await ctx.author.send(
                    "ERROR: Key pair may already be in use, regenerate a new key pair and try again."
                )
        else:
            log.error(
                f"Unable to parse config for user {user_id}, config may have been modified by a different tool."
            )

        return False

    async def process_registration(
        self, ctx: lightbulb.Context, user_id: str, key: str
    ) -> None:
        """
        Updates Guild's Wireguard config for valid user requests, and creates/sends User Wireguard config if possible.

        :param ctx: Discord context used to send messages to user
        :param user_id: Requesting Discord user's UUID
        :param key: Requested WireGuard key for the user
        :return None:
        """
        if key in self.wg_config.peers:
            key_is_approved = await self.verify_user_owns_key(ctx, user_id, key)
        else:
            # Remove previous user peer configuration and create new one
            for peer_entry, peer_conf in self.wg_config.peers.items():
                if peer_conf.get("_rawdata")[0][1::] == user_id:
                    # Remove IP from route table
                    subprocess.run(
                        shlex.split(
                            f"/sbin/ip route delete {shlex.quote(peer_conf.get('AllowedIPs'))} dev {shlex.quote(Path(settings.wireguard_config_filename).stem)}"
                        )
                    )  # nosec B603

                    self.wg_config.del_peer(peer_entry)
                    break

            try:
                user_address = self.get_an_available_ip()
            except ConfigGenError as e:
                await ctx.author.send(
                    f"Error during WireGuard Config generation, notify server admin: {e}"
                )
                return

            self.wg_config.add_peer(key, f"#{user_id}")
            self.wg_config.add_attr(
                key, "AllowedIPs", ipaddress.ip_network(user_address)
            )

            self.wg_config.write_file()

            try:
                await self.generate_user_config(user_id, user_address)
            except PermissionError as e:
                await ctx.author.send("ERROR: Unable to retrieve your configuration.")
                log.error(e)
                return

            # Update host route table with new IP
            subprocess.run(
                shlex.split(
                    f"/sbin/ip route add {user_address} dev {shlex.quote(Path(settings.wireguard_config_filename).stem)}"
                )
            )  # nosec B603

            key_is_approved = True

        if key_is_approved:
            hot_reload_wgconf()
            await ctx.author.send(
                "Key registration successful!\n\
                Add the following lines to your tunnel config below your [Interface]'s PrivateKey:"
            )
            try:
                with open(Path(settings.wireguard_config_dir) / user_id) as f:
                    await ctx.author.send(f.read())
            except PermissionError as e:
                self.wg_config.del_peer(key)
                await ctx.author.send("ERROR: Unable to retrieve your configuration.")
                log.error(e)
