import asyncio
import base64
import binascii
import ipaddress
import logging
import os

import hikari
import lightbulb
import wgconfig

import wg_control
from config import conf

log = logging.getLogger(__name__)
bot = lightbulb.BotApp(
    token=conf.bot_token,
    intents=hikari.Intents.GUILD_MESSAGES | hikari.Intents.DM_MESSAGES,
)
wg_config = wgconfig.WGConfig(conf.wireguard_config_path)
wg_config.read_file()


class KeyValidationError(Exception):
    def __init(self, message):
        self.message = message
        super().__init__(self.message)


class ConfigGenError(Exception):
    def __init(self, message):
        self.message = message
        super().__init__(self.message)


def get_an_available_ip() -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """
    Calculates and returns an available IP address.

    :return ipaddress.IPv4Address | ipaddress.IPv6Address: Unclaimed ip address
    """
    reserved_ips = set().union(
        *[set(x) for x in conf.guild_interface_reserved_network_addresses]
    )

    # Collect IPs defined in WireGuard conf
    claimed_ips = set()
    for _, v in wg_config.peers.items():
        claimed_ips.update(ipaddress.ip_network(v.get("AllowedIPs")).hosts())

    available_ips = (
        set(conf.guild_interface_address.hosts()) - reserved_ips - claimed_ips
    )

    if not available_ips:
        msg = "No IPs available!"
        log.error(msg)
        raise ConfigGenError(msg)

    return available_ips.pop()


async def validate_public_key(key: str) -> None:
    """
    Check key decodes and is of expected length for a WireGuard key (32 bytes).

    :param key: Requested WireGuard key for the user
    :return:
    """
    try:
        if key is not None and len(base64.b64decode(key)) != 32:
            raise KeyValidationError(f'Invalid WireGuard public key "{key}"')
    except binascii.Error as e:
        raise KeyValidationError(f'Invalid WireGuard public key "{key}"') from e


async def generate_user_config(
    user_id: str, user_address: ipaddress.IPv4Address | ipaddress.IPv6Address
) -> None:
    """
    Creates config file for the user to connect to the Guild endpoint.

    :param user_id: Requesting Discord user's UUID
    :param user_address: IP address assigned to the user
    :return None:
    """
    wg_conf_filepath = os.path.join(conf.wireguard_user_config_dir, user_id)
    try:
        user_conf = wgconfig.WGConfig(wg_conf_filepath)
    except PermissionError as e:
        raise e

    user_conf.add_attr(None, "Address", user_address)

    user_conf.add_peer(conf.guild_public_key)
    user_conf.add_attr(
        conf.guild_public_key, "AllowedIPs", ",".join(map(str, conf.user_allowed_ips))
    )
    user_conf.add_attr(conf.guild_public_key, "Endpoint", conf.user_endpoint)

    user_conf.write_file()
    # Remove leading "[Interface]" line
    with open(wg_conf_filepath, 'r') as wg:
        contents = wg.read().splitlines(True)
    with open(wg_conf_filepath, 'w') as wg:
        wg.writelines(contents[1:])
    log.info(f"Wrote conf file for {user_id}")


async def verify_registered_key(ctx: lightbulb.Context, user_id: str, key: str) -> bool:
    """
    Verify that a registered key belongs to the requesting user.
    We don't want a user to be able to take over an existing connection.

    :param ctx: Discord context used to send messages to user
    :param user_id: Requesting Discord user's UUID
    :param key: Requested WireGuard key for the user
    :return bool:
    """
    if (
        peer_id := wg_config.get_peer(key, include_details=True).get("_rawdata")[0]
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


async def process_registration(ctx: lightbulb.Context, user_id: str, key: str) -> None:
    """
    Updates Guild's Wireguard config for valid user requests, and creates/sends User Wireguard config if possible.

    :param ctx: Discord context used to send messages to user
    :param user_id: Requesting Discord user's UUID
    :param key: Requested WireGuard key for the user
    :return None:
    """
    if key in wg_config.peers:
        key_is_approved = await verify_registered_key(ctx, user_id, key)
    else:
        # Remove previous user peer configuration and create new one
        #   Don't necessarily need this if a robust timeout was implemented for keys, but this does prevent clutter
        for peer_entry, peer_conf in wg_config.peers.items():
            if peer_conf.get("_rawdata")[0][1::] == user_id:
                wg_config.del_peer(peer_entry)
                break

        try:
            user_address = get_an_available_ip()
        except ConfigGenError as e:
            await ctx.author.send(
                f"Error during WireGuard Config generation, notify server admin: {e}"
            )
            return

        wg_config.add_peer(key, f"#{user_id}")
        wg_config.add_attr(key, "AllowedIPs", ipaddress.ip_network(user_address))

        wg_config.write_file()

        try:
            await generate_user_config(user_id, user_address)
        except PermissionError as e:
            await ctx.author.send("ERROR: Unable to retrieve your configuration.")
            log.error(e)
            return

        key_is_approved = True

    if key_is_approved:
        wg_control.hot_reload_wgconf()
        await ctx.author.send("Add the following lines to your tunnel config below your [Interface]'s PrivateKey:")
        try:
            with open(os.path.join(conf.wireguard_user_config_dir, user_id)) as f:
                await ctx.author.send(f.read())
        except PermissionError as e:
            wg_config.del_peer(key)
            await ctx.author.send("ERROR: Unable to retrieve your configuration.")
            log.error(e)


@bot.command()
@lightbulb.option("key", "Your WireGuard public key")
@lightbulb.command("register", "Register yourself with the WireGuard tunnel.")
@lightbulb.implements(lightbulb.SlashCommand)
async def echo(ctx: lightbulb.Context) -> None:
    """
    Discord Bot command that takes a WireGuard public key and creates configuration file(s) to enable a connection.

    :param ctx: Discord context containing a Wireguard key
    :return None:
    """
    try:
        log.info(
            f'User "{ctx.user.id.__str__()}" attempting to register with Key "{ctx.options.key}"'
        )
        await validate_public_key(ctx.options.key)
        await process_registration(ctx, ctx.user.id.__str__(), ctx.options.key)
        log.info(
            f'User "{ctx.user.id.__str__()}" registered successfully with Key "{ctx.options.key}"'
        )
    except KeyValidationError as e:
        log.warning(f'User "{ctx.user.id.__str__()}" {e}')
        await ctx.author.send(f"ERROR: {e}")
    finally:
        await ctx.respond("Thanks for registering!\nReply sent to your DMs.")
        await asyncio.sleep(5)
        await ctx.delete_last_response()


bot.run()
