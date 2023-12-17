import os
from typing import Optional
from database import db
from database import collection

import dotenv
import hikari
import lightbulb
import asyncio
import pymongo
from pymongo import MongoClient
from sympy import sympify
from lightbulb.ext import tasks
from hikari import Intents
from hikari import Snowflake

dotenv.load_dotenv()

INTENTS = Intents.GUILD_MEMBERS | Intents.GUILDS | Intents.DM_MESSAGES | Intents.GUILD_MESSAGES | Intents.MESSAGE_CONTENT | Intents.GUILD_MESSAGE_REACTIONS

bot = lightbulb.BotApp(
    os.environ["BOT_TOKEN"],
    prefix="!",
    intents=INTENTS,
    banner=None,
)
tasks.load(bot)

bot.load_extensions_from("./extensions/")

@tasks.task(m=6, auto_start=True)
async def collect_mesages():
    guild = await bot.rest.fetch_guild(826405737093136434)
    for channel_id in [826405737093136437, 1061281533681475614, 1001391150705418300, 1119261381745709127, 934755735311638599, 1062553300899217478, 1064690093438283886, 1087215587031257138, 1121479899841044510, 1147008618894471188]:
        
        channel = await bot.rest.fetch_channel(channel_id)
        
        if channel and isinstance(channel, hikari.GuildTextChannel):
            # Fetch all messages in the channel
            last_saved_message = collection.find_one({"channel_id": channel_id}, sort=[("_id", -1)])
            start_message_id = last_saved_message["message_id"] if last_saved_message else None
            messages = await bot.rest.fetch_messages(channel, after=start_message_id)

            # Save message data to MongoDB
            for message in messages:
                try:
                    member = await bot.rest.fetch_member(guild, message.author.id)
                    message_data = {
                        "message_id": message.id,
                        "author_id": message.author.id,
                        "author_username": message.author.username,
                        "author_display_name": member.display_name,
                        "content": message.content,
                        "timestamp": message.created_at,
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                    }
                    collection.insert_one(message_data)
                except hikari.errors.NotFoundError:
                    member = "Unknown User"
                    message_data = {
                        "message_id": message.id,
                        "author_id": message.author.id,
                        "author_username": message.author.username,
                        "author_display_name": member,
                        "content": message.content,
                        "timestamp": message.created_at,
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                    }
                    collection.insert_one(message_data)
                    # Insert or update the document in MongoDB
                #    await collection.replace_one({"message_id": message_data["message_id"]}, message_data, upsert=True)
            
        
@bot.command
@lightbulb.command("ping", description="The bot's ping.")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond(f"Pong! Latency: {bot.heartbeat_latency * 1000:.2f}ms.")

@bot.command
@lightbulb.option(
    "ping", "User to ping. Don't abuse.", type=hikari.User, required=False
)
@lightbulb.option(
    "attachment", "Attachment to add.", type=hikari.Attachment, required=False
)
@lightbulb.option(
    "channel", "Channel to post message to.", type=hikari.TextableChannel
)
@lightbulb.option("message", "The message to announce.", type=str)
@lightbulb.command("wordsinmymouth", "Make DUM-E say whatever you want!", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def wordsinmymouth(
    ctx: lightbulb.SlashContext,
    message: str,
    channel: hikari.GuildTextChannel,
    attachment: Optional[hikari.Attachment] = None,
    ping: Optional[hikari.User] = None,
) -> None:

    await ctx.app.rest.create_message(
        channel=channel.id,
        content=f"{ping.mention if ping else ''} {message}",
        attachment=attachment if attachment else hikari.UNDEFINED,
        user_mentions=True,
    )

    await ctx.respond(
        f"Message posted to <#{channel.id}>!", flags=hikari.MessageFlag.EPHEMERAL
    )
    
@bot.command
@lightbulb.option("expression", description="The equation you want to calculate.", type=str)
@lightbulb.command("calculate", description="Calculate an equation.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def calculate(ctx: lightbulb.SlashContext, expression = str) -> None:
    try:
        result = sympify(expression)
        await ctx.respond(f"{expression} is equal to {result}")
    except Exception as e:
        await ctx.respond(f"Error: {e}")

@bot.command
@lightbulb.option("time", description="How long you want to wait for the reminder.", type=int)
@lightbulb.option("unit", description="The unit of time to wait.", type=str, choices=["seconds", "minutes", "hours", "days"])
@lightbulb.option("message", description="The message you want for the reminder.", type=str)
@lightbulb.command("remindme", description="Get reminded about something after a specified amount of time. The message will appear in your DMs.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def remindme(
    ctx: lightbulb.Context,
    time = int,
    unit = str,
    message = str) -> None:
    
    channel = await bot.rest.fetch_channel(ctx.channel_id)
    
    unit_multipliers = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
    if unit.lower() not in unit_multipliers:
        await ctx.respond("Invalid unit. Please choose from: seconds, minutes, hours, days.")
        return
        
    time_in_seconds = time * unit_multipliers[unit.lower()]
    
    response = await ctx.respond(f'Got it! You will be remind with "{message}" in {time} {unit}.', flags=hikari.MessageFlag.EPHEMERAL)
    original_message = await response.message()
    message_id = original_message.id
    message_link = f"https://discord.com/channels/{ctx.guild_id}/{ctx.channel_id}/{message_id}"
    
    await asyncio.sleep(time_in_seconds)
    
    await ctx.author.send(f"Your reminder: {message}, which was in this channel: <#{channel.id}>. Link: {message_link}")
    
@bot.listen(hikari.ReactionAddEvent)
async def on_reaction_create(event: hikari.ReactionAddEvent) -> None:
    
    user = await bot.rest.fetch_user(event.user_id)
    
    if user.is_bot:
        return
       
    if isinstance(event.guild_id, hikari.Snowflake):
        try:
            # Fetch the message
            message = await bot.rest.fetch_message(event.channel_id, event.message_id)

            # Get the emoji that the user added
            emoji = event.emoji_name
            emoji_id = event.emoji_id
            emoji_type = message.reactions
            for i in emoji_type:
                emoji_type = i.emoji

            # Add the same reaction as the user
            if isinstance(emoji_type, hikari.CustomEmoji):
                await message.add_reaction(emoji, emoji_id)
            else:
                await message.add_reaction(emoji)
                
        except hikari.errors.ForbiddenError:
            # Bot does not have permission to add reactions
            pass
        except hikari.errors.NotFoundError:
            # Message not found
            pass

if __name__ == "__main__":
    bot.run()