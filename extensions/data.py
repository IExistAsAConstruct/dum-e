from datetime import datetime, timezone, timedelta
from collections import Counter

from pymongo import ReturnDocument

from database import kek_counter
import random
import re
import math
import asyncio
from typing import Optional, Final
from cachetools import TTLCache


import hikari
import lightbulb
from lightbulb import Choice

loader = lightbulb.Loader()

def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {
            1: 'st',
            2: 'nd',
            3: 'rd'
        }.get(number % 10, 'th')
    return f"{number}{suffix}"

OWNER_ID = 453445704690434049

keks_for_next_rank = [
    1, 10, 25, 40,
    100, 150, 200, 350,
    550, 700, 1000, 2000
]

rank_titles = [
    "Occasionally Funny", "Jokester", "Stand Up Comedian", "Class Clown",
    "Amateur Clown", "Professional Clown", "Stand Up Comedian But Funny", "Kekw Collector",
    "Master of The Funny:tm:", "Head Clown", "The Entire Circus", "Planet of Clownery"
]

KEKW_EMOJI: Final[str] = "<:kekw:1029082555481337876>"
ANTIKEK_EMOJI: Final[str] = "<:ANTIkek:1135424631130570862>"
LEADERBOARD_CHANNEL_ID: Final[int] = 1141830149176836246
BOT_ID: Final[int] = 1125871833053417585
ANTIKEK_COOLDOWN_SECONDS: Final[int] = 43200  # 12 hours
ANTIKEK_MAX_COUNT: Final[int] = 3
DEKEK_RESPONSE_CHANCE: Final[float] = 0.001
INITIAL_BASEDBUCKS: Final[int] = 500

user_based_cooldown = {}

@loader.command()
class GetInfo(
    lightbulb.SlashCommand,
    name = "userinfo",
    description = "Get info on a server member."
):
    user = lightbulb.user('user', "The user to get the info of.", default = None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        target_user = self.user or ctx.user
        member_got = await ctx.user.app.rest.fetch_member(ctx.guild_id, target_user)
        roles = await member_got.fetch_roles()
        color = roles[1].color if len(roles) > 1 else roles[0].color if len(roles) > 0 else hikari.Color(0xFFFFFF)

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        one_month_ago = now - timedelta(days=30)

        if not member_got:
            await ctx.respond("Could not find user!", ephemeral = True)
            return

        user_data = kek_counter.find_one(
            {'user_id': str(member_got.id)}
        )

        if not user_data:
            await ctx.respond("Could not find user data!", ephemeral=True)
            return

        total_keks = user_data.get('kek_count', 0)
        based_count = user_data.get('based_count', 0)
        basedbucks = user_data.get('basedbucks', 0)
        kekbanned = user_data.get('kekbanned', False)
        rank = user_data.get('rank', 'No Rank')

        keks_last_7_days = [kek for kek in user_data.get("keks", []) if
                            datetime.fromisoformat(kek["date"]).astimezone(timezone.utc) >= seven_days_ago]
        keks_last_month = [kek for kek in user_data.get("keks", []) if
                           datetime.fromisoformat(kek["date"]).astimezone(timezone.utc) >= one_month_ago]

        kek_types = [kek["kek_type"] for kek in user_data.get("keks", [])]
        counts = Counter(kek_types)
        kek_amount = counts.get("kek", 0)
        antikek_amount = counts.get("ANTIkek", 0)

        embed = hikari.Embed(
                title=f'User Info - {member_got.display_name}',
                description=f'**{rank}**',
                color=color,
                timestamp=datetime.now().astimezone()
            )

        embed.set_footer(
            text=f'Requested by {ctx.user}',
            icon=ctx.user.display_avatar_url
        )

        embed.set_thumbnail(member_got.avatar_url)
        embed.add_field('Bot?', 'Yes' if member_got.is_bot else 'No', inline=True)
        embed.add_field(
            'Created account on',
            f'<t:{int(member_got.created_at.timestamp())}:d>\n(<t:{int(member_got.created_at.timestamp())}:R>)',
            inline=True
        )
        embed.add_field(
            "Joined server on",
            f"<t:{int(member_got.joined_at.timestamp())}:d>\n(<t:{int(member_got.joined_at.timestamp())}:R>)",
            inline=True,
        )
        embed.add_field("General Kek Data","-------",inline=False)
        embed.add_field(
            "Kek Count (Total)",
            f"{total_keks} total keks",
            inline=True
        )
        embed.add_field(
            "Recorded Keks",
            f"{kek_amount} keks with data on record",
            inline=True
        )
        embed.add_field(
            "Recorded ANTIkeks",
            f"{antikek_amount} ANTIkeks with data on record",
            inline=True
        )
        embed.add_field("Kekbanned?", f"{kekbanned}", inline=True)
        embed.add_field("Weekly/Monthly Kek Data", "-------", inline=False)
        embed.add_field(
            "Kek Count (Week)",
            f"{len(keks_last_7_days)} total keks in last week",
            inline=True
        )
        embed.add_field(
            "Kek Count (Month)",
            f"{len(keks_last_month)} total keks in last month",
            inline=True
        )
        embed.add_field(
            "Keks per day (Week)",
            f"{round(len(keks_last_7_days) / 7, 2)} keks per day in last week",
            inline=True
        )
        embed.add_field(
            "Keks per day (Month)",
            f"{round(len(keks_last_month) / 30, 2)} keks per day in last month",
            inline=True
        )
        embed.add_field("Miscellaneous Data", "-------", inline=False)
        embed.add_field(
            "Kek:ANTIkek ratio",
            f"{round(kek_amount / antikek_amount, 2) if antikek_amount != 0 else 'Infinite'} kek ratio",
            inline=True
        )
        embed.add_field("Based Count", f"{based_count} total baseds", inline=True)
        embed.add_field(
            "Basedbucks",
            f"{basedbucks} {'Basedbucks' if basedbucks != 1 else 'Basedbuck'} in the bank",
            inline=True
        )
        embed.add_field(
            "Credit Score",
            f"{user_data.get('credit_score', 700)}",
            inline=True
        )

        await ctx.respond(embed=embed)


@loader.command()
class Leaderboard(
    lightbulb.SlashCommand,
    name='leaderboard',
    description='Get the leaderboard for keks and baseds.'
):
    board_type = lightbulb.string(
        'board_type',
        'Which board to check.',
        choices=[
            Choice('Kek Count', 'Kek Count'),
            Choice('Based Count', 'Based Count'),
        ]
    )
    page = lightbulb.integer('page', 'Which page to check.', default=1)

    async def create_leaderboard_embed(self, data, page_number, board_type):
        page_size = 8
        total_pages = (len(data) + page_size - 1) // page_size

        if not (1 <= page_number <= total_pages):
            raise ValueError(f'Invalid page number! Choose a number between 1 and {total_pages}.')

        start_idx = (page_number - 1) * page_size
        end_idx = min(start_idx + page_size, len(data))

        embed = hikari.Embed(
            title=f'{board_type} Leaderboard',
            color=hikari.Color.from_hex_code('#3498db')
        )

        count_field = 'kek_count' if board_type == 'Kek Count' else 'based_count'
        title_suffix = 'Funniest User' if board_type == 'Kek Count' else 'Most Based User'

        for i, user_data in enumerate(data[start_idx:end_idx], start=start_idx + 1):
            username = 'IF the Funny - Retired. Salute!' if user_data['display_name'] == 'laux3650atmylaurierdotca' else \
            user_data['display_name']
            count = user_data[count_field]
            rank = user_data['rank']
            ranking = ordinal(i)

            if i == 1:
                name = f"🥇 {ranking} - {username} - {title_suffix}"
            elif i == 2:
                name = f"🥈 {ranking} - {username}"
            elif i == 3:
                name = f"🥉 {ranking} - {username}"
            else:
                name = f"{ranking} - {username}"

            value = f"{board_type}: {count}\nRank: {rank}"
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(
            text=f'Page {page_number}/{total_pages} | {len(data)} Users | Use /leaderboard to view leaderboard data'
        )

        return embed

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        try:
            # Defer the response immediately to prevent timeout
            await ctx.defer()

            # Get the data and sort it
            sort_field = 'kek_count' if self.board_type == 'Kek Count' else 'based_count'
            leaderboard_data = list(kek_counter.find().sort(sort_field, -1))

            # Create and send the embed
            embed = await self.create_leaderboard_embed(
                leaderboard_data,
                self.page,
                self.board_type
            )

            await ctx.respond(embed)

        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {str(e)}", ephemeral=True)


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    # Skip bot messages immediately
    if event.is_bot or event.content is None:
        return

    message = event.message
    user_id = event.author_id
    user = await event.app.rest.fetch_member(event.guild_id, user_id)
    channel_id = event.channel_id

    # Preprocess content
    content = re.sub(r"[',.?]", "", event.content.lower())

    # Early return if not a "based" or "cringe" message
    if not (content.startswith("based") or content.startswith("cringe")):
        return

    # Determine target message (replied or previous message)
    target_message = (
        event.message.referenced_message
        if event.message.referenced_message
        else (await event.app.rest.fetch_messages(channel_id, before=message.id))[0]
    )

    # Prevent self-rating
    if target_message.author.id == message.author.id:
        print(f"{user.username} tried (and failed) to {'base' if content.startswith('based') else 'cringe'} themselves")
        return

    # Check cooldown
    last_based_time = user_based_cooldown.get(user.id, datetime.min.replace(tzinfo=timezone.utc))
    cooldown_duration = timedelta(minutes=1)

    if datetime.now(timezone.utc) - last_based_time < cooldown_duration:
        return

    # Determine increment value
    increment = 1 if content.startswith("based") else -1

    # Prepare user data, creating if not exists
    try:
        user_data = kek_counter.find_one_and_update(
            {"user_id": str(target_message.author.id)},
            {
                "$set": {
                    "username": target_message.author.username,
                    "display_name": target_message.author.display_name,
                },
                "$inc": {"based_count": increment},
                "$setOnInsert": {
                    "rank": "Rankless",
                    "keks": [],
                    "kek_count": 0,
                    "basedbucks": 500,
                    "loan_debt": [],
                    "credit_score": 100,
                    "kekbanned": False
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        # Update cooldown
        user_based_cooldown[user.id] = datetime.now(timezone.utc)

        # Log action
        action = "based" if content.startswith("based") else "cringed"
        print(f"{user.username} {action} {target_message.author.username}")

        # Milestone check
        based_count = user_data['based_count']
        if based_count % 10 == 0:
            channel = await event.app.rest.fetch_channel(channel_id)
            if channel:
                await event.app.rest.create_message(
                    channel.id,
                    content=f"{target_message.author.username} reached a based count milestone of {based_count}!"
                )

    except Exception as e:
        print(f"Error processing message: {e}")
        # Optionally log the full traceback
        import traceback
        traceback.print_exc()


async def update_leaderboard(guild, kekd_member, keking_user, kek_type, message, leaderboard_channel):
    leaderboard_data = list(kek_counter.find().sort("kek_count", -1))
    data = {}

    for user_data in leaderboard_data:
        user_id = user_data["user_id"]
        data[user_id] = {"kekw_count": user_data["kek_count"]}

    kekd_member_position = None
    for position, item in enumerate(data):
        if item == str(kekd_member.id):
            kekd_member_position = position + 1
            break

    if kekd_member_position is not None:
        # Calculate the total number of pages
        page_size = 8
        total_pages = (len(leaderboard_data) + page_size - 1) // page_size

        # Calculate the page number based on the user's position
        page_num = (kekd_member_position + page_size - 1) // page_size

        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(leaderboard_data))

        embed = hikari.Embed(title="Kek Count Leaderboard", color=hikari.Color.from_hex_code("#3498db"))

        # Add fields for each user's kekw count and rank
        for i, user_data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
            username = user_data["display_name"]
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            kek_count = user_data["kek_count"]
            rank = user_data["rank"]
            ranking = ordinal(i)

            if i == 1:
                embed.add_field(name=f"🥇 {ranking} - {username} - Funniest User",
                                value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            elif i == 2:
                embed.add_field(name=f"🥈 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}",
                                inline=False)
            elif i == 3:
                embed.add_field(name=f"🥉 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}",
                                inline=False)
            else:
                embed.add_field(name=f"{ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}",
                                inline=False)

            embed.set_footer(
                text=f"Page {page_num}/{total_pages} | {len(leaderboard_data)} Users | Use /leaderboard to view leaderboard data")

        await leaderboard_channel.send(embed=embed)
        await leaderboard_channel.send(
            f"{keking_user.display_name} ({keking_user.username}) reacted to {kekd_member.display_name}'s ({kekd_member.username}) [message]({message.make_link(guild)}) with {'a kek' if kek_type == 'kek' else 'an antikek'}!"
        )

@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
async def me_only(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if ctx.user.id != OWNER_ID:
        raise RuntimeError("You can't use this command!")

@loader.command
class Kekban(
    lightbulb.SlashCommand,
    name='kekban',
    description='Ban a user from participating in the economy. They can still receive keks.',
    hooks=[me_only or lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)]
):
    user = lightbulb.user('user', 'The user to ban from participating.')

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        user_data = kek_counter.find_one((
            {'user_id': str(self.user.id)}
        ))

        if not user_data:
            user_data = {
                "username": self.user.username,
                "display_name": self.user.display_name,
                "user_id": str(self.user.id),
                "rank": "Rankless",
                "keks": [],
                "kek_count": 0,
                "based_count": 0,
                "basedbucks": 500,
                "loan_debt": [],
                "credit_score": 100,
                "kekbanned": False
            }
            kek_counter.insert_one(user_data)
        if user_data['kekbanned']:
            await ctx.respond(
                f'{self.user.mention} is already banned from participating in the kekonomy.',
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        kek_counter.update_one(
            {"user_id": str(self.user.id)},
            {"$set": {"kekbanned": True}}
        )

        await ctx.respond(f"{self.user.mention} has been banned from participating in the kekonomy.")


@loader.command
class Kekunban(
    lightbulb.SlashCommand,
    name='kekunban',
    description='Reallow a user to participate in the kekonomy.',
    hooks=[me_only or lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)]
):
    user = lightbulb.user('user', 'The user to allow to participate.')

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        user_data = kek_counter.find_one((
            {'user_id': str(self.user.id)}
        ))

        if not user_data:
            user_data = {
                "username": self.user.username,
                "display_name": self.user.display_name,
                "user_id": str(self.user.id),
                "rank": "Rankless",
                "keks": [],
                "kek_count": 0,
                "based_count": 0,
                "basedbucks": 500,
                "loan_debt": [],
                "credit_score": 100,
                "kekbanned": False
            }
            kek_counter.insert_one(user_data)
        if not user_data['kekbanned']:
            await ctx.respond(
                f'{self.user.mention} is already allowed to participate in the kekonomy.',
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        kek_counter.update_one(
            {"user_id": str(self.user.id)},
            {"$set": {"kekbanned": False}}
        )

        await ctx.respond(f"{self.user.mention} has been allowed to participate in the kekonomy once more.")


user_cache = TTLCache(maxsize=1000, ttl=3600)  # Cache user data for 1 hour
antikek_cache = TTLCache(maxsize=1000, ttl=ANTIKEK_COOLDOWN_SECONDS)


async def get_member_safe(app, guild_id: int, user_id: int) -> Optional[hikari.Member]:
    """Safely fetch member with error handling and caching."""
    cache_key = f"{guild_id}:{user_id}"
    if cache_key in user_cache:
        return user_cache[cache_key]

    try:
        member = await app.rest.fetch_member(guild_id, user_id)
        user_cache[cache_key] = member
        return member
    except hikari.errors.NotFoundError:
        return None


def get_kek_type(emoji: hikari.Emoji) -> Optional[str]:
    """Determine the type of kek reaction."""
    emoji_str = str(emoji)
    if emoji_str == KEKW_EMOJI:
        return "kek"
    elif emoji_str == ANTIKEK_EMOJI:
        return "ANTIkek"
    return None


async def check_antikek_limit(user_id: str) -> bool:
    """Check if user has exceeded ANTIkek limit."""
    if user_id not in antikek_cache:
        antikek_cache[user_id] = 1
        return False

    count = antikek_cache[user_id]
    if count >= ANTIKEK_MAX_COUNT:
        return True

    antikek_cache[user_id] = count + 1
    return False


async def send_dekek_message(channel) -> None:
    """Send the dekek message with rate limiting."""
    if random.random() >= DEKEK_RESPONSE_CHANCE:
        return

    message = (
        "I just dekek'd your comment.\n\n"
        "# FAQ\n"
        "## What does this mean?\n"
        "The amount of keks (laughs) on your leaderboard entry and discord account has decreased by one.\n\n"
        "## Why did you do this?\n"
        "There are several reasons I may deem a comment to be unworthy of positive or neutral keks. "
        "These include, but are not limited to:\n\n"
        "* Rudeness towards other Discorders.\n"
        "* Spreading incorrect information,\n"
        "* Sarcasm not correctly flagged with a /s.\n\n"
        "## Am I banned from the Discord?\n"
        "No - not yet. But you should refrain from making comments like this in the future. "
        "Otherwise, I will be forced to issue an additional dekek, which may put your commenting "
        "and posting privileges in jeopardy.\n\n"
        "## I don't believe my comment deserved a dekek. Can you un-dekek it?\n"
        "Sure, mistakes happen. But only in exceedingly rare circumstances will I undo a dekek. "
        "If you would like to issue an appeal, shoot me a private message explaining what I got wrong. "
        "I tend to respond to Discord PMs within several minutes. Do note, however, that over 99.9% "
        "of dekek appeals are rejected, and yours is likely no exception.\n\n"
        "## How can I prevent this from happening in the future?\n"
        "Accept the dekek and move on. But learn from this mistake: your behavior will not be "
        "tolerated on discord.com. I will continue to issue dekeks until you improve your conduct. "
        "Remember: keks are a privilege, not a right."
    )

    try:
        await channel.send(message)
    except hikari.errors.ForbiddenError:
        pass  # Silently handle permission errors


async def process_kek(
        kek_counter,
        message: hikari.Message,
        member: hikari.Member,
        user: hikari.User,
        kek_type: str,
        guild_id: int,
        is_april_fools: bool
) -> None:
    """Process a kek reaction and update the database."""
    user_data = kek_counter.find_one({"user_id": str(message.author.id)})

    if not user_data:
        user_data = {
            "username": message.author.username,
            "display_name": member.display_name,
            "user_id": str(message.author.id),
            "rank": "Rankless",
            "keks": [],
            "kek_count": 0,
            "based_count": 0,
            "basedbucks": INITIAL_BASEDBUCKS,
            "loan_debt": [],
            "credit_score": 100,
            "kekbanned": False
        }
        kek_counter.insert_one(user_data)

    # Check for existing kek with aggregation for better performance
    existing_kek = kek_counter.find_one({
        "user_id": str(message.author.id),
        "keks": {
            "$elemMatch": {
                "messageLink": message.make_link(guild_id),
                "reacter_user_id": str(user.id),
                "kek_type": kek_type,
            }
        }
    })

    if not existing_kek:
        update_data = {
            "$inc": {"kek_count": 1 if kek_type == "kek" else -1 if kek_type == "ANTIkek" or is_april_fools else 0},
            "$set": {"display_name": member.display_name},
            "$push": {
                "keks": {
                    "messageLink": message.make_link(guild_id),
                    "date": datetime.now(timezone.utc).isoformat(),
                    "reacter_user_id": str(user.id),
                    "reacter_username": user.username,
                    "kek_type": kek_type,
                }
            }
        }

        kek_counter.update_one(
            {"user_id": str(message.author.id)},
            update_data,
            upsert=True
        )


@loader.listener(hikari.GuildReactionAddEvent)
async def kek_counting(event: hikari.GuildReactionAddEvent) -> None:
    """Main event handler for counting keks."""
    # Early return if no emoji
    if not event.emoji_name:
        return

    try:

        is_april_fools = datetime.now().month == 4 and datetime.now().day == 1

        # Fetch necessary data concurrently
        user, channel, message = await asyncio.gather(
            get_member_safe(event.app, event.guild_id, event.user_id),
            event.app.rest.fetch_channel(event.channel_id),
            event.app.rest.fetch_message(event.channel_id, event.message_id)
        )

        if not all([user, channel, message]):
            return

        # Early return conditions
        if user.is_bot:
            return

        # Get message author
        if message.interaction and message.interaction.name == "meme" and message.author.id == BOT_ID:
            member = await get_member_safe(event.app, event.guild_id, message.interaction.user.id)
        else:
            member = await get_member_safe(event.app, event.guild_id, message.author.id)

        if not member or user.id == member.id:
            return

        # Modified emoji handling
        guild = await channel.app.rest.fetch_guild(event.guild_id)

        # Check if it's a custom emoji
        if event.emoji_id:
            emoji = await event.app.rest.fetch_emoji(guild, event.emoji_id)
        else:
            # Handle Unicode emoji case
            emoji = event.emoji_name  # Use the emoji name directly

        kek_type = get_kek_type(emoji)
        if not kek_type:
            return

        if kek_type == "ANTIkek" and await check_antikek_limit(str(user.id)):
            return

        # Check if user is kekbanned
        user_data = kek_counter.find_one({"user_id": str(user.id)})
        if user_data and user_data.get("kekbanned", False):
            dm_channel = await event.app.rest.create_dm_channel(user.id)
            await dm_channel.send(f"Sorry {user.mention}, you are banned from participating in the kekonomy.")
            return

        # Process kek and update leaderboard
        await asyncio.gather(
            process_kek(kek_counter, message, member, user, kek_type, event.guild_id, is_april_fools),
            update_leaderboard(event.guild_id, member, user, kek_type, message,
                               await event.app.rest.fetch_channel(LEADERBOARD_CHANNEL_ID)),
            update_rank(str(message.author.id), member, channel)
        )

        # Send dekek message if applicable
        if kek_type == "ANTIkek":
            await send_dekek_message(channel)

    except Exception as e:
        # Log the error but don't crash the bot
        print(f"Error in kek_counting: {str(e)}")


async def update_rank(user_id, member, channel):
    user_data = kek_counter.find_one({"user_id": user_id})
    kek_count = user_data["kek_count"]

    rank_up = False

    for i in range(len(keks_for_next_rank) - 1, -1, -1):
        threshold = keks_for_next_rank[i]
        title = rank_titles[i]

        if kek_count == threshold:
            new_rank = title

            if new_rank == rank_titles[-1]:
                # Get the user and channel objects
                #    user = await bot.rest.fetch_user(user_id)
                #    channel = await bot.rest.fetch_channel(channel_id)

                if channel:
                    # Send a special message for achieving the very last rank
                    await channel.send(
                        f"🎉🎉🎉 {member.mention} has exceeded clownery of the circus kind, and is no longer just the entire circus, an entire Planet of Clownery! 🎉🎉🎉")

                kek_counter.update_one(
                    {"user_id": user_data["user_id"]},
                    {"$set": {"rank": new_rank}},
                )

                rank_up = True

                break

            # Check if the user has reached the very last rank
            if new_rank == rank_titles[-2]:

                if channel:
                    # Send a special message for achieving the very last rank
                    await channel.send(
                        f"🎉🎉🎉 {member.mention} has shown themselves to be one of the funniest motherfuckers this side of basedcount and is now not just a clown, but The Entire Circus! 🎉🎉🎉")

                kek_counter.update_one(
                    {"user_id": user_data["user_id"]},
                    {"$set": {"rank": new_rank}},
                )

                rank_up = True

                break

            # Check if the user has reached a new rank (excluding the last rank)
            elif new_rank != user_data["rank"]:
                # Get the user and channel objects
                #    user = await bot.rest.fetch_user(user_id)
                #    channel = await bot.rest.fetch_channel(channel_id)

                if channel:
                    # Send congratulatory message for reaching a new rank
                    await channel.send(
                        f"{member.display_name} reached a kekw count milestone of {kek_count} and received the rank '{new_rank}'!")

                # Update the rank in the database
                kek_counter.update_one(
                    {"user_id": user_data["user_id"]},
                    {"$set": {"rank": new_rank}},
                )

                rank_up = True

                break

    if not rank_up and math.trunc(kek_count) % 10 == 0:
        # Get the user and channel objects
        #    user = await bot.rest.fetch_user(user_id)
        #    channel = await bot.rest.fetch_channel(channel_id)

        if channel:
            # Send congratulatory message
            await channel.send(f"{member.display_name} reached a kekw count milestone of {kek_count}!")