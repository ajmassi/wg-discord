import asyncio
import base64
import binascii
import ipaddress
import logging
import os

import hikari
import lightbulb
import wgconfig

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


def get_available_ip() -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Calculates and returns an available IP address"""
    reserved_ips = set().union(*[set(x) for x in conf.guild_interface_reserved_network_addresses])

    # Collect IPs defined in WireGuard conf
    claimed_ips = set()
    for _, v in wg_config.peers.items():
        claimed_ips.update(ipaddress.ip_network(v.get("AllowedIPs")).hosts())

    available_ips = set(conf.guild_interface_address.hosts()) - reserved_ips - claimed_ips

    if not available_ips:
        msg = "No IPs available!"
        log.error(msg)
        raise ConfigGenError(msg)

    return available_ips.pop()


async def validate_public_key(key: str) -> None:
    # Best we can do here for input validation is check that our received key is a 32-byte string
    try:
        if key is not None and len(base64.b64decode(key)) != 32:
            raise KeyValidationError(f"Invalid WireGuard public key \"{key}\"")
    except binascii.Error as e:
        raise KeyValidationError(f"Invalid WireGuard public key \"{key}\"") from e


async def generate_user_config(user_id: str, user_address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    user_conf = wgconfig.WGConfig(os.path.join(conf.wireguard_user_config_dir, user_id))
    user_conf.initialize_file()
    user_conf.add_attr(None, 'PrivateKey', '<Copy Private Key Here>')
    user_conf.add_attr(None, 'Address', user_address)
    user_conf.add_attr(None, 'ListenPort', conf.guild_interface_listen_port)

    user_conf.add_peer(conf.guild_public_key)
    user_conf.add_attr(
        conf.guild_public_key,
        "AllowedIPs",
        ','.join(map(str, conf.user_allowed_ips)),
    )
    user_conf.add_attr(
        conf.guild_public_key,
        "Endpoint",
        conf.user_endpoint,
    )

    user_conf.write_file()
    log.info(f"Wrote conf file for {user_id}")


async def verify_registered_key(ctx: lightbulb.Context, user_id: str, key: str) -> bool:
    """
    Verify that a registered key belongs to the requesting user.
    We don't want a user to be able to take over an existing connection.

    :param ctx:
    :param user_id:
    :param key:
    :return bool:
    """
    if (peer_id := wg_config.get_peer(key, include_details=True).get("_rawdata")[0]) and peer_id.startswith("#"):
        if peer_id[1::] == user_id:
            await ctx.author.send("Your public key is already configured.")
            return True
        else:
            log.warning(f"User \"{user_id}\" provided Key \"{key}\" that was already in use.")
            await ctx.author.send("ERROR: Key pair may already be in use, regenerate a new key pair and try again.")
    else:
        log.error(f"Unable to parse config for user {user_id}, config may have been modified by a different tool.")

    return False


async def process_registration(
    ctx: lightbulb.Context, user_id: str, key: str
) -> None:
    """
    Updates Guild's Wireguard config for valid user requests, and creates/sends User Wireguard config if possible.

    :param ctx:
    :param user_id:
    :param key:
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
            user_address = get_available_ip()
        except ConfigGenError as e:
            await ctx.author.send(f"Error during WireGuard Config generation, notify server admin: {e}")
            return

        wg_config.add_peer(key, f"#{user_id}")
        wg_config.add_attr(
            key,
            "Endpoint",
            conf.user_endpoint,
        )
        wg_config.add_attr(
            key,
            "AllowedIPs",
            ipaddress.ip_network(user_address),
        )

        wg_config.write_file()

        await generate_user_config(user_id, user_address)
        key_is_approved = True

    if key_is_approved:
        await ctx.author.send("Your client config:")
        try:
            with open(f"./{user_id}") as f:
                await ctx.author.send(f.read())
        except PermissionError as e:
            wg_config.del_peer(key)
            log.error(e)


@bot.command()
@lightbulb.option("key", "Your WireGuard public key")
@lightbulb.command("register", "Register yourself with the WireGuard tunnel.")
@lightbulb.implements(lightbulb.SlashCommand)
async def echo(ctx: lightbulb.Context) -> None:
    try:
        log.info(
            f"User \"{ctx.user.id.__str__()}\" attempting to register with Key \"{ctx.options.key}\""
        )
        await validate_public_key(ctx.options.key)
        await process_registration(ctx, ctx.user.id.__str__(), ctx.options.key)
        log.info(
            f"User \"{ctx.user.id.__str__()}\" registered successfully with Key \"{ctx.options.key}\""
        )
    except KeyValidationError as e:
        log.warning(f"User \"{ctx.user.id.__str__()}\" {e}")
        await ctx.author.send(f"ERROR: {e}")
    finally:
        await ctx.respond("Thanks for registering!\nReply sent to your DMs.")
        await asyncio.sleep(5)
        await ctx.delete_last_response()


bot.run()
