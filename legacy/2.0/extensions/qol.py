import re

import hikari
import lightbulb

qol_plugin = lightbulb.Plugin("Quality of Life")

def extract_message_ids(link):
    # Define the regex pattern for Discord message links
    pattern = re.compile(r'https?://discord\.com/channels/(\d+)/(\d+)/(\d+)')

    # Match the pattern in the provided link
    match = pattern.match(link)

    # Extract IDs if the link matches the pattern
    if match:
        guild_id, channel_id, message_id = map(int, match.groups())
        return guild_id, channel_id, message_id
    else:
        return None

@qol_plugin.command
@lightbulb.option("link", "The link of the message you want to get the reply from.", hikari.Message)
@lightbulb.command("getoriginal", "Get the replied message of the message link you send.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def getoriginal(ctx: lightbulb.SlashContext, link: hikari.Message) -> None:
    ids = extract_message_ids(link)
    guild_id, channel_id, message_id = ids
    guild = await ctx.app.rest.fetch_guild(guild_id)
    message = await ctx.app.rest.fetch_message(channel_id, message_id)
    message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    content = message.referenced_message.content
    if (message.referenced_message):
        await ctx.respond(f"The message this was replying to was this: \"{content}\" ([Link to reply]({message.referenced_message.make_link(guild)})). Link to linked message: {message_link}", attachments=message.referenced_message.attachments if message.referenced_message.attachments else None, flags=hikari.MessageFlag.EPHEMERAL | hikari.MessageFlag.SUPPRESS_EMBEDS)
    else:
        await ctx.respond(f"This message isn't replying to anything!", flags=hikari.MessageFlag.EPHEMERAL)

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(qol_plugin)