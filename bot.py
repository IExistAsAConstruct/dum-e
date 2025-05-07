import os
from datetime import datetime, timezone

from dotenv import main
from pyexpat.errors import messages
import extensions.gambling
from database import collection, stocks, kek_counter
import asyncio
from typing import List, Dict, Any, Sequence

import hikari
from hikari import Intents
import lightbulb


main.load_dotenv()

INTENTS = Intents.GUILD_MEMBERS | Intents.GUILDS | Intents.DM_MESSAGES | Intents.GUILD_MESSAGES | Intents.MESSAGE_CONTENT | Intents.GUILD_MESSAGE_REACTIONS

bot = hikari.GatewayBot(os.getenv("BOT_TOKEN"), intents=INTENTS)
client = lightbulb.client_from_app(bot)

bot.subscribe(hikari.StartingEvent, client.start)

client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(hikari.GatewayBot, lambda: bot)
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(lightbulb.GatewayEnabledClient, lambda: client)

CHANNEL_IDS = [
    826405737093136437, 1061281533681475614, 1001391150705418300,
    1119261381745709127, 934755735311638599, 1062553300899217478,
    1064690093438283886, 1087215587031257138, 1121479899841044510,
    1147008618894471188, 1227892062222024744
]

@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    # Load any extensions
    print("Loading extensions...")
    await client.load_extensions("extensions.data", "extensions.gambling", "extensions.word_cloud", "extensions.meme", "extensions.word_game")
    extensions.gambling.initialize_stocks(stocks)
    extensions.gambling.check_stock_initialization(stocks)
    # Start the bot - make sure commands are synced properly
    await client.start()

async def process_messages(messages_got: Sequence[hikari.Message], guild: hikari.Guild, channel: hikari.GuildTextChannel) -> List[Dict[Any, Any]]:
    """Process a batch of messages concurrently"""
    async def get_message_data(message: hikari.Message) -> Dict[Any, Any]:
        try:
            member_got = await bot.rest.fetch_member(guild, message.author.id)
            display_name = member_got.display_name
        except hikari.NotFoundError:
            display_name = "Unknown User"

        return {
            "message_id": message.id,
            "author_id": message.author.id,
            "author_username": message.author.username,
            "author_display_name": display_name,
            "content": message.content,
            "timestamp": message.created_at,
            "channel_id": channel.id,
            "channel_name": channel.name
        }

    return await asyncio.gather(
        *(get_message_data(message) for message in messages_got)
    )

@client.task(lightbulb.uniformtrigger(minutes=6))
async def collect_messages() -> None:
    guild = await bot.rest.fetch_guild(826405737093136434)

    channels = await asyncio.gather(
        *(bot.rest.fetch_channel(channel_id) for channel_id in CHANNEL_IDS)
    )

    for channel in channels:

        if channel and isinstance(channel, hikari.GuildTextChannel):

            last_saved_message = collection.find_one(
                {'channel_id': channel.id},
                sort=[('_id', -1)]
            )
            start_message_id = last_saved_message['message_id'] if last_saved_message else None

            messages_got = await bot.rest.fetch_messages(
                channel,
                after = start_message_id
            )

            if not messages:
                continue

            message_data = await process_messages(messages_got, guild, channel)

            if message_data:
                collection.insert_many(message_data)

@bot.listen(hikari.GuildMessageCreateEvent)
async def message_reward(event: hikari.GuildMessageCreateEvent) -> None:

    if event.is_bot or not event.content:
        return

    MIN_WORDS = 3
    MIN_CHARS = 10
    COOLDOWN = 30
    REWARD_AMOUNT = 25
    MESSAGE_THRESHOLD = 10

    user_id = str(event.author_id)
    content = event.content.strip()

    is_valid = all([
        len(content) >= MIN_CHARS,
        len(content.split()) >= MIN_WORDS,
        not any(url in content for url in ["http://", "https://"]),
        not content.startswith(("/", "!"))
    ])

    if not is_valid:
        return

    user_data = kek_counter.find_one({"user_id": user_id}) or {}

    now = datetime.now(timezone.utc)

    for user in kek_counter.find({"last_valid_message": {"$exists": True}}):
        naive_dt = user["last_valid_message"]
        aware_dt = naive_dt.replace(tzinfo=timezone.utc)
        kek_counter.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_valid_message": aware_dt}}
        )

    last_message = user_data.get("last_valid_message")
    if last_message:
        # Convert naive datetime to aware if needed
        if last_message.tzinfo is None:
            last_message = last_message.replace(tzinfo=timezone.utc)

        # Calculate time difference properly
        time_diff = (now - last_message).total_seconds()
        if time_diff < COOLDOWN:
            return

    kek_counter.update_one(
        {"user_id": user_id},
        {"$set": {
            "valid_message_count": user_data.get("valid_message_count", 0) + 1,
            "last_valid_message": now
        }},
        upsert=True
    )

    # Check reward threshold
    new_count = user_data.get("valid_message_count", 0) + 1
    if new_count % MESSAGE_THRESHOLD == 0:
        kek_counter.update_one(
            {"user_id": user_id},
            {"$inc": {"basedbucks": REWARD_AMOUNT},
             "$set": {"valid_message_count": 0}
             }
        )

        print(f"{event.author.display_name} ({event.author.username}) got {REWARD_AMOUNT} basedbucks for commentary")

        await event.message.add_reaction("💰")

@client.register()
class WordsInMyMouth(
    lightbulb.SlashCommand,
    name="wordsinmymouth",
    description="Make DUM-E say whatever you want!"
):
    message = lightbulb.string('message', 'The message to say.')
    channel_to_send = lightbulb.channel('channel', 'Channel to post the message to.')
    ping = lightbulb.user('user', "The user to ping. Don't abuse.", default=None)
    attachment = lightbulb.attachment('attachment', 'An attachment to add to the message.', default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.defer(ephemeral=True)

        # Prepare message content once
        content = f"{self.ping.mention if self.ping else ''} {self.message}"

        # Send message to channel
        await bot.rest.create_message(
            channel=self.channel_to_send.id,
            content=content,
            attachment=self.attachment if self.attachment else hikari.UNDEFINED,
            user_mentions=True
        )

        # Notify owner
        app = await bot.rest.fetch_application()
        await app.owner.send(
            f'{ctx.user.username} sent to <#{self.channel_to_send.id}> this message via DUM-E: "{self.message}"'
        )

        # Respond to user
        await ctx.respond(
            f'Posting message to {self.channel_to_send}!',
            ephemeral=True
        )

@client.register()
class Ping(
    lightbulb.SlashCommand,
    name = "ping",
    description = "checks the bot is alive"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Pong!")

@client.register()
class IC(
    lightbulb.SlashCommand,
    name = "ic",
    description = "ic"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(f"🇮 🇨")

class MyMenu(lightbulb.components.Menu):
    def __init__(self) -> None:
        self.button = self.add_interactive_button(
            hikari.ButtonStyle.PRIMARY,
            self.on_button_press,
            label="Press me!"
        )

    async def on_button_press(self, ctx: lightbulb.components.MenuContext) -> None:
        await ctx.respond("Button pressed!", edit=True, components=[])
        # Stop listening for additional interactions for this menu
        ctx.stop_interacting()

@client.register()
class TestButton(
    lightbulb.SlashCommand,
    name="testbutton",
    description="Test a button"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        menu = MyMenu()
        resp = await ctx.respond("Press the button!", components=menu)

        try:
            await menu.attach(client, wait=True, timeout=30)
        except asyncio.TimeoutError:
            await ctx.edit_response(resp, "Timed out!", components=[])

@bot.listen(hikari.ReactionAddEvent)
async def on_reaction_create(event: hikari.ReactionAddEvent) -> None:

    user = await bot.rest.fetch_user(event.user_id)

    if user.is_bot:
        return

    if isinstance(event.channel_id, hikari.Snowflake):
        message = await bot.rest.fetch_message(event.channel_id, event.message_id)

        emoji = event.emoji_name
        emoji_id = event.emoji_id
        emoji_type = message.reactions
        for i in emoji_type:
            emoji_type = i.emoji

        if isinstance(emoji_type, hikari.CustomEmoji):
            await message.add_reaction(emoji, emoji_id)
        else:
            await message.add_reaction(emoji)

@bot.listen(hikari.MemberCreateEvent)
async def on_member_join(event: hikari.MemberCreateEvent) -> None:
    """
    Sends a message to a hardcoded modlog channel any time a new user joins the guild (server).
    """
    new_user = event.member
    modlog_channel = event.app.rest.fetch_channel(931378204881608754)

    if modlog_channel:
        embed = hikari.Embed(title="New user!", color=hikari.Color.from_hex_code("#ff6b00"),
                             description=f"<@{new_user.id}> just joined the server!")
        embed.set_author(name=new_user.display_name, icon=new_user.avatar_url)
        embed.add_field("Account created on:", inline=False,
                        value=f"{new_user.created_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")

        await modlog_channel.send(embed)

bot.run()