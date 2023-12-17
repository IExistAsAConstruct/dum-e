import discord
import random
import asyncio
import re
import emoji
from datetime import datetime, timedelta
import time
import json
import os.path
import requests
import shutil
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable the Members intent
intents.reactions = True

client = discord.Client(intents=intents)

target_user_id = "146996859183955968"
response_counter = {}
user_ranks = {}
bot_owner = 453445704690434049
stopwatch_data = {}
seen_messages = set()
file_path = "basedcount.json"
token_path =  'token.txt'
backup_file = "backup_count.txt"  # Backup file path

# Function to capitalize text
def capitalize_text(text):
    return text.upper()

cooldown_duration = 300  # Cooldown duration in seconds
cooldown = 43200
send_message_interval = 10  # Count interval to send a message

# Dictionary to track user last message timestamps
user_message_timestamps = {}

# Cooldown duration in seconds
cooldown_duration = 10
message_limit = 3  # Number of messages allowed within the cooldown period

async def is_rate_limited(user_id):
    current_time = time.time()
    timestamps = user_message_timestamps.get(user_id, [])

    # Remove old timestamps
    timestamps = [t for t in timestamps if current_time - t <= cooldown_duration]

    # Check if the user has exceeded the message limit
    if len(timestamps) >= message_limit:
        return True

    # Update the timestamps for the user
    timestamps.append(current_time)
    user_message_timestamps[user_id] = timestamps

    return False

# Load stored data from file
def load_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        for user_id, user_data in data.items():
            user_data.setdefault("kekw_count", 0)
    for user_id in data:
        if "daily_kek_counts" not in data[user_id]:
            data[user_id]["daily_kek_counts"] = [0] * 7
    return data
    
# Save data to file
def save_data(data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
        
def save_seen_messages(seen_messages):
    with open('seen_messages.json', 'w') as file:
        json.dump(list(seen_messages), file)

def load_seen_messages():
    try:
        with open('seen_messages.json', 'r') as file:
            return set(json.load(file))
    except FileNotFoundError:
        return set()
        
# Load user reactions data from a file
def load_user_reactions(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save user reactions data to a file
def save_user_reactions(user_reactions, file_path):
    user_reactions_dict = {str(message_id): list(user_ids) for message_id, user_ids in user_reactions.items()}
    with open(file_path, 'w') as file:
        json.dump(user_reactions_dict, file)
        
# Backup data to a text file
def backup_data(data):
    with open(backup_file, 'w') as file:
        for user_id, count in data.items():
            file.write(f"{user_id}: {count}\n")
            
# Function to get the rank based on kekw count
def get_rank(kekw_count):
    ranks = [
        ("Occasionally Funny", 1),
        ("Jokester", 10),
        ("Stand Up Comedian", 25),
        ("Class Clown", 40),
        ("Amateur Clown", 100),
        ("Professional Clown", 150),
        ("Stand Up Comedian But Funny", 200),
        ("Kekw Collector", 350),
        ("Master of The Funny:tm:", 550),
        ("Head Clown", 700),
        ("The Entire Circus", 999)
    ]
    
    for rank, kekw_requirement in ranks[::-1]:
        if kekw_count >= kekw_requirement:
            return rank
    return "Rankless"
    
def find_users_by_name(guild, target_name):
    target_name_lower = target_name.lower()
    return [member for member in guild.members if member.display_name.lower() == target_name_lower or member.name.lower() == target_name_lower]

    
def calculate_kek_per_day_ratio(daily_kek_counts):
    data = load_data(file_path)
    
    current_day = datetime.today().weekday()

    # Check if the current day is different from the last recorded day
    last_recorded_day = data.get("last_recorded_day", current_day)
    if current_day != last_recorded_day:
        # Calculate the number of days between the current day and the last recorded day
        days_since_last_recorded = (current_day - last_recorded_day) % 7

        # Fill in the days with 0 keks in between
        for i in range(1, days_since_last_recorded):
            day_index = (last_recorded_day + i) % 7
            daily_kek_counts[day_index] = 0
    
    # Get the daily kek count list for the last 7 days
    total_keks = sum(daily_kek_counts)
    total_days = len(daily_kek_counts)
    
    
    if total_days == 0:
        return 0.0

    return total_keks / total_days
    
def get_kek_per_day_ratio(user_data):
    return calculate_kek_per_day_ratio(user_data["daily_kek_counts"])
    
def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return f"{number}{suffix}"
    
user_cooldowns = {}
user_reactions_file = "user_reactions.json"
user_reactions = load_user_reactions(user_reactions_file)
last_unkek_time = {}

commands_list = [
    "!balloon - What's wrong with you? You're an idiot...",
    "!basedcountpage [number] - View everyone's discord based count. Number is page number, no number defaults to page 1.",
    "!bingo - Gain a link to the semi-official basedcount_bot bingo card. May contain in-jokes.",
    "!commands [number] - View a list of all commands (duh). Number is page number, no number defaults to page 1.",
    "!dekekcomment - I just dekek'd your comment.",
    "!hacking - Okay, kid, I'm done. I doubt you even have basic knowledge of hacking...",
    "!ifthefunny - Did you ever hear the tragedy of ironicForemanite The Funny? I thought not...",
    "!kekcountpage [number] - View the discord kekw count leaderboard (how many kekws users received). Number is page number, no number defaults to page 1.",
    "!kekratio [name] - View a user's kek ratio. [name] is either user display name or username. No name defaults to your kekratio.",
    "!kpd [name] - View a user's KPD (kek per day) average. [name] is either user display name or username. No name defaults to your kpd.",
    "!navyseals - What the fuck did you just fucking say about me, you little bitch?",
    "!postingcontent - Posting content again that was deemed rule-breaking by one of us is de facto considered rule-breaking...",
    "!product - I've personally seen a lot of very smart people try and figure out how to make a product better...",
    "!shakeys - Shows off the latest Shakey's ad that collaborates with PCM.",
    "!sofunny - Omg, this video is so funny, I laughed so hard...",
    "!startstopwatch - Starts a personal stopwatch for you only. Lap with !lapstopwatch. Stop with !stopstopwatch.",
    "!toiletbed - I know that some people might think it's weird that I live in my toilet bed...",
    "!tts - Makes DUM-E say spooky TTS noises.",
    "!unreact - Makes DUM-E remove his reactions to the last 10 messages.",
    "wordsinmymouth - Puts words in DUM-E's mouth. Used as 'wordsinmymouth [Server ID] [channel-name] [message]'. DMS ONLY."
]


def create_commands_embed(page_num, total_pages, message):
    commands_per_page = 5
    start_idx = (page_num - 1) * commands_per_page
    end_idx = start_idx + commands_per_page
    embed = discord.Embed(title=f"Commands (Page {page_num} / {total_pages})", color=discord.Color.blue())
    embed.set_footer(text=f"Page {page_num}/{total_pages} | {len(commands_list)} Commands | use !commands [pagenum] to see other pages")
        
    for i, command in enumerate(commands_list[start_idx:end_idx], start=start_idx + 1):
        command_name, command_description = command.split(" - ", 1)
        embed.add_field(name=command_name, value=command_description, inline=False)

    return embed
    
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    global based_count
    seen_messages = load_seen_messages()
    based_count = load_data(file_path)

with open(token_path, 'r') as token_file:
    bot_token = token_file.read().strip()

@client.event
async def on_message(message):
    global seen_messages
    if message.author == client.user:
        if 'nigger' in message.content.lower() or 'nigga' in message.content.lower():
            await message.delete()
        return
    
    seen_messages = load_seen_messages()
    seen_messages.add(message.id)
    save_seen_messages(seen_messages)
    content = re.sub(r"[',.?]", "", message.content.lower())
    guild = message.guild  # Get the guild (server) object
    user_id = message.author.id
    
    
    if content.startswith("!"):
        if await is_rate_limited(user_id):
            print("user was rate limited")
            return

    # Find emojis in the message content
#    emojis = []

    # Check for Unicode emojis
#    for c in message.content:
#        if emoji.is_emoji(c):
#            emojis.append(c)

    # Check for custom emojis
#    custom_emojis = [
#        e for e in message.content.split()
#        if len(e) > 2 and e[0] == '<' and e[-1] == '>'
#    ]
#    emojis.extend(custom_emojis)

    # Iterate over the found emojis and add them as reactions
#    for emoji_code in emojis:
#        try:
#            await message.add_reaction(emoji_code)
#        except discord.errors.HTTPException:
#            print(f"Failed to add reaction for emoji: {emoji_code}")
    
    if content.startswith("!commands"):
        total_pages = (len(commands_list) + 4) // 5

        command_parts = message.content.split()
        if len(command_parts) == 1:
            page_num = 1
        else:
            try:
                page_num = int(command_parts[1])
                if page_num < 1 or page_num > total_pages:
                    raise ValueError()
            except (IndexError, ValueError):
                if message.channel == target_channel_id:
                    return await message.channel.send(f"THAT'S NOT A PAGE NUMBER! USE A NUMBER BETWEEN 1 AND {total_pages} (INCLUSIVE).")
                else:
                    return await message.channel.send(f"That's not a page number! Use a number between 1 and {total_pages} (inclusive).")

        embed = create_commands_embed(page_num, total_pages, message)
        await message.channel.send(embed=embed)
        
    if random.random() < 0.001:
        if message.channel == target_channel_id:
            response = "THIS IS FORCING COMPELLED SPEECH!"
        else:
            response = "This is forcing compelled speech!"
        await message.channel.send(response)
        print(f"{client.get_user(user_id).name} got compelled speech'd")
        
    if random.random() < 0.0001:
        response = "De acuerdo con todas las leyes conocidas de la aviación,  Es gibt keine Möglichkeit eine Biene 到处跑，然后抛弃你。Je ne te ferais jamais pleurer, je ne te ferais jamais pleurer ang lalaking nasa salamin ay tumango- aspetta cazzo mi sono distratto. cosa stavo cantando di nuovo?"
        await message.channel.send(response)
        print(f"{client.get_user(user_id).name} got bee movie'd")
        
    data = load_data(file_path)  # Load data before processing the message
    
    user_id = str(message.author.id)
    
    if user_id not in data:
        data[user_id] = {"kekw_count": 0, "daily_kek_count": 0, "message_count": 0}
    elif "message_count" not in data[str(user_id)]:
        data[str(user_id)]["message_count"] = 0

    data[user_id]["message_count"] += 1
    save_data(data)

    if content.startswith("based"):
        if not message.author.bot and not content.startswith('!basedcount'):
            channel = message.channel
            replied_msg = None

            if message.reference is not None:
                replied_msg = await channel.fetch_message(message.reference.message_id)

            if replied_msg is not None and replied_msg.author.id != message.author.id:
                user_id = replied_msg.author.id
                if str(user_id) not in data:
                    data[str(user_id)] = {"count": 0}

                if isinstance(data[str(user_id)], int):
                    data[str(user_id)] = {"count": data[str(user_id)]}

                if "count" not in data[str(user_id)]:
                    data[str(user_id)]["count"] = 0

                # Check if the cooldown period has passed
                current_time = time.time()
                last_based_time = data[str(user_id)].get("last_based_time", 0)
                if current_time - last_based_time > cooldown_duration:
                    if str(user_id) not in data or "count" not in data[str(user_id)]:
                        data[str(user_id)] = {"count": 0, "cooldown": 0}
                    # Increment the count
                    data[str(user_id)]["count"] += 1
                    count = data[str(user_id)]["count"]
                    
                    # Print a message indicating the based count increment
                    user_name = client.get_user(user_id).name
                    reacted_user_name = client.get_user(message.author.id).name
                    print(f'{reacted_user_name} reacted with "based" to {user_name}')
                    
                    if count % send_message_interval == 0:
                        member = guild.get_member(replied_msg.author.id)
                        member_name = member.display_name if member else replied_msg.author.name
                        await message.channel.send(f"{member_name} reached a based count of {count}!")

                    
                    # Update the last_based_time
                    data[str(user_id)]["last_based_time"] = current_time
                    save_data(data)

#                current_time = time.time()
#                cooldown_end_time = cooldown_data.get(str(user_id), 0)
#                if current_time > cooldown_end_time:
#                    if str(user_id) not in data or "count" not in data[str(user_id)]:
#                        data[str(user_id)] = {"count": 0, "cooldown": 0}
#                    data[str(user_id)]["count"] += 1  # Increment the count
#                    cooldown_end_time = current_time + cooldown_duration  # Set the new cooldown end time
#                    cooldown_data[str(user_id)] = cooldown_end_time
            elif message.mentions:
                mentioned_user = message.mentions[0]  # Get the first mentioned user
                user_id = str(mentioned_user.id)


                if str(user_id) not in data:
                    data[str(user_id)] = {"count": 0}

                if isinstance(data[str(user_id)], int):
                    data[str(user_id)] = {"count": data[str(user_id)]}

                if "count" not in data[str(user_id)]:
                    data[str(user_id)]["count"] = 0

                # Check if the cooldown period has passed
                current_time = time.time()
                last_based_time = data[str(user_id)].get("last_based_time", 0)
                if current_time - last_based_time > cooldown_duration:
                    if str(user_id) not in data or "count" not in data[str(user_id)]:
                        data[str(user_id)] = {"count": 0, "cooldown": 0}
                    # Increment the count
                    data[str(user_id)]["count"] += 1
                    count = data[str(user_id)]["count"]
                    
                    # Print a message indicating the based count increment
                    user_name = client.get_user(user_id).name
                    reacted_user_name = client.get_user(message.author.id).name
                    print(f'{reacted_user_name} reacted with "based" to {user_name}')
                    
                    if count % send_message_interval == 0:
                        member = guild.get_member(replied_msg.author.id)
                        member_name = member.display_name if member else replied_msg.author.name
                        await message.channel.send(f"{member_name} reached a based count of {count}!")

                    
                    # Update the last_based_time
                    data[str(user_id)]["last_based_time"] = current_time

            elif replied_msg is not None and replied_msg.author.id == message.author.id:
                await message.channel.send("You cannot give based to yourself!")

            elif replied_msg is None:
                async for msg in channel.history(limit=2):
                    if msg.author.id != message.author.id:
                        user_id = msg.author.id
                        if str(user_id) not in data:
                            data[str(user_id)] = {"count": 0}

                        if isinstance(data[str(user_id)], int):
                            data[str(user_id)] = {"count": data[str(user_id)]}

                        if "count" not in data[str(user_id)]:
                            data[str(user_id)]["count"] = 0

                        # Check if the cooldown period has passed
                        current_time = time.time()
                        last_based_time = data[str(user_id)].get("last_based_time", 0)
                        if current_time - last_based_time > cooldown_duration:
                            # Increment the count
                            data[str(user_id)]["count"] += 1
                            count = data[str(user_id)]["count"]
                            
                            # Print a message indicating the based count increment
                            user_name = client.get_user(user_id).name
                            reacted_user_name = client.get_user(message.author.id).name
                            print(f'{reacted_user_name} reacted with "based" to {user_name}')
                    
                            # Check if the count is a multiple of 10
                            if count % send_message_interval == 0:
                                member = guild.get_member(user_id)
                                member_name = member.display_name if member else "Unknown Member"
                                await message.channel.send(f"{member_name} reached a based count of {count}!")

                                
                            # Update the last_based_time
                            data[str(user_id)]["last_based_time"] = current_time
                            save_data(data)

#                        current_time = time.time()
#                        cooldown_end_time = cooldown_data.get(str(user_id), 0)
#                        if current_time > cooldown_end_time:
#                            data[str(user_id)]["count"] += 1  # Increment the count
#                            cooldown_end_time = current_time + cooldown_duration  # Set the new cooldown end time
#                            cooldown_data[str(user_id)] = cooldown_end_time

                            break  # Skip incrementthe counter for the user who sent "based".
                            
    if content.startswith("!kpd"):
    
        data = load_data(file_path)
        
        # Get the target name from the command
        command_parts = message.content.split()
        if len(command_parts) > 1:
            target_name = " ".join(command_parts[1:])
            target_users = find_users_by_name(message.guild, target_name)
        else:
            # If no name is provided, use the message author as the target user
            target_users = [message.author]

        if not target_users:
            await message.channel.send("User not found in the server.")
            return

        if len(target_users) > 1:
            # If multiple users match the provided name, prompt the user to specify
            user_list = "\n".join([f"{i + 1}. {user.display_name if user.display_name else user.name}" for i, user in enumerate(target_users)])
            await message.channel.send(f"Multiple users match the name. Please specify by using the number:\n{user_list}")

            def check(m):
                return m.author == message.author and m.content.isdigit()

            try:
                response = await client.wait_for('message', check=check, timeout=30)
                user_choice = int(response.content)
                if 1 <= user_choice <= len(target_users):
                    target_user = target_users[user_choice - 1]
                else:
                    await message.channel.send("Invalid choice. Aborting.")
                    return
            except asyncio.TimeoutError:
                await message.channel.send("You took too long to respond. Aborting.")
                return
        else:
            target_user = target_users[0]

        # Get the user ID and user data from the JSON data
        user_id = str(target_user.id)
        user_data = data.setdefault(user_id, {"kekw_count": 0, "daily_kek_counts": [0] * 7})
        
        kek_per_day = get_kek_per_day_ratio(user_data)
        
        # Get the username or display name if available
        username = target_user.display_name if target_user.display_name else target_user.name

        # Send the kek per day ratio as a message
        if kek_per_day >= 5:
            await message.channel.send(f"{username} has a KPD of {kek_per_day:.2f}! They're a funny guy!")
        else:
            await message.channel.send(f"{username} has a KPD of {kek_per_day:.2f}.")

    if content.startswith('!kekratio'):
       # Get the target user's display name or username from the message content
        args = message.content.split()

        if len(args) == 1:  # If no username is mentioned, check the message author's ratio
            target_user = message.author
        else:
            target_user_name = " ".join(args[1:])  # Get the full name as provided in the message
            target_user = None

            # Create a list to store all matching users
            matching_users = []

            for member in message.guild.members:
                if target_user_name.lower() in member.display_name.lower() or target_user_name.lower() in member.name.lower():
                    matching_users.append(member)

            if not matching_users:
                await message.channel.send(f"User '{target_user_name}' not found.")
                return

            # If there is only one matching user, use that as the target user
            if len(matching_users) == 1:
                target_user = matching_users[0]
            else:
                # If there are multiple matching users, ask the user to select the correct one
                options = [f"{i+1}. {user.display_name if user.display_name != user.name else user.name}" for i, user in enumerate(matching_users)]
                options_str = "\n".join(options)
                await message.channel.send(f"Multiple users found. Please select the correct user:\n{options_str}")

                try:
                    response = await client.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author)
                    index = int(response.content) - 1
                    if 0 <= index < len(matching_users):
                        target_user = matching_users[index]
                except (ValueError, asyncio.TimeoutError):
                    await message.channel.send("Invalid selection or timeout. Please try again.")
                    return

            if target_user is None:
                await message.channel.send(f"User '{target_user_name}' not found.")
                return
                
        # Check if the target user is in the data
        data = load_data(file_path)
        target_id = str(target_user.id)
        if target_id not in data:
            await message.channel.send(f"{target_user.display_name} has no data.")
            return

        # Get the user's kekw count and message count
        kekw_count = data[str(target_user.id)]["kekw_count"]
        message_count = data[str(target_user.id)]["message_count"]

        # Calculate the kek-to-message ratio
        kek_ratio = round(kekw_count / message_count, 2) if message_count > 0 else 0
        
        target_name = target_user.display_name if target_user.display_name != target_user.name else target_user.name

        response_message = f"{target_name}, with a kek count of {kekw_count} and a message count of {message_count}, has a kek-to-message ratio of: {kek_ratio:.2f}."
        if kek_ratio >= 0.1:
            response_message += " Pretty good!"

        # Send the response message
        await message.channel.send(response_message)
        
    if content.startswith('!tts'):
        content = message.content[4:].strip()  # Extract the message content after the command and remove leading/trailing spaces
        if not content:
            content = 'Spooky text to speech noises!'
        await message.channel.send(content, tts=True)
        
    if content == '!startstopwatch':
        if message.author.id in stopwatch_data:
            await message.channel.send("Stopwatch already running for you!")
        else:
            stopwatch_data[message.author.id] = {
                'start_time': time.time(),
                'last_lap_time': 0,
                'laps': []
            }
            await message.channel.send("Stopwatch started!")

    if content == '!lapstopwatch':
        if message.author.id in stopwatch_data:
            current_time = time.time()
            start_time = stopwatch_data[message.author.id]['start_time']
            last_lap_time = stopwatch_data[message.author.id]['last_lap_time']
            lap_time = current_time - (start_time + last_lap_time)
            stopwatch_data[message.author.id]['last_lap_time'] += lap_time
            stopwatch_data[message.author.id]['laps'].append(lap_time)
            await message.channel.send(f"Lap recorded: {lap_time:.2f} seconds")
        else:
            await message.channel.send("No stopwatch running for you!")

    if content == '!stopstopwatch':
        if message.author.id in stopwatch_data:
            current_time = time.time()
            start_time = stopwatch_data[message.author.id]['start_time']
            last_lap_time = stopwatch_data[message.author.id]['last_lap_time']
            lap_time = current_time - (start_time + last_lap_time)
            stopwatch_data[message.author.id]['last_lap_time'] += lap_time
            stopwatch_data[message.author.id]['laps'].append(lap_time)
            total_time = sum(stopwatch_data[message.author.id]['laps'])
            del stopwatch_data[message.author.id]
            await message.channel.send(f"Stopwatch stopped! Total time: {total_time:.2f} seconds")
        else:
            await message.channel.send("No stopwatch running for you!")

    if content.startswith('!toiletbed'):
        response = 'I know that some people might think it\'s weird that I live in my toiletbed and also happen to be a moderator on the PCM sub, but let me tell you, it\'s the best thing ever! I get to play video games, watch anime, and be in charge of all the other users on the server, all the while living in the comfort of my toiletbed.\n\nI\'ve got my gaming setup down here, my computer where I can keep an eye on the PCM server, a mini fridge stocked with mountain Dew and Doritos, and of course my mom\'s home-cooked meals. Plus I\'ve got a comfy bet and all the snacks I could want, and let\'s be real, what more could a guy want?\n\nBeing a moderator is a full-time job. and I am always on the lookout for rule-breakers and trolls. I spend hours on the sub, making sure that everyone is following the rules and that everyone is having a good time- And if they don\'t follow the rules, I\'ll just kick them out. It\'s so cool to have that kind of power.\n\nBut, living in the toiletbed does have its perks. For one, I don\'t have to worry about noise levels or being too loud, and my mom is always around to bring me food and drinks. Plus, I\'m close to the laundry room so I can keep my clothes clean and impress my online friends.\n\nAll in all, being a subreddit moderator is the best thing ever and I wouldn\'t trade it for anything, even if I do happen to be living in my toiletbed. It\'s not the most glamorous life, but it\'s mine and I make the best of it. So, if you happen to be on our PCM subreddit, know that there\'s a toiletbed-dwelling moderator, who also happen to be a anime and Mountain Dew enthusiast, a bit socially awkward, probably never had a real-life girlfriend, is just a big kid at heard and happen to be a neckbeard, keeping an eye on things.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        
    if content.startswith('!ifthefunny'):
        response = 'Did you ever hear the tragedy of ironicForemanite The Funny? I thought not. It’s not a story the Channers would tell you. It’s a PCM legend. ironicForemanite was a Dark Lord of the keks, so powerful and so wise he could use the memes to influence the kekws to create supremacy… He had such a knowledge of the kek side that he could even keep the ones he cared about from being cringe. The kek side of the memes is a pathway to many abilities some consider to be unnatural. He became so kek… the only thing he was afraid of was losing his power, which eventually, of course, he did. Unfortunately, he became overzealous and radical, then his peers ANTIkek’d him in his sleep. Ironic. He could save others from cringe, but not himself.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        
    if content.startswith('fuck you'):
        responses = ['Fuck you too!', 'I\'m not your sister. Nor your mother.', 'Uno reverse card!']
        response = random.choice(responses)
        await message.channel.send(response)
    
    if content == 'say hi dum-e':
        await message.channel.send('Hi, DUM-E!')
        
    if content == 'say goodbye dum-e':
        file = discord.File('say_goodbye.png', filename='say_goodbye.png')
        await message.channel.send('Goodbye, DUM-E!')
        await message.channel.send(file=file)
                
    if content.startswith('!postingcontent'):
        response = 'Posting content again that was deemed rule breaking by one of us is defacto considered rule breaking. If you have questions as to why it was removed. You can ask via modmail and we will answer there. Just doing what op did, and technically you have done, breaks the rules by this virtue. That said, the rule breaking content is barely visible so I will defer to other mods before doing anything on this.\n\nBefore any of you snowflakes even try to go after my flair. I have been told this is operating procedure already when I joined as well as I wasn\'t the one to remove that post.\n\nEdit: Nice, reported for misinformation lmao. I don\'t do anything to my own reports but I was expecting this. Also, nice Reddit Cares whoever did it. I\'m sure you\'re smugging real nicely right now. Personally, I don\'t care'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
    
    if content.startswith('!dekekcomment'):
        response = 'I just dekek\'d your comment.\n\n# FAQ\n## What does this mean?\nThe amount of keks (laughs) on your leaderboard entry and discord account has decreased by one.\n\n## Why did you do this?\nThere are several reasons I may deem a comment to be unworthy of positive or neutral keks. These include, but are not limited to:\n\n* Rudeness towards other Discorders.\n* Spreading incorrect information,\n* Sarcasm not correctly flagged with a /s.\n\n## Am I banned from the Discord?\nNo - not yet. But you should refrain from making comments like this in the future. Otherwise I will be forced to issue an additional dekek, which may put your commenting and posting privileges in jeopardy.\n\n## I don\'t believe my comment deserved a dekek. Can you un-dekek it?\nSure, mistakes happen. But only in exceedingly rare circumstances will I undo a dekek. If you would like to issue an appeal, shoot me a private message explaining what I got wrong. I tend to respond to Discord PMs within several minutes. Do note, however, that over 99.9% of dekek appeals are rejected, and yours is likely no exception.\n\n## How can I prevent this from happening in the future?\nAccept the dekek and move on. But learn from this mistake: your behavior will not be tolerated on discord.com. I will continue to issue dekeks until you improve your conduct. Remember: keks are a privilege, not a right.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        
    if content.startswith('!balloon'):
        response = 'What\'s wrong with you\'re an idiot? You\'re a complete lying useless piece of shit. You\'ll never learn a lesson from my useless words. You don\'t even deserve another chance. Congratulations, you\'ve earned my useless words, and today I\'ll teach you the unironic skill of throwing words into air, and tomorrow I\'m going to teach you how to throw them in a balloon. Honestly, I hate the name balloon, but your dad made a nice name for herself. Just go through the instructions and you’ll be fine.\n\nThe only problem is that, now that you\'ve accomplished your task, the balloon will stop working. So instead of telling me you can\'t throw words into space if you don\'t stop working, tell me where you\'re going with the balloon, and that\'s exactly what my mom did.\n\nThe balloon will stop working if you don\'t stop working.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        
    if content.startswith('!product'):
        response = 'I\'ve personally seen a lot of very smart people try and figure out how to make a product better, and are often very successful, but the product is not there.\nThere are several common problems with products, the most common of which is that they may lead to a product being bland or blandishments. The more common problem is that the designer uses the product in a way which makes its user feel like they have to buy something other than a conventional plastic bottle and a box full of plastic.\nThere can be many reasons why brands have these problems, but this post explains a few of them so you can have a better grasp of them.\nHere\'s your solution:\n1) Remove product\nSo how does you remove it from your life-cycle? By making it taste better.\nIt\'s easy to make a product bland, but you can also make it look good. I highly recommend using a glass glass container with a bottle of water in it instead of a water bottle. If you\'re using a glass container, it should also serve as a barrier against liquids in the product.\n2) Add bottle to it\nI\'m an advocate for a glass container, and it\'s incredibly helpful to add some glass shards to the product. I use a bit of the sauce added by a bottle of water but it helps me get the whole recipe. Even if something isn\'t good, you can still add some of the sauce to your drink.\nThe glass bottle is great, but you don\'t have to use it. It can be handy for adding to sauces or flavoring your meal.\n3) Use a glass bottle as an alternative to a glass glass bottle\nA bottle is the standard for anything with reusable bottles, but there are tons of ways to make it functional.\nA lot of companies are very concerned with plastic bottles, so if you\'re considering putting a bottle on a glass bottle, you should be pretty aware of that by putting some glass bottles in it:\nGlass bottle is only reusable if you bring it into the kitchen because someone doesn\'t like it\n*Only* *a* bottle'
        response2 = 'The only thing they have against the bottle in a bottle will be that it will contain bacteria and viruses. Once you put the bottle in the wrong container, you will be wasting money and you will lose money on the bottles you put in it.\nThis also applies to reusable bottles, but you will often see people getting rid of bottles if they put them in a container that is larger than the bottle. So if you put a bottle in a glass bottle, you will actually be paying more for what you put into it.\n*I* *did* make one'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        await message.channel.send(response2)
    
    if content.startswith('!sofunny'):
        response = 'Omg this video is so funny, this video is so funny I laughed so hard, I laughed so hard I threw my phone, my stomach hurt, my nose started bleeding and I fell of of my bed and then I laughed so hard that the vibration from my laughter caused me to slide across the floor like some kind of fucked up caterpillar. Then I laughed so hard that I cried. Then I laughed so hard that I began flying. I flew threw the roof of my house and continued to fly up up up, up into the sky and I continued flying upwards until I went to outer space, I laughed so hard I went to outer space. Then I continued to laugh and the radiation from outer space started to disintegrate my body, my body disintegrated but I continued to laugh. Then I met God, God wasn’t a man or woman, God was two different cubes with different colors and I transcended God because I laughed so hard. I transcended God into a world of light and laughter. I could not stop laughing, all I could do is laughter now. I miss my friends, I miss my home I hope that I can see them again but I know that I never will, because I will never stop laughing I will laugh for eternity.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
    
    if content.startswith('!hacking'):
        response = 'okay, kid im done. I doubt you even have basic knowlege of hacking. I doul boot linux so i can run my scripts. you made a big mistake of replying to my comment without using a proxy, because i\'m already tracking youre ip. since ur so hacking iliterate, that means internet protocol. once i find your ip i can easily install a backdoor trojan into your pc, not to mention your email will be in my hands. dont even bother turning off your pc, because i can rout malware into your power system so i can turn your excuse of a computer on at any time. it might be a good time to cancel your credit card since ill have that too. if i wanted I could release your home information onto my secure irc chat and maybe if your unlucky someone will come knocking at your door. i\'d highly suggest you take your little comment about me back since i am no script kiddie. i know java and c++ fluently and make my own scripts and source code. because im a nice guy ill give you a chance to take it back. you have 4 hours in unix time, clock is ticking. ill let you know when the time is up by sending you an email to [redacted] which i aquired with a java program i just wrote. see you then'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
        
    if content.startswith('!authfascism'):
        response = 'auth is just fascism, or as I like to call it, trumpism'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
    
    if content.startswith('!navyseals'):
        response = 'What the fuck did you just fucking say about me, you little bitch? I\'ll have you know I graduated top of my class in the Navy Seals, and I\'ve been involved in numerous secret raids on Al-Quaeda, and I have over 300 confirmed kills. I am trained in gorilla warfare and I\'m the top sniper in the entire US armed forces. You are nothing to me but just another target. I will wipe you the fuck out with precision the likes of which has never been seen before on this Earth, mark my fucking words. You think you can get away with saying that shit to me over the Internet? Think again, fucker. As we speak I am contacting my secret network of spies across the USA and your IP is being traced right now so you better prepare for the storm, maggot. The storm that wipes out the pathetic little thing you call your life. You\'re fucking dead, kid. I can be anywhere, anytime, and I can kill you in over seven hundred ways, and that\'s just with my bare hands. Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the United States Marine Corps and I will use it to its full extent to wipe your miserable ass off the face of the continent, you little shit. If only you could have known what unholy retribution your little "clever" comment was about to bring down upon you, maybe you would have held your fucking tongue. But you couldn\'t, you didn\'t, and now you\'re paying the price, you goddamn idiot. I will shit fury all over you and you will drown in it. You\'re fucking dead, kiddo.'
        if message.mentions:
            response = f"{message.mentions[0].mention} {response}"
        await message.channel.send(response)
    
    if content.startswith('!shakeys'):
        file = discord.File('shakeys_ad.png', filename='shakeys_ad.png')
        await message.channel.send(file=file)
    
    if content.startswith('!bingo'):
        
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
                    leaderboard_message += f"{place} - {entry['name']} ({entry['victories']} wins)\n"

                # Send the leaderboard message to the Discord channel
                #await ctx.send(leaderboard_message)

            else:
                await message.channel.send(f"Error: Unable to fetch data from the API (Status Code: {response.status_code})")
    
        except Exception as e:
            await message.channel.send(f"An error occurred: {e}")
            
        response = "Go to https://basedcount-bingo.netlify.app/ and play with the official basedcount_bot bingo card!\n\nOnly people with the \"Bingo Player\" role can participate. If you wish to join, ask a Server Admin to give you the role.\n\nRules:\n* Log in with your Discord account.\n* A card has automatically been generated for you. You don't have to take screenshots of it nor send it in the bingo channel.\n* When someone ticks a box for the first time, a notification will be sent by the bot here on the bingo channel, as well as on the log on the site. You don't have to send a screenshot of the ticked box.\n* Get a bingo by marking off the board whenever certain events happen.\n* No cheesing the card by purposely doing the tiles on the board. It must happen naturally.\n* If it doesn't happen in the basedcount server, it doesn't count.\n* If it doesn't happen in Main (general-bots), it doesn't count.\n* I Exist and the admins get to determine what does or does not count as a hit on the bingo card if it's not obvious.\n* If someone gets a valid bingo, no more squares can be marked unless you noticed you missed a mark before.\n* If more than one people get a bingo at once, it counts as a win for all of them.\n* The current round lasts for one week, starting at the beginning of the round. If seven days have passed without a bingo, then the game is a draw and a new round with new cards begins.\n\n" + leaderboard_message
        
        await message.channel.send(response)
        # Ranks:
        # 5 wins - Bingo Professional
        # 10 wins - Bingo Master
        # 20 wins - Better Than Grandma
        # 50 wins - King/Queen of The Retirement Home
        
    if 'what browser' in content or 'browser' in content or 'browse' in content:
        if random.random() < 0.1:
            if message.author.id not in response_counter:
                response_counter[message.author.id] = 0
            response_counter[message.author.id] += 1
        
            delay_time = random.randint(30, 1800)
            print("waiting ", delay_time, "seconds")
            await asyncio.sleep(delay_time)
        
            for _ in range(response_counter[message.author.id]):
                await message.reply('I browse using Internet Explorer 9!')
                print(f"{client.get_user(user_id).name} got browser'd")
        
    if "drifting" in content or "drift" in content:
        if random.random() < 0.15:
            file = discord.File('multitrack_drifting.png', filename='multitrack_drifting.png')
            await message.channel.send(file=file)
            print(f"{client.get_user(user_id).name} got drifted")
            
    if "wrong" in content:
        if random.random() < 0.01:
            response = "https://media.discordapp.net/stickers/1174407116983894036?size=160&passthrough=false"
            await message.channel.send(response)
            print(f"{client.get_user(user_id).name} got drifted")
            
    if "joever" in content or content.startswith('its joever') or 'over' in content:
        if random.random() < 0.01:
            file = discord.File('joever.jpg', filename='joever.jpg')
            await message.channel.send(file=file)
            print(f"{client.get_user(user_id).name} got joever'd")
                
    if "swiss" in content or 'switzerland' in content:
        if random.random() < 0.01:
            response = "https://en.wikipedia.org/wiki/Switzerland_during_the_World_Wars#Financial_relationships_with_Nazi_Germany"
            await message.channel.send(response)
            print(f"{client.get_user(user_id).name} got swiss'd")
    
    if "lonely" in content or 'soulmate' in content or 'love' in content:
        if random.random() < 0.01:
            response = "Never worry about falling in love with someone who isn’t right for you. Taiwanese mail-order brides find foreign men like you irresistible!"
            await message.channel.send(response)
            print(f"{client.get_user(user_id).name} got mail order bride'd")
            
    if content.startswith('joewari da'):
        file = discord.File('joewari.jpg', filename='joewari.jpg')
        await message.channel.send(file=file)
        
    if str(message.author.id) == target_user_id:
        if random.random() < 0.001:
            response = 'Posting content again that was deemed rule breaking by one of us is defacto considered rule breaking. If you have questions as to why it was removed. You can ask via modmail and we will answer there. Just doing what op did, and technically you have done, breaks the rules by this virtue. That said, the rule breaking content is barely visible so I will defer to other mods before doing anything on this.\n\nBefore any of you snowflakes even try to go after my flair. I have been told this is operating procedure already when I joined as well as I wasn\'t the one to remove that post.\n\nEdit: Nice, reported for misinformation lmao. I don\'t do anything to my own reports but I was expecting this. Also, nice Reddit Cares whoever did it. I\'m sure you\'re smugging real nicely right now. Personally, I don\'t care'
            await message.channel.send(response)
            print(f"{client.get_user(user_id).name} got copypasta'd")
    
    if not isinstance(message.channel, discord.DMChannel):
        target_role = discord.utils.get(message.guild.roles, id=928987214917025832)
        if target_role in message.author.roles:
            if random.random() < 0.001:
                response = 'I know that some people might think it\'s weird that I live in my toiletbed and also happen to be a moderator on the PCM sub, but let me tell you, it\'s the best thing ever! I get to play video games, watch anime, and be in charge of all the other users on the server, all the while living in the comfort of my toiletbed.\n\nI\'ve got my gaming setup down here, my computer where I can keep an eye on the PCM server, a mini fridge stocked with mountain Dew and Doritos, and of course my mom\'s home-cooked meals. Plus I\'ve got a comfy bet and all the snacks I could want, and let\'s be real, what more could a guy want?\n\nBeing a moderator is a full-time job. and I am always on the lookout for rule-breakers and trolls. I spend hours on the sub, making sure that everyone is following the rules and that everyone is having a good time- And if they don\'t follow the rules, I\'ll just kick them out. It\'s so cool to have that kind of power.\n\nBut, living in the toiletbed does have its perks. For one, I don\'t have to worry about noise levels or being too loud, and my mom is always around to bring me food and drinks. Plus, I\'m close to the laundry room so I can keep my clothes clean and impress my online friends.\n\nAll in all, being a subreddit moderator is the best thing ever and I wouldn\'t trade it for anything, even if I do happen to be living in my toiletbed. It\'s not the most glamorous life, but it\'s mine and I make the best of it. So, if you happen to be on our PCM subreddit, know that there\'s a toiletbed-dwelling moderator, who also happen to be a anime and Mountain Dew enthusiast, a bit socially awkward, probably never had a real-life girlfriend, is just a big kid at heard and happen to be a neckbeard, keeping an eye on things.'
                await message.channel.send(response)
                
    if content.startswith("!unreact"):
        channel = message.channel
        last_messages = [msg async for msg in channel.history(limit=21)]
        
        for msg in last_messages[1:]:
            for reaction in msg.reactions:
                if reaction.me:
                    await reaction.remove(client.user)

        await message.channel.send("Reactions removed from the last 20 messages.")
        
    # Check if the message content prompts the bot to search for kekw reactions
#    if content.startswith('!check_kekw'):
#        channel = message.channel

        # Iterate through the past messages in the channel
#        async for past_message in channel.history(limit=None):
#            if past_message.id not in seen_messages:
#                # Check if the message is older than one day
#                now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
#                message_time = now - past_message.created_at
#                if message_time.days > 1 and message_time.days < 182:
#                    seen_messages.add(past_message.id)
#                    print("checked")
#                    # Iterate through the reactions on the message
#                    for reaction in past_message.reactions:
#                        # Check if the reaction is the kekw emoji
#                        if str(reaction.emoji) == "<:kekw:1029082555481337876>":
#                            # Get the users who reacted with kekw
#                            users = []
#                            async for user in reaction.users():
#                                users.append(user)
#                            for user in users:
#                                # Ignore bot reactions and the author's own reactions
#                                if user != client.user and user != past_message.author:
#                                    reacted_user = user
#                                    data = load_data(file_path)
#                                    if str(reacted_user.id) not in data:
#                                        data[str(reacted_user.id)] = {"count": 0, "kekw_count": 0}
#                                    if "kekw_count" not in data[str(reacted_user.id)]:
#                                        data[str(reacted_user.id)]["kekw_count"] = 0
#                                    data[str(reacted_user.id)]["kekw_count"] += 1
#                                    save_data(data)
#                                    print("incremented")
                                    

        
 #       # Save the updated data
 #       await message.channel.send("Kekws accounted for from the last 6 months.")
 #       save_data(data)
 #       save_seen_messages(seen_messages)
    if content.startswith('!basedcountpage'):
        # Load the data and sort based on kekw count
        data = load_data(file_path)
        count_leaderboard = sorted(data.items(), key=lambda x: (-x[1].get("count", 0), x[1].get("count", 0), message.guild.get_member(int(x[0])).display_name.lower() if message.guild.get_member(int(x[0])) else ""))
        
        count_leaderboard = [(user_id, user_data) for user_id, user_data in count_leaderboard if user_data.get("count", 0) != 0]

        # Set the page size
        page_size = 8

        # Calculate the total number of pages
        total_pages = (len(count_leaderboard) + page_size - 1) // page_size

        # Get the page number from the command
        try:
            command_parts = message.content.split()
            if len(command_parts) == 1:
                page_num = 1
            else:
                page_num = int(command_parts[1])
                if page_num < 1 or page_num > total_pages:
                    raise ValueError()
        except (IndexError, ValueError):
            return await message.channel.send(f"That's not a page number! Use a number between 1 and {total_pages} (inclusive).")

        # Get the start and end indices for the current page
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(count_leaderboard))

        # Create an embed for the leaderboard
        embed = discord.Embed(title="Based Count (Discord) Leaderboard", color=discord.Color.blue())
        embed.set_footer(text=f"Page {page_num}/{total_pages} | {len(count_leaderboard)} Users | use !basedcountpage [pagenum] to see other pages")

        # Add fields for each user's kekw count and rank
        for i, (user_id, user_data) in enumerate(count_leaderboard[start_idx:end_idx], start=start_idx + 1):
            member = message.guild.get_member(int(user_id))
            username = member.display_name if member else (await client.fetch_user(user_id)).name if await client.fetch_user(user_id) else "Unknown User"
            count = user_data["count"]
            rank = get_rank(count)

            if i == 1:
                username = f"🥇 {username} - Most Based User"
            elif i == 2:
                username = f"🥈 {username}"
            elif i == 3:
                username = f"🥉 {username}"
                
            if count > 0: 
                embed.add_field(name=username, value=f"{count} Baseds", inline=False)
            
        await message.channel.send(embed=embed)
            
    if content.startswith('!kekcountpage'):
        # Load the data and sort based on kekw count
        data = load_data(file_path)
        count_leaderboard = sorted(data.items(), key=lambda x: (-x[1].get("kekw_count", 0), x[1].get("kekw_count", 0), message.guild.get_member(int(x[0])).display_name.lower() if message.guild.get_member(int(x[0])) else ""))
        
        count_leaderboard = [(user_id, user_data) for user_id, user_data in count_leaderboard if user_data.get("kekw_count", 0) != 0]

        # Set the page size
        page_size = 8

        # Calculate the total number of pages
        total_pages = (len(count_leaderboard) + page_size - 1) // page_size

        # Get the page number from the command
        try:
            command_parts = message.content.split()
            if len(command_parts) == 1:
                page_num = 1
            else:
                page_num = int(command_parts[1])
                if page_num < 1 or page_num > total_pages:
                    raise ValueError()
        except (IndexError, ValueError):
            return await message.channel.send(f"That's not a page number! Use a number between 1 and {total_pages} (inclusive).")

        # Get the start and end indices for the current page
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(count_leaderboard))

        # Create an embed for the leaderboard
        embed = discord.Embed(title="Kekw Count Leaderboard", color=discord.Color.blue())
        embed.set_footer(text=f"Page {page_num}/{total_pages} | {len(count_leaderboard)} Users | use !kekcountpage [pagenum] to see other pages")

        # Add fields for each user's kekw count and rank
        for i, (user_id, user_data) in enumerate(count_leaderboard[start_idx:end_idx], start=start_idx + 1):
            member = message.guild.get_member(int(user_id))
            username = member.display_name if member else (await client.fetch_user(user_id)).name if await client.fetch_user(user_id) else "Unknown User"
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            if member:
                name = (await client.fetch_user(user_id)).name
                username = f"{username} ({name})"
            kekw_count = user_data["kekw_count"]
            rank = get_rank(kekw_count)

            if i == 1:
                username = f"🥇 {username} - Funniest User"
            elif i == 2:
                username = f"🥈 {username}"
            elif i == 3:
                username = f"🥉 {username}"

            embed.add_field(name=username, value=f"{kekw_count} Kekws\nRank: {rank}", inline=False)

        # Send the embed as a message
        await message.channel.send(embed=embed)
    
    if isinstance(message.channel, discord.DMChannel):
        # Check if the message is in a DM channel

        content = message.content
        if content.startswith('wordsinmymouth'):
            message_parts = content.split()

            guild_id = int(message_parts[1].strip('[]'))  # Extract the guild ID as an integer (remove the brackets)
            target = message_parts[2]  # Extract the target message ID or channel name
            message_to_send = ' '.join(message_parts[3:])

            if target.isdigit():
                target_id = int(target)
                # Find the guild based on the ID
                guild = client.get_guild(guild_id)

                if guild:
                    target_message = await find_target_message_by_id(guild, target_id)

                    if target_message:
                        # Reply to the target message
                        reply = await target_message.reply(message_to_send)

                        # Send a direct message to the specified user
                        specified_user = await client.fetch_user(bot_owner)
                        user = message.author
                        await specified_user.send(f"{user.name} ({user.id}) replied to a message in DUM-E:\n```{message_to_send}```\nReply ID: {reply.id}\nOriginal Message ID: {target_message.id}")
            else:
                # Find the guild based on the ID
                guild = client.get_guild(guild_id)

                if guild:
                    target_message = await find_target_message_by_channel(guild, target)

                    if target_message:
                        # Reply to the target message
                        reply = await target_message.channel.send(message_to_send)

                        # Send a direct message to the specified user
                        specified_user = await client.fetch_user(bot_owner)
                        user = message.author
                        await specified_user.send(f"{user.name} ({user.id}) replied to a message in DUM-E:\n```{message_to_send}```\nReply ID: {reply.id}\nOriginal Message ID: {target_message.id}")

async def find_target_message_by_id(guild, target_id):
    for channel in guild.text_channels:
        try:
            return await channel.fetch_message(target_id)
        except discord.NotFound:
            pass

    return None

async def find_target_message_by_channel(guild, target_channel):
    for channel in guild.text_channels:
        if channel.name.lower() == target_channel.lower():
            async for message in channel.history(limit=1):
                return message

    return None

@client.event
async def on_reaction_add(reaction, user):
    if user != client.user:  # Ignore the bot's own reactions
        message = reaction.message
        reacted_user = message.author

        await message.add_reaction(reaction.emoji)
            
@client.event
async def on_raw_reaction_add(payload):
    # Check if the reaction is the "kekw" emoji
    if str(payload.emoji) == "<:kekw:1029082555481337876>":
        # Get channel and message IDs from payload
        reacted_user_id = payload.user_id
        channel_id = payload.channel_id
        message_id = payload.message_id
        guild_id = payload.guild_id
        user_id = payload.user_id
        # Get data from IDs
        guild = client.get_guild(guild_id)
        channel = guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        user = guild.get_member(user_id)
        reacted_user = message.author
        reacted_user_id = str(reacted_user.id)
        reacting_user_id = str(payload.user_id)
        bingo_channel = discord.utils.get(message.guild.text_channels, name='bingo')
        rank_up = 0
        
        if reacting_user_id in (str(client.user.id), reacted_user_id):
            return
            
        if reacting_user_id == "1017211466186760254":
            return
            
        if reacted_user_id == 803320666354221056 and reacting_user_id == 235473795035430912:
            file = discord.File('reminder.png', filename='reminder.png')
            await message.channel.send(file=file)
        user_reactions = load_user_reactions(user_reactions_file)

        if user_id not in user_reactions.get(str(message_id), set()):
            # Increment kekw count
            data = load_data(file_path)
            user_reactions = load_user_reactions(user_reactions_file)
            seen_messages = load_seen_messages()
            if message_id not in seen_messages:
                if str(reacted_user.id) not in data:
                    data[str(reacted_user.id)] = {"kekw_count": 0, "rank": "Unknown Rank"}  # Initialize rank data if not present
            data.setdefault(reacted_user_id, {"kekw_count": 0})
            data[str(reacted_user.id)]["kekw_count"] += 1
            current_day = datetime.today().weekday()

            # Check if the current day is different from the last recorded day
            last_recorded_day = data[str(reacted_user.id)].get("last_recorded_day", current_day)
            if current_day != last_recorded_day:
                # Calculate the number of days between the current day and the last recorded day
                days_since_last_recorded = (current_day - last_recorded_day) % 7

                # Fill in the days with 0 keks in between
                for i in range(1, days_since_last_recorded):
                    day_index = (last_recorded_day + i) % 7
                    data[str(reacted_user.id)]["daily_kek_counts"][day_index] = 0

            # Update the current day's kek count
            data[str(reacted_user.id)]["daily_kek_counts"][current_day] += 1

            # Update the last recorded day for the user
            data[str(reacted_user.id)]["last_recorded_day"] = current_day

            # Save data
            save_data(data)
            save_user_reactions(user_reactions, user_reactions_file)

            kekw_count = data[str(reacted_user.id)]["kekw_count"]
            new_rank = get_rank(kekw_count)

            # Check if the user already has the rank
            current_rank = data[str(reacted_user.id)].get("rank", None)
            if new_rank != current_rank:
                user_ranks[reacted_user.id] = new_rank
                data[str(reacted_user.id)]["rank"] = new_rank

                # Send congratulation message only if the rank is new
                if new_rank == "The Entire Circus":
                    await channel.send(f"🎉🎉🎉 {reacted_user.mention} has shown themselves to be one of the funniest motherfuckers this side of basedcount and is now not just a clown, but The Entire Circus! 🎉🎉🎉")
                else:
                    await channel.send(f"{reacted_user.display_name} reached a kekw count milestone of {kekw_count} and received the rank '{new_rank}'!")
                rank_up = 1
        
            kekw_count = data[reacted_user_id]["kekw_count"]
            if kekw_count % 10 == 0 and rank_up != 1:
                response = f"{reacted_user.display_name} reached a kekw count milestone of {kekw_count}!"
                if kekw_count == 420:
                    response = f"{response} Nice."
                await channel.send(f"{response}")
            rank_up = 0
        
            save_data(data)
        
    if str(payload.emoji) == "<:ANTIkek:1135424631130570862>":
        # Get channel and message IDs from payload
        reacted_user_id = payload.user_id
        channel_id = payload.channel_id
        message_id = payload.message_id
        guild_id = payload.guild_id
        user_id = payload.user_id
        # Get data from IDs
        guild = client.get_guild(guild_id)
        channel = guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        user = guild.get_member(user_id)
        reacted_user = message.author
        reacted_user_id = str(reacted_user.id)
        reacting_user_id = str(payload.user_id)


        # Skip if author or bot
        if reacting_user_id == str(client.user.id):
            return
            
        if user.id in user_cooldowns and user_cooldowns[user.id] > datetime.now():
            print("a user tried antikeking too soon, get rekt scrub")
            return
            
        if reacting_user_id == "1017211466186760254":
            return

        # Decrement kek count
        data = load_data(file_path)
        user_reactions = load_user_reactions(user_reactions_file)
        if user_id not in user_reactions.get(str(message_id), set()):
            if str(reacted_user.id) in data:
                data[str(reacted_user.id)].setdefault("kekw_count", 0)
                data[str(reacted_user.id)]["kekw_count"] -= 1
                save_data(data)
                if random.random() < 0.01:
                    channel = client.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    reacted_user = await client.fetch_user(reacted_user_id)
                    response = 'I just dekek\'d your comment.\n\n# FAQ\n## What does this mean?\nThe amount of keks (laughs) on your leaderboard entry and discord account has decreased by one.\n\n## Why did you do this?\nThere are several reasons I may deem a comment to be unworthy of positive or neutral keks. These include, but are not limited to:\n\n* Rudeness towards other Discorders.\n* Spreading incorrect information,\n* Sarcasm not correctly flagged with a /s.\n\n## Am I banned from the Discord?\nNo - not yet. But you should refrain from making comments like this in the future. Otherwise I will be forced to issue an additional dekek, which may put your commenting and posting privileges in jeopardy.\n\n## I don\'t believe my comment deserved a dekek. Can you un-dekek it?\nSure, mistakes happen. But only in exceedingly rare circumstances will I undo a dekek. If you would like to issue an appeal, shoot me a private message explaining what I got wrong. I tend to respond to Discord PMs within several minutes. Do note, however, that over 99.9% of dekek appeals are rejected, and yours is likely no exception.\n\n## How can I prevent this from happening in the future?\nAccept the dekek and move on. But learn from this mistake: your behavior will not be tolerated on discord.com. I will continue to issue dekeks until you improve your conduct. Remember: keks are a privilege, not a right.'
                    response = f"{reacted_user.mention} {response}"
                    await message.channel.send(response)
                    
                save_user_reactions(user_reactions, user_reactions_file)

        # Update the last unkek timestamp for the user
            user_cooldowns[user.id] = datetime.now() + timedelta(hours=12)
                
    if str(payload.emoji) in ["<:kekw:1029082555481337876>", "<:ANTIkek:1135424631130570862>"]:
        # Get the channel object where you want to send the leaderboard
        leaderboard_channel = client.get_channel(1141830149176836246)
        guild = client.get_guild(payload.guild_id)
        reacting_member = guild.get_member(payload.user_id)
        
        reacting_user_display_name = reacting_member.display_name

        # Load the data and sort based on kekw count
        data = load_data(file_path)
        count_leaderboard = sorted(data.items(), key=lambda x: (-x[1].get("kekw_count", 0), x[1].get("kekw_count", 0), message.guild.get_member(int(x[0])).display_name.lower() if message.guild.get_member(int(x[0])) else ""))
        
        reacted_user_position = next((i for i, (user_id, _) in enumerate(count_leaderboard, start=1) if user_id == reacted_user_id), None)
        
        if reacted_user_position is not None:
            page_size = 8
            page_num = (reacted_user_position + page_size - 1) // page_size
        
        count_leaderboard = [(user_id, user_data) for user_id, user_data in count_leaderboard if user_data.get("kekw_count", 0) != 0]

        # Calculate the total number of pages
        total_pages = (len(count_leaderboard) + page_size - 1) // page_size

        # Get the start and end indices for the current page
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(count_leaderboard))

        # Create an embed for the leaderboard
        embed = discord.Embed(title="Kekw Count Leaderboard", color=discord.Color.blue())
        embed.set_footer(text=f"Page {page_num}/{total_pages} | {len(count_leaderboard)} Users | use !kekcountpage [pagenum] to see other pages")

        # Add fields for each user's kekw count and rank
        for i, (user_id, user_data) in enumerate(count_leaderboard[start_idx:end_idx], start=start_idx + 1):
            member = message.guild.get_member(int(user_id))
            username = member.display_name if member else (await client.fetch_user(user_id)).name if await client.fetch_user(user_id) else "Unknown User"
            if username == "laux3650atmylaurierdotca":
                username = "IF the Funny - Retired. Salute!"
            if member:
                name = (await client.fetch_user(user_id)).name
                username = f"{username} ({name})"
            kekw_count = user_data["kekw_count"]
            rank = get_rank(kekw_count)

            if i == 1:
                username = f"🥇 {username} - Funniest User"
            elif i == 2:
                username = f"🥈 {username}"
            elif i == 3:
                username = f"🥉 {username}"

            embed.add_field(name=username, value=f"{kekw_count} Kekws\nRank: {rank}", inline=False)

        # Send the embed as a message
        await leaderboard_channel.send(embed=embed)

        # After sending the leaderboard, you can also send a message indicating the kek or dekek
        await leaderboard_channel.send(f"{reacting_user_display_name} ({reacting_member}) reacted to {message.author.display_name}'s ({message.author}) [message]({message.jump_url}) with {'a kek' if str(payload.emoji) == '<:kekw:1029082555481337876>' else 'an antikek'}!")

client.run(bot_token)