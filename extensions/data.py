from datetime import datetime, timezone
from datetime import timedelta
from typing import Optional
from collections import Counter
from database import db
from database import kek_counter
import requests
import random
import re
import math

import hikari
from hikari import User
import lightbulb

data_plugin = lightbulb.Plugin("Data")

def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return f"{number}{suffix}"
    
antikek_info = {"user_id": None, "count": 0, "last_timestamp": None}
antikek_data = []
user_based_cooldown = {}
antikek_limit = False
keks_for_next_rank = [1, 10, 25, 40, 100, 150, 200, 350, 550, 700, 1000, 2000]  # Add more thresholds as needed
rank_titles = ["Occasionally Funny", "Jokester", "Stand Up Comedian", "Class Clown", "Amateur Clown", "Professional Clown", "Stand Up Comedian But Funny", "Kekw Collector", "Master of The Funny:tm:", "Head Clown", "The Entire Circus", "Planet of Clownery"]

@data_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option(
    "user", "The user to get information about.", hikari.User, required=False
)
@lightbulb.command("userinfo", "Get info on a server member.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.UserCommand)
async def userinfo(
    ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None
) -> None:
    assert ctx.guild_id is not None

    guild = await ctx.app.rest.fetch_guild(ctx.guild_id)
    target_user = user or ctx.author
    member = await ctx.app.rest.fetch_member(ctx.guild_id, target_user.id)
    roles = await member.fetch_roles()
    color = roles[1].color if len(roles) > 1 else roles[0].color if len(roles) > 0 else hikari.Colour(0xFFFFFF)

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    # Fetch user data from the database (assuming kek_counter is a collection)
    user_data = kek_counter.find_one({"user_id": str(member.id)})

    if not user_data:
        await ctx.respond("No data found for this user.")
        return

    total_keks = user_data.get("kek_count", 0)
    based_count = user_data.get("based_count", 0)
    basedbucks = user_data.get("basedbucks", 0)
    kekbanned = user_data.get("kekbanned", False)
    rank = user_data.get("rank", "No rank")

    keks_last_7_days = [kek for kek in user_data.get("keks", []) if datetime.fromisoformat(kek["date"]).astimezone(timezone.utc) >= seven_days_ago]
    keks_last_month = [kek for kek in user_data.get("keks", []) if datetime.fromisoformat(kek["date"]).astimezone(timezone.utc) >= one_month_ago]

    kek_types = [kek["kek_type"] for kek in user_data.get("keks", [])]
    counts = Counter(kek_types)
    kek_amount = counts.get("kek", 0)
    antikek_amount = counts.get("ANTIkek", 0)

    embed = (
        hikari.Embed(
            title=f"User Info - {member.display_name}",
            description=f"**{rank}**",
            colour=color,
            timestamp=datetime.now().astimezone(),
        )
        .set_footer(
            text=f"Requested by {ctx.author}",
            icon=ctx.author.display_avatar_url,
        )
        .set_thumbnail(member.avatar_url)
        .add_field("Bot?", "Yes" if member.is_bot else "No", inline=True)
        .add_field(
            "Created account on",
            f"<t:{int(member.created_at.timestamp())}:d>\n(<t:{int(member.created_at.timestamp())}:R>)",
            inline=True,
        )
        .add_field(
            "Joined server on",
            f"<t:{int(member.joined_at.timestamp())}:d>\n(<t:{int(member.joined_at.timestamp())}:R>)",
            inline=True,
        )
        .add_field("General Kek Data", "-------", inline=False)
        .add_field("Kek Count (Total)", f"{total_keks} total keks", inline=True)
        .add_field("Recorded Keks", f"{kek_amount} keks with data on record", inline=True)
        .add_field("Recorded ANTIkeks", f"{antikek_amount} ANTIkeks with data on record", inline=True)
        .add_field("Kekbanned?", f"{kekbanned}", inline=True)
        .add_field("Weekly/Monthly Kek Data", "-------", inline=False)
        .add_field("Kek Count (Week)", f"{len(keks_last_7_days)} total keks in last week", inline=True)
        .add_field("Kek Count (Month)", f"{len(keks_last_month)} total keks in last month", inline=True)
        .add_field("Keks per day (Week)", f"{round(len(keks_last_7_days) / 7, 2)} keks per day in last week", inline=True)
        .add_field("Keks per day (Month)", f"{round(len(keks_last_month) / 30, 2)} keks per day in last month", inline=True)
        .add_field("Miscellaneous Data", "-------", inline=False)
        .add_field("Kek:ANTIkek ratio", f"{round(kek_amount / antikek_amount, 2) if antikek_amount != 0 else 'Infinite'} kek ratio", inline=True)
        .add_field("Based Count", f"{based_count} total baseds", inline=True)
        .add_field("Basedbucks", f"{basedbucks} {'Basedbucks' if basedbucks != 1 else 'Basedbuck'} in the bank", inline=True)
    )

    await ctx.respond(embed)
    
@data_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("board_type", "Which board to check.", type=str, choices=["Kek Count", "Based Count"])
@lightbulb.option("page", "Which page to check.", type=int, default=1)
@lightbulb.command("leaderboard", "Get your local discord server leaderboard.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def leaderboard(ctx: lightbulb.Context, board_type: str, page: int = 1) -> None:
    bot = lightbulb.BotApp
    if board_type == "Kek Count":
        leaderboard_data = list(kek_counter.find().sort("kek_count", -1))
        
        page_size = 8
        
        total_pages = (len(leaderboard_data) + page_size - 1) // page_size
        
        try:
            page_number = page
            if not (1 <= page_number <= total_pages):
                raise ValueError
        except (ValueError, IndexError):
            await ctx.respond(f"Invalid page number! Choose a number between 1 and {total_pages}.")
            
        start_idx = (page_number - 1) * page_size
        end_idx = min(start_idx + page_size, len(leaderboard_data))
        
        embed = hikari.Embed(title="Kekw Count Leaderboard", color=hikari.Color.from_hex_code("#3498db"))

        # Add fields for each user's kekw count and rank
        for i, user_data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
            username = user_data["display_name"]
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            kek_count = user_data["kek_count"]
            rank = user_data["rank"]
            ranking = ordinal(i)
            
            if i == 1:
                embed.add_field(name=f"🥇 {ranking} - {username} - Funniest User", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            elif i == 2:
                embed.add_field(name=f"🥈 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            elif i == 3:
                embed.add_field(name=f"🥉 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            else:
                embed.add_field(name=f"{ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
                
        embed.set_footer(text=f"Page {page_number}/{total_pages} | {len(leaderboard_data)} Users | Use /leaderboard to view leaderboard data")

        # Send the embed as a message
        await ctx.respond(embed=embed)

        
    if board_type == "Based Count":
        leaderboard_data = list(kek_counter.find().sort("based_count", -1))
        
        page_size = 8
        
        total_pages = (len(leaderboard_data) + page_size - 1) // page_size
        
        try:
            page_number = page
            if not (1 <= page_number <= total_pages):
                raise ValueError
        except (ValueError, IndexError):
            await ctx.respond(f"Invalid page number! Choose a number between 1 and {total_pages}.")    
        
        start_idx = (page_number - 1) * page_size
        end_idx = min(start_idx + page_size, len(leaderboard_data))
        
        embed = hikari.Embed(title="Based Count Leaderboard", color=hikari.Color.from_hex_code("#3498db"))

        # Add fields for each user's kekw count and rank
        for i, user_data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
            username = user_data["display_name"]
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            based_count = user_data["based_count"]
            rank = user_data["rank"]
            ranking = ordinal(i)
            
            if i == 1:
                embed.add_field(name=f"🥇 {ranking} - {username} - Most Based User", value=f"Based Count: {based_count}", inline=False)
            elif i == 2:
                embed.add_field(name=f"🥈 {ranking} - {username}", value=f"Based Count: {based_count}", inline=False)
            elif i == 3:
                embed.add_field(name=f"🥉 {ranking} - {username}", value=f"Based Count: {based_count}", inline=False)
            else:
                embed.add_field(name=f"{ranking} - {username}", value=f"Based Count: {based_count}", inline=False)
                
        embed.set_footer(text=f"Page {page_number}/{total_pages} | {len(leaderboard_data)} Users | Use /leaderboard to view leaderboard data")

        # Send the embed as a message
        await ctx.respond(embed=embed)
    
@data_plugin.command
@lightbulb.command("bingo", description="Get a link to the official basedcount_bot bingo, along with rules and a leaderboard.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def bingo(ctx: lightbulb.Context) -> None:
    api_endpoint = 'https://basedcount-bingo.netlify.app/api/v1/leaderboard'

    try:
        # Make a GET request to the API
        response = requests.get(api_endpoint)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Process leaderboard data
            leaderboard_entries = data['leaderboard']
            leaderboard_message = "Leaderboard:\n"
            for entry in leaderboard_entries:
                place = ordinal(entry['place'])
                leaderboard_message += f"{place} - {entry['name']} ({entry['victories']} {'wins' if entry['victories'] > 1 or entry['victories'] < 1 else 'win'})\n"
                
        else:
            await ctx.respond(f"Error: Unable to fetch data from the API (Status Code: {response.status_code})")
    
    except Exception as e:
        await ctx.respond(f"An error occurred: {e}")
        
    await ctx.respond(
        "Go to https://bingo.basedcount.com/ and play with the official basedcount_bot bingo card!\n\n"
        "Only people with the \"Bingo Player\" role can participate. If you wish to join, ask a Server Admin to give you the role.\n\n"
        "Rules:\n* Log in with your Discord account.\n"
        "* A card has automatically been generated for you. You don't have to take screenshots of it nor send it in the bingo channel.\n"
        "* When someone ticks a box for the first time, a notification will be sent by the bot here on the bingo channel, as well as on the log on the site. You don't have to send a screenshot of the ticked box.\n"
        "* Get a bingo by marking off the board whenever certain events happen.\n"
        "* No cheesing the card by purposely doing the tiles on the board. It must happen naturally. Light baiting is allowed, but only in forms of social engineering.\n"
        "* If it doesn't happen in the basedcount server, it doesn't count.\n"
        "* If it doesn't happen in a publicly available channel, it doesn't count.\n"
        "* I Exist and the admins get to determine what does or does not count as a hit on the bingo card if it's not obvious.\n"
        "* If someone gets a valid bingo, no more squares can be marked unless you noticed you missed a mark before.\n"
        "* If more than one people get a bingo at once, it counts as a win for all of them.\n"
        "* The current round lasts for one week, starting at the beginning of the round. If seven days have passed without a bingo, then the game is a draw and a new round with new cards begins.\n\n"
        f"{leaderboard_message}"
    )
    
@data_plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    message = event.message
    user_id = event.author_id
    user = await event.app.rest.fetch_member(event.guild_id, user_id)
    channel_id = event.channel_id
    replied_message = None
  
    if event.is_bot:
        return
        
    if event.content is not None:
        content = re.sub(r"[',.?]", "", event.content.lower())
        
        if event.message.referenced_message:

            replied_message = event.message.referenced_message
            
            if content.startswith("based"):
                
                if replied_message.author.id == message.author.id:
                    print(f"{user.username} tried (and failed) to based themselves")
                    return
                
                user_data = kek_counter.find_one({"user_id": str(replied_message.author.id)})

                # If the user does not exist, insert the data
                if not user_data:
                    user_data = {
                        "username": message.author.username,
                        "display_name": member.display_name,
                        "user_id": str(message.author.id),
                        "rank": "Rankless",
                        "keks": [],
                        "kek_count": 0,
                        "based_count": 0,
                        "basedbucks": 500,
                        "loan_debt": [],
                        "kekbanned": False
                    }
                    kek_counter.insert_one(user_data)

                last_based_time = user_based_cooldown.get(user.id, datetime.min.replace(tzinfo=timezone.utc))
                
                cooldown_duration = timedelta(minutes=1)
                
                if datetime.now(timezone.utc) - last_based_time >= cooldown_duration:
                    # Update the document with kek information
                    kek_counter.update_one(
                        {"user_id": str(replied_message.author.id)},
                        {
                            "$inc": {"based_count": 1},
                        },
                        upsert=True,
                    )

                    # Update the last "based" time for the user in the cooldown dictionary
                    user_based_cooldown[user.id] = datetime.now(timezone.utc)

                    print(f"{user.username} gave {replied_message.author.username} a based")

                    based_count = user_data["based_count"] + 1

                    if based_count % 10 == 0:
                        # Get the user and channel objects
                        channel = await event.app.rest.fetch_channel(channel_id)

                        if channel:
                            # Send congratulatory message
                            await event.app.rest.create_message(channel.id, content = f"{replied_message.author.username} reached a based count milestone of {based_count}!")
                            return
                            
        if content.startswith("based"):
            messages = await event.app.rest.fetch_messages(channel_id, before=message.id)
            messages = messages[0]
            
            if messages.author.id == message.author.id:
                print(f"{user.username} tried (and failed) to based themselves")
                return
            
            user_data = kek_counter.find_one({"user_id": str(messages.author.id)})

                # If the user does not exist, insert the data
            if not user_data:
                user_data = {
                    "username": message.author.username,
                    "display_name": member.display_name,
                    "user_id": str(message.author.id),
                    "rank": "Rankless",
                    "keks": [],
                    "kek_count": 0,
                    "based_count": 0,
                    "basedbucks": 500,
                    "loan_debt": [],
                    "kekbanned": False
                }
                kek_counter.insert_one(user_data)

            last_based_time = user_based_cooldown.get(user.id, datetime.min.replace(tzinfo=timezone.utc))
              
            cooldown_duration = timedelta(minutes=1)
            
            if datetime.now(timezone.utc) - last_based_time >= cooldown_duration:
                # Update the document with kek information
                kek_counter.update_one(
                    {"user_id": str(messages.author.id)},
                    {
                        "$inc": {"based_count": 1},
                    },
                    upsert=True,
                )

                # Update the last "based" time for the user in the cooldown dictionary
                user_based_cooldown[user.id] = datetime.now(timezone.utc)

                print(f"{user.username} gave {messages.author.username} a based")

                based_count = user_data["based_count"] + 1

                if based_count % 10 == 0:
                    # Get the user and channel objects
                    channel = await event.app.rest.fetch_channel(channel_id)

                    if channel:
                        # Send congratulatory message
                        await event.app.rest.create_message(channel.id, content = f"{message.author.username} reached a based count milestone of {based_count}!")
            
    
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
        
    
        embed = hikari.Embed(title="Kekw Count Leaderboard", color=hikari.Color.from_hex_code("#3498db"))

        # Add fields for each user's kekw count and rank
        for i, user_data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
            username = user_data["display_name"]
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            kek_count = user_data["kek_count"]
            rank = user_data["rank"]
            ranking = ordinal(i)
                
            if i == 1:
                embed.add_field(name=f"🥇 {ranking} - {username} - Funniest User", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            elif i == 2:
                embed.add_field(name=f"🥈 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            elif i == 3:
                embed.add_field(name=f"🥉 {ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
            else:
                embed.add_field(name=f"{ranking} - {username}", value=f"Kekw Count: {kek_count}\nRank: {rank}", inline=False)
                    
            embed.set_footer(text=f"Page {page_num}/{total_pages} | {len(leaderboard_data)} Users | Use /leaderboard to view leaderboard data")
        
    await leaderboard_channel.send(embed=embed)
    await leaderboard_channel.send(f"{keking_user.display_name} ({keking_user.username}) reacted to {kekd_member.display_name}'s ({kekd_member.username}) [message]({message.make_link(guild)}) with {'a kek' if kek_type == 'kek' else 'an antikek'}!")
    
@data_plugin.command
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ban from participating.", hikari.User)
@lightbulb.command("kekban", "Ban a user from participating in the kekonomy. They can still receive keks.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def kekban(
    ctx: lightbulb.SlashContext, user: hikari.User
) -> None:
    user_data = kek_counter.find_one({"user_id": str(user.id)})
    
    if not user_data:
        user_data = {
            "username": user.username,
            "display_name": user.display_name,
            "user_id": str(user.id),
            "rank": "Rankless",
            "keks": [],
            "kek_count": 0,
            "based_count": 0,
            "basedbucks": 500,
            "loan_debt": [],
            "kekbanned": False
        }
        kek_counter.insert_one(user_data)
    if user_data["kekbanned"]:
        await ctx.respond(f"{user.mention} is already banned from participating in the kekonomy.", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    # Set the kekbanned flag to True
    kek_counter.update_one(
        {"user_id": str(user.id)},
        {"$set": {"kekbanned": True}}
    )

    await ctx.respond(f"{user.mention} has been banned from participating in the kekonomy.")
    
@data_plugin.command
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to allow to participate.", hikari.User)
@lightbulb.command("kekunban", "Reallow a user to participate in the kekonomy.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def kekunban(
    ctx: lightbulb.SlashContext, user: hikari.User
) -> None:
    user_data = kek_counter.find_one({"user_id": str(user.id)})
    
    if not user_data:
        user_data = {
            "username": user.username,
            "display_name": user.display_name,
            "user_id": str(user.id),
            "rank": "Rankless",
            "keks": [],
            "kek_count": 0,
            "based_count": 0,
            "basedbucks": 500,
            "loan_debt": [],
            "kekbanned": False
        }
        kek_counter.insert_one(user_data)
    if not user_data["kekbanned"]:
        await ctx.respond(f"{user.mention} is already allowed to participate in the kekonomy.", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    # Set the kekbanned flag to False
    kek_counter.update_one(
        {"user_id": str(user.id)},
        {"$set": {"kekbanned": False}}
    )

    await ctx.respond(f"{user.mention} has been allowed to participate in the kekonomy once more.")

@data_plugin.listener(hikari.ReactionAddEvent)
async def kek_counting(event: hikari.ReactionAddEvent) -> None:
    
    user = await event.app.rest.fetch_member(event.guild_id, event.user_id)
    channel = await event.app.rest.fetch_channel(event.channel_id)
    message = await event.app.rest.fetch_message(event.channel_id, event.message_id)
    try:
        member = await event.app.rest.fetch_member(event.guild_id, message.author)
        if member.id == 1125871833053417585 and message.interaction and message.interaction.name == "meme":
            member = await event.app.rest.fetch_member(event.guild_id, message.interaction.user.id)
    except hikari.errors.NotFoundError:
        member = "Unknown User"
    if user.is_bot or user.id == member.id:
        return
        
    user_data = kek_counter.find_one({"user_id": str(user.id)})
    if user_data and user_data.get("kekbanned", False):
        dm_channel = await event.app.rest.create_dm_channel(user.id)
        await event.app.rest.create_message(
            channel=dm_channel.id,
            content=f"Sorry {user.mention}, you are banned from participating in the kekonomy.",
        )
        return
        
    antikek_limit = False
    emoji_type = message.reactions
    for i in emoji_type:
        emoji_type = i.emoji
    
    kek_type = "kek" if str(emoji_type) == "<:kekw:1029082555481337876>" else "ANTIkek" if str(emoji_type) == "<:ANTIkek:1135424631130570862>" else None
    
    if kek_type == "ANTIkek":
        user_id = str(event.user_id)
        antikek_info['user_id'] = user_id

        if antikek_info["count"] >= 3 and (datetime.now(timezone.utc) - antikek_info["last_timestamp"]).total_seconds() < 43200:  # 12 hours cooldown
            print("exceeded antikek limit")
            antikek_limit = True
                    # User has exceeded the limit, you can choose to ignore or send a message indicating the limit
            return

                # Update the ANTIkek count and timestamp for the user
        antikek_info["count"] += 1
        antikek_info["last_timestamp"] = datetime.now(timezone.utc)
        antikek_data = [antikek_info]
                
        chance_of_response = 0.001  # 0.1% chance
        if random.random() < chance_of_response:
            channel = reaction.message.channel
            await channel.send(
                "I just dekek'd your comment.\n\n# FAQ\n## What does this mean?\n"
                "The amount of keks (laughs) on your leaderboard entry and discord account has decreased by one.\n\n"
                "## Why did you do this?\nThere are several reasons I may deem a comment to be unworthy of positive or neutral keks. "
                "These include, but are not limited to:\n\n"
                "* Rudeness towards other Discorders.\n"
                "* Spreading incorrect information,\n"
                "* Sarcasm not correctly flagged with a /s.\n\n"
                "## Am I banned from the Discord?\nNo - not yet. But you should refrain from making comments like this in the future. "
                "Otherwise, I will be forced to issue an additional dekek, which may put your commenting and posting privileges in jeopardy.\n\n"
                "## I don't believe my comment deserved a dekek. Can you un-dekek it?\nSure, mistakes happen. But only in exceedingly rare "
                "circumstances will I undo a dekek. If you would like to issue an appeal, shoot me a private message explaining what I got wrong. "
                "I tend to respond to Discord PMs within several minutes. Do note, however, that over 99.9% of dekek appeals are rejected, and yours "
                "is likely no exception.\n\n"
                "## How can I prevent this from happening in the future?\nAccept the dekek and move on. But learn from this mistake: your behavior "
                "will not be tolerated on discord.com. I will continue to issue dekeks until you improve your conduct. Remember: keks are a privilege, not a right."
                )
                
    if kek_type:
        if antikek_limit:
            return
        # Find the document for the user
        user_data = kek_counter.find_one({"user_id": str(message.author.id)})

        # If the user does not exist, insert the data
        if not user_data:
            user_data = {
                "username": message.author.username,
                "display_name": member.display_name,
                "user_id": str(message.author.id),
                "rank": "Rankless",
                "keks": [],
                "kek_count": 0,
                "based_count": 0,
                "basedbucks": 500,
                "loan_debt": [],
                "kekbanned": False
            }
            kek_counter.insert_one(user_data)
            
        existing_kek = kek_counter.find_one(
            {
                "user_id": str(message.author.id),
                "keks": {
                    "$elemMatch": {
                        "messageLink": message.make_link(event.guild_id),
                        "reacter_user_id": str(event.user_id),
                        "kek_type": kek_type,
                    }
                },
            }
        )

        # Update the document with kek information
        if not existing_kek:
            kek_counter.update_one(
                {"user_id": str(message.author.id)},
                {
                    "$inc": {"kek_count": 1} if kek_type == "kek" else {"kek_count": -1},
                    "$set": {"display_name": member.display_name},
                    "$push": {
                        "keks": {
                            "messageLink": message.make_link(event.guild_id),
                            "date": datetime.now(timezone.utc).isoformat(),
                            "reacter_user_id": str(event.user_id),
                            "reacter_username": user.username,
                            "kek_type": kek_type,
                        }
                    },
                },
                upsert=True,
            )
        
            leaderboard_channel = await event.app.rest.fetch_channel(1141830149176836246)
            
            await update_leaderboard(event.guild_id, member, user, kek_type, message, leaderboard_channel)
            await update_rank(str(message.author.id), event.channel_id, user, member, channel)
        
async def update_rank(user_id, channel_id, user, member, channel):
    user_data = kek_counter.find_one({"user_id": user_id})
    kek_count = user_data["kek_count"]
    new_rank = None
    previous_rank = user_data.get("rank", "Rankless")  # Use get method to provide a default value
    
    rank_up = False

    for i in range(len(keks_for_next_rank)-1, -1, -1):
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
                    await channel.send(f"🎉🎉🎉 {member.mention} has exceeded clownery of the circus kind, and is no longer just the entire circus, an entire Planet of Clownery! 🎉🎉🎉")
                    
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
                    await channel.send(f"🎉🎉🎉 {member.mention} has shown themselves to be one of the funniest motherfuckers this side of basedcount and is now not just a clown, but The Entire Circus! 🎉🎉🎉")
                    
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
                    await channel.send(f"{member.display_name} reached a kekw count milestone of {kek_count} and received the rank '{new_rank}'!")

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
    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(data_plugin)