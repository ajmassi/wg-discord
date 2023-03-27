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
wg_config = wgconfig.WGConfig("./wg0.conf")
wg_config.read_file()


class KeyValidationError(Exception):
    def __init(self, message):
        self.message = message
        super().__init__(self.message)


async def get_available_ips():
    network = set()
    if os.getenv("GUILD_INTERFACE_ADDRESS"):
        network = ipaddress.ip_network("GUILD_INTERFACE_ADDRESS")
    else:
        raise ValueError("GUILD_INTERFACE_ADDRESS is required")

    reserved_ips = set()
    if os.getenv("GUILD_INTERFACE_RESERVED_NETWORK_ADDRESSES"):
        for ip in os.getenv("GUILD_INTERFACE_RESERVED_NETWORK_ADDRESSES").split(","):
            try:
                reserved_ips.update([ipaddress.ip_address(ip.strip())])
            except ValueError as e:
                log.warning(f"Invalid IP address in config file: {e}")

    # Collect IPs defined in WireGuard conf
    claimed_ips = set()
    for _, v in wg_config.peers.items():
        claimed_ips.update(ipaddress.ip_network(v.get("AllowedIPs")).hosts())

    return set(network.hosts()) - reserved_ips - claimed_ips


async def validate_public_key(key: str) -> None:
    # Best we can do here for input validation is check that our received key is a 32-byte string
    try:
        if key is not None and len(base64.b64decode(key)) != 32:
            raise KeyValidationError(f"Invalid WireGuard public key \"{key}\"")
    except binascii.Error as e:
        raise KeyValidationError(f"Invalid WireGuard public key \"{key}\"") from e


async def process_wireguard_config(
    ctx: lightbulb.Context, user_id: str, key: str
) -> None:
    config_created = False

    # Check if a different user already registered the provided key pair
    #  The intent is that we don't want a user to be able to take over an existing connection
    if key in wg_config.peers:
        if (
            peer_id := wg_config.get_peer(key, include_details=True).get("_rawdata")[0]
        ) and peer_id.startswith("#"):
            if peer_id[1::] == user_id:
                await ctx.author.send("Your public key is already configured.")
                config_created = True
            else:
                log.warning(f"User \"{user_id}\" provided Key \"{key}\" that was already in use.")
                await ctx.author.send(
                    "ERROR: This key pair may already be in use, regenerate a new key pair and try again."
                )
        else:
            # TODO work on error text, maybe also send alert to caller
            log.error(
                "Config appears to be modified or created by a different tool, cannot update"
            )
    else:
        # If the wg key is not already in use, check for and remove previous user configuration and create new one
        for k, v in wg_config.peers.items():
            if v.get("_rawdata")[0] == user_id:
                wg_config.del_peer(k)
                break

        wg_config.add_peer(key, f"#{user_id}")
        wg_config.add_attr(
            key,
            "Endpoint",
            "wg.example.com:51820",
            "# Added for demonstration purposes",
        )

        config_created = True

    if config_created:
        await ctx.author.send("Your client config: <#TODO>")


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
        await process_wireguard_config(ctx, ctx.user.id.__str__(), ctx.options.key)
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
