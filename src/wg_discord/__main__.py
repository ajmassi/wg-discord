import asyncio
import base64
import binascii
import logging
from pathlib import Path
from sys import exit

import hikari
import lightbulb

from wg_discord import tunnel_manager
from wg_discord.settings import settings
from wg_discord.wg_control import (
    initialize_wireguard_config,
    start_wireguard,
    stop_wireguard,
    update_wireguard_config_private_key,
)

log = logging.getLogger(__name__)
bot = lightbulb.BotApp(
    token=settings.bot_token,
    intents=hikari.Intents.GUILD_MESSAGES | hikari.Intents.DM_MESSAGES,
)


class KeyValidationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


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

        t_manager_instance = tunnel_manager.TunnelManager()
        await t_manager_instance.process_registration(
            ctx, ctx.user.id.__str__(), ctx.options.key
        )

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


def main():
    if not Path(settings.wireguard_config_filepath).exists():
        initialize_wireguard_config()
    else:
        update_wireguard_config_private_key(settings.guild_private_key)

    start_wireguard()

    try:
        bot.run()
    finally:
        stop_wireguard()
        exit()


if __name__ == "__main__":
    main()
