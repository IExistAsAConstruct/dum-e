import discord

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable the Members intent
intents.reactions = True

client = discord.Client(intents=intents)

user_ranks = {}

# Function to get the rank based on kekw count
def get_rank(kekw_count):
    ranks = [
        ("Occasionally Funny", 1),
        ("Jokester", 10),
        ("Stand Up Comedian", 25),
        ("Class Clown", 40),
        ("Amateur Clown", 100),
        ("Professional Clown", 140),
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

@client.event
async def handle_kekw_reaction(guild, payload):
    # Check if the reaction is the "kekw" emoji
    if str(payload.emoji) == "<:kekw:1029082555481337876>" or str(payload.emoji) == "<:kekw:1130828454980501575>":
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
        
        if reacting_user_id in (message.author.id, str(client.user.id)):
            return
            
        if reacted_user_id == 803320666354221056 and reacting_user_id == 235473795035430912:
            file = discord.File('reminder.png', filename='reminder.png')
            await message.channel.send(file=file)
            
        # Increment kekw count
        data = load_data(file_path)
        seen_messages = load_seen_messages()
        if message_id not in seen_messages:
            if str(reacted_user.id) not in data:
                data[str(reacted_user.id)] = {"kekw_count": 0, "rank": "Unknown Rank"}  # Initialize rank data if not present
        data[str(reacted_user.id)].setdefault("kekw_count", 0)
        data[str(reacted_user.id)]["kekw_count"] += 1

        kekw_count = data[str(reacted_user.id)]["kekw_count"]
        new_rank = get_rank(kekw_count)

        # Check if the user already has the rank
        current_rank = data[str(reacted_user.id)].get("rank", None)
        if new_rank != current_rank:
            user_ranks[reacted_user.id] = new_rank
            data[str(reacted_user.id)]["rank"] = new_rank
            
            await channel.send(f"{reacted_user.display_name} reached a kekw count milestone of {kekw_count} and received the rank '{new_rank}'!")
            rank_up = 1
        
        kekw_count = data[reacted_user_id]["kekw_count"]
        if kekw_count % 10 == 0 and rank_up != 1:
            await channel.send(f"{reacted_user.display_name} reached a kekw count milestone of {kekw_count}!")
        rank_up = 0
        
        save_data(data)