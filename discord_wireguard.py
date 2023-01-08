import base64
import binascii
import os
import time

import lightbulb

bot = lightbulb.BotApp(token=os.environ["BOT_TOKEN"])


def validate_public_key(key):
    # Best we can do here for input validation is check that our received key is a 32-byte string
    if key is not None and len(base64.b64decode(key)) != 32:
        raise ValueError(f"Provided value [{key}] is not a valid Wireguard Public Key.")


@bot.command()
@lightbulb.option("key", "Your Wireguard Public Key")
@lightbulb.command("register", "Register yourself with the Wireguard tunnel.")
@lightbulb.implements(lightbulb.SlashCommand)
async def echo(ctx: lightbulb.Context) -> None:
    try:
        validate_public_key(ctx.options.key)
        await ctx.author.send(ctx.options.key)
    except binascii.Error:
        await ctx.author.send("ERROR: Invalid Wireguard Public Key")
    except ValueError as e:
        await ctx.author.send(f"ERROR: {e}")
    finally:
        await ctx.respond("Thanks for registering!\nReply sent to your DMs.")
        time.sleep(5)
        await ctx.delete_last_response()


bot.run()
