import hikari
import lightbulb
import random
import string
import gamble

from datetime import datetime
from datetime import timedelta
from lightbulb.ext import tasks
from typing import Optional
from database import db
from database import kek_counter

gambling_plugin = lightbulb.Plugin("Gambling")

poker_games = {}
hosts = []
poker_instances = {}
blackjack_instances = {}
used_game_ids = []
used_gamba_ids = []
gamble_instances = {}

@lightbulb.Check
# Defining the custom check function
def check_is_host(context: lightbulb.Context) -> bool:
    # Returns True if the author's ID is the same as the given one
    return context.author in hosts

def check_if_broke(player, betting) -> bool:
    player_data = kek_counter.find_one({"user_id": str(player.id)})
    if (player_data["basedbucks"] > 0 and betting == "Basedbucks") or (player_data["kek_count"] > 0 and betting == "Keks"):
        print("true")
        return True
    else:
        print("false")
        return False

def generate_game_id():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Banking

@tasks.task(d=1, auto_start=True)
async def appreciate_debt():
    query = {
        'loan_debt': {'$exists': True, '$ne': []}
    }
    # Find documents
    documents = kek_counter.find(query)
    for doc in documents:
        modified = False
        total_debt_increase = 0
        for debt in doc['loan_debt']:
            # Determine the latest date
            latest_date = max(debt['date'], debt['last_increase'])
            # Calculate new loan amount if it has been one week since the latest date
            if (datetime.now() - latest_date).days >= 7:
                debt['last_increase'] = datetime.now()
                new_loan_amount = debt['loan amount'] * (1 + debt['apr'])
                total_debt_increase += new_loan_amount - debt['loan amount']
                debt['loan amount'] = new_loan_amount
                doc['total_debt'] += total_debt_increase
                modified = True
                

        # If any modification has been made, update the document in the database
        if modified:
            kek_counter.update_one({'_id': doc['_id']}, {'$set': {'loan_debt': doc['loan_debt']}})
            print("data modified")
'''    debtors = kek_counter.find({"loan_debt": {"$exists": True, "$ne": []}})
    query = {
        'based_count.kek_counter.loan_debt': {'$exists': True, '$ne': []}
    }

    # Find documents
    result = collection.find(query)

    # Iterate over the results
    for doc in result:
        print(doc)
    for user in debtors:
        for debt in user['loan_debt']:
            
            print(user['loan_debt'])
            print(debt)
            one_week_later = user['loan_debt'][debt]['last_increase'] + timedelta(weeks=1) or user['loan_debt'][debt]['date'] + timedelta(weeks=1)
            if datetime.utcnow() >= one_week_later:
                debt_increase = user['loan_debt'][debt]['loan amount'] * user['loan_debt'][debt]['apr']
                kek_counter.update_one(
                    {"user_id": str(user['user_id'])},
                    {
                        "$inc": {'total_debt': debt_increase},
                        "$set":
                        {
                            'loan_debt': {
                                "date": user['loan_debt'][debt]['date'],
                                "loan amount": user['loan_debt'][debt]['loan amount'] + debt_increase,
                                "apr": user['loan_debt'][debt]['apr'],
                                "last_increase": datetime.utcnow()
                            },
                        }
                            
                    },
                    upsert=True,
                )'''

@gambling_plugin.command
@lightbulb.command("bank", "Use the bank's services to supplement your finances.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def bank(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond("invoked bank")

@bank.child
@lightbulb.option("user", "User to donate Basedbucks to.", type=hikari.User)
@lightbulb.option("donation", "Amount of Basedbucks to donate.", type=float, min_value=1)
@lightbulb.command("donate", "Donate your Basedbucks to a fellow user.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def donate(ctx: lightbulb.SlashContext, user: hikari.User, donation: float) -> None:
    player_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    if donation > player_data["basedbucks"]:
        await ctx.respond("You don't have enough money to make that kind of donation!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if donation <= 0:
        await ctx.respond("You can't donate zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.author.id == user.id:
        await ctx.respond("You can't donate to yourself!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    kek_counter.update_one(
            {"user_id": str(ctx.author.id)},
            {
                "$inc": {'basedbucks': donation * -1}
            },
            upsert=True,
        )
    kek_counter.update_one(
            {"user_id": str(user.id)},
            {
                "$inc": {'basedbucks': donation}
            },
            upsert=True,
        )
    await ctx.respond(f"{ctx.author.mention} donated {donation} Basedbucks to {user.mention}!")

@bank.child
@lightbulb.option("borrow", "Amount of Basedbucks to borrow.", type=float, min_value=1)
@lightbulb.command("loan", "Borrow Basedbucks from the bank.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def loan(ctx: lightbulb.SlashContext, borrow: float) -> None:
    player_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    apr = 0.03 if borrow < 5000 else 0.07
    if borrow <= 0:
        await ctx.respond("You can't borrow zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    kek_counter.update_one(
        {"user_id": str(ctx.author.id)},
        {
            "$inc": {'basedbucks': borrow},
            "$inc": {'total_debt': borrow},
            "$push": {
                        "loan_debt": {
                            "date": datetime.utcnow(),
                            "loan amount": borrow,
                            "apr": apr,
                            "last_increase": datetime.utcnow()
                        }
                    },
        },
        upsert=True,
        
    )
    await ctx.respond(f"{ctx.author.mention} borrowed {borrow} Basedbucks from the bank!")

@bank.child
@lightbulb.command("alldebt", "Check how much total debt you have.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def check_loan(ctx: lightbulb.SlashContext) -> None:
    player_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    debts = []
    debt_date = []
    for data in player_data['loan_debt']:
        debts.append(data['loan amount'])
        debt_date.append(data['date'])
    await ctx.respond(
        f"{ctx.author.mention}, your total debt is {player_data['total_debt']} Basedbucks.\n"
        "Your total debts:\n"
    )
    i = 1
    while i <= len(debts):
        await ctx.app.rest.create_message(ctx.channel_id, content = f'Debt {i} - Debt amount: {debts[i - 1]}, Borrowed at {debt_date[i - 1].strftime("%c")}')
        i += 1
# Poker
'''



class PokerGame:
    def __init__(self, table_name, host, player_max, bet):
        self.game_id = generate_game_id()
        while self.game_id in used_game_ids:
            self.game_id = generate_game_id()
        
        used_game_ids.append(self.game_id)
        self.table_name = table_name
        self.host = host
        self.players = {}
        self.player_max = player_max
        self.bet = bet
        self.deck = gamble.Deck()

    def start_game(self):
        self.deck.shuffle()
    
    def add_player(self, player):
        self.players[player] = {'hand': []}
    
    def deal_cards(self):
        for _ in range(2):
            for player_id in self.players:
                card = self.deck.draw()
                self.players[player]['hand'].append(card)
                
    async def set_flop(self):
        self.flop = [self.deck.draw() for __ in range(3)]
        await ctx.app.rest.create_message(ctx.channel_id, content = f'The flop: {self.flop[0]} {self.flop[1]} {self.flop[2]}')
    
    async def set_turn(self):
        self.turn = self.deck.draw()
        await ctx.app.rest.create_message(ctx.channel_id, content = f'The turn: {self.flop[0]} {self.flop[1]} {self.flop[2]} {self.turn}')
    
    async def set_river(self):
        self.river = self.deck.draw()
        await ctx.app.rest.create_message(ctx.channel_id, content = f'The river: {self.flop[0]} {self.flop[1]} {self.flop[2]} {self.turn} {self.river}')
    
    async def send_cards(self):
        for player in self.players:
            player.send(f"Your cards are: {self.players[player]['hand']}")

@gambling_plugin.command
@lightbulb.command("poker", "Play a quick game of poker.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def poker(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond("invoked poker")
    
@poker.child
@lightbulb.option("players", "Maximum amount of players to play with. Minimum 2, maximum 6.", type=int, min_value=2, max_value=6)
@lightbulb.option("bet", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.option("table_name", "What the table will be called.", type=str)
@lightbulb.command("host", "Start a game of poker. UNFINISHED", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def host_poker(ctx: lightbulb.Context, players: int, bet: str, table_name: str) -> None:
    player = await ctx.app.rest.fetch_member(ctx.guild_id, ctx.author)
    if poker_games:
        for game in poker_games:
            if player in poker_games[game]["Players"] or player in poker_games[game]["Host"]:
                await ctx.respond("You can't make a table while already hosting/are a player of another!", flags=hikari.MessageFlag.EPHEMERAL)
                break
            else:
                print(f"game hosted with {players} players with {bet} on the line")
                table = PokerGame(table_name, player, players, bet)
                poker_games[table_name] = {}
                poker_games[table_name]["Game_id"] = table.game_id
                poker_instances[table.game_id] = table
                poker_games[table_name]["Bet"] = bet
                poker_games[table_name]["Players"] = []
                poker_games[table_name]["Player Max"] = players
                poker_games[table_name]["Players"].append(player)
                poker_games[table_name]["Host"] = player
                hosts.append(player)
                table.add_player(ctx.author.username)
                await ctx.respond(f'Game "{table_name}" created. Use /poker join with the game id "{poker_games[table_name]["Game_id"]}" to join the table.')
    else:
        print(f"game hosted with {players} players with {bet} on the line")
        table = PokerGame(table_name, player, players, bet)
        poker_games[table_name] = {}
        poker_games[table_name]["Game_id"] = table.game_id
        poker_instances[table.game_id] = table
        poker_games[table_name]["Bet"] = bet
        poker_games[table_name]["Players"] = []
        poker_games[table_name]["Player Max"] = players
        poker_games[table_name]["Players"].append(player)
        poker_games[table_name]["Host"] = player
        hosts.append(player)
        table.add_player(ctx.author.username)
        await ctx.respond(f'Game "{table_name}" created. Use /poker join with the game id "{poker_games[table_name]["Game_id"]}" to join the table.')

@poker.child
@lightbulb.option("id", "The ID of the table you want to join.", type=str)
@lightbulb.command("join", "Join a game of poker. UNFINISHED", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def join_poker(ctx: lightbulb.Context, id: str) -> None:
    player = await ctx.app.rest.fetch_member(ctx.guild_id, ctx.author)
    for game in poker_games:
        if player in poker_games[game]["Players"] or player in poker_games[game]["Host"]:
            await ctx.respond("You can only join one table at a time!", flags=hikari.MessageFlag.EPHEMERAL)
        elif id in poker_games[game]["Game_id"]:
            if len(poker_games[game]["Players"]) == poker_games[game]["Player Max"]:
                await ctx.respond("That game is currently full!", flags=hikari.MessageFlag.EPHEMERAL)
            poker_games[game]["Players"].append(ctx.author.username)
            poker_instances[id].add_player(player)
            await ctx.respond("joined")
            
@poker.child
@lightbulb.add_checks(check_is_host)
@lightbulb.command("play", "Start a game of poker. Fails if you are not hosting. UNFINISHED")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def start_poker(ctx: lightbulb.Context) -> None:
    host = ctx.author
    game = 15
    await ctx.respond(f"Game {host} started!")
    
@poker.child
@lightbulb.command("games", "View currently hosted games. UNFINISHED")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def games_poker(ctx: lightbulb.Context) -> None:
    games = list(poker_games.keys())
    await ctx.respond("Games currently active:")
    for game in games:
        await ctx.app.rest.create_message(ctx.channel_id, content = f"Game: {game}, Game ID: {poker_games[game]['Game_id']}, Betting: {poker_games[game]['Bet']}, Players ({len(poker_games[game]['Players'])}/{poker_games[game]['Player Max']}): {', '.join(str(player) for player in poker_games[game]['Players'])}, Host: {poker_games[game]['Host']}")
'''
# Blackjack

class Blackjack:
    def __init__(self, table, host, ante, choice):
        self.table = table
        self.players = {}
        self.host = host
        self.dealerh = []
        self.ante = ante
        self.insurance = 0
        self.insurance_play = False
        self.dealer_blackjack = False
        self.difficulty = 0 if choice == "Simple" else 1
        
    def setup(self):
        self.deck = gamble.Deck()
        self.deck = self.deck.shuffle()
        self.initial()
        
    def add_player(self, player, betting, wager):
        self.players[player] = {'hand': [], 'split_hand': [], 'wager': wager, 'betting': betting, 'doubled_down': False}
    
    def draw(self, ctx):
        for _ in range(2):
            for player in self.players:
                self.players[player]['hand'].append(self.deck.draw())
            self.dealerh.append(self.deck.draw())
        ctx.respond(
            "Cards:\n"
            f"{player.mention}'s hand: {player['hand']}"
        )
        if self.dealerh[0].startswith("A") and difficulty == 1:
            self.offer_insurance()
    
    def hit(self,player):
        self.players[player]['hand'].append(self.deck.draw())
        
    def stand(self):
        self.dealer_play("stand")
        
    def split(self):
        self.hand2 = self.hand.pop()
        
    def double_down(self, bet):
        self.ante += bet
        self.hit()
        self.dealer_play("double")
        
    def surrender(self):
        self.ante = self.ante/2
        
    async def offer_insurance(self):
        await ctx.app.rest.create_message(ctx.channel_id, content= "The dealer has an Ace. Would you like to bet on some insurance? Type !insure or !sidebet with a value to bet insurance, or !continue to refuse.")
        
    def insurance(self, bet):
        self.insurance = bet
        
    def dealer_play(self, choice):
        choice = 0
        
    def payout(self, odds, difficulty):
        if difficulty == 1:
            if odds == "1:1":
                self.ante += self.ante
            
            elif odds == "3:2":
                self.ante += self.ante * 1.5
        else:
            self.ante += self.ante
                
@gambling_plugin.command
@lightbulb.command("blackjack", "Play a quick game of blackjack.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def blackjack(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond("invoked blackjack")
    
@gambling_plugin.command
@lightbulb.command("hit", "Get a card.")
@lightbulb.implements(lightbulb.PrefixCommand)
async def blackjack(ctx: lightbulb.PrefixContext) -> None:
    for user in blackjack_instances:
        if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel) and ctx.get_channel() in blackjack_instances[user]['Thread']:
            table = blackjack_instances[user]['Table']
            if ctx.author in blackjack_instances[user]['Players']:
                table.hit(ctx.author)
        else:
            await ctx.respond("This command can only be used inside a blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
        
@blackjack.child
@lightbulb.option("wager", "How much you want to initially bet.", type=int)
@lightbulb.option("difficulty", "How simple you want your game of blackjack to be.", type=str, choices=["Simple", "Complex"])
@lightbulb.option("betting", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.command("open", "Open a table and set up a quick game of blackjack.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def setup(ctx: lightbulb.SlashContext, ante: int, difficulty: str) -> None:
    if not check_if_broke(ctx.author, betting):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.author.username not in blackjack_instances:
        message = await ctx.respond("Setting up table...")
        message = await message.message()
        thread = await ctx.app.rest.create_message_thread(ctx.channel_id, message, f"{ctx.author.username}'s Blackjack Table")
        table = Blackjack(thread, ctx.author, ante, difficulty)
        blackjack_instances[ctx.author.username] = {}
        table.add_player(ctx.author)
        blackjack_instances[ctx.author.username]["Thread"] = thread
        blackjack_instances[ctx.author.username]["Table"] = table
        blackjack_instances[ctx.author.username]["Players"] = {}
        blackjack_instances[ctx.author.username]["Players"].append(ctx.author)
        blackjack_instances[ctx.author.username]["Original Message"] = message
        kek_counter.update_one(
            {"user_id": str(ctx.author.id)},
            {
                "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
            },
            upsert=True,
        )
        await ctx.app.rest.edit_message(ctx.channel_id, message, "Table created! You can now play blackjack here.")
    else:
        await ctx.respond("You already have a table open!", flags=hikari.MessageFlag.EPHEMERAL)
        
@blackjack.child
@lightbulb.option("wager", "How much you want to initially bet.", type=int)
@lightbulb.option("betting", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.command("join", "Join a table to play a quick game of blackjack. Must be used in the blackjack table.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def join(ctx: lightbulb.SlashContext, ante: int, difficulty: str, betting: int) -> None:
    if not check_if_broke(ctx.author, betting):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    for tables in blackjack_instances:
        if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel):
            if ctx.author.username not in blackjack_instances:
                if blackjack_instances[tables]["Thread"] == ctx.get_channel():
                    table = blackjack_instances[tables]["Table"]
                    blackjack_instances[ctx.author.username]["Players"].append(ctx.author)
                    table.add_player(ctx.author)
                    kek_counter.update_one(
                        {"user_id": str(ctx.author.id)},
                        {
                            "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
                        },
                        upsert=True,
                    )
                    await ctx.app.rest.create_message(ctx.channel_id, message, "Table created! You can now play blackjack here.")
                else:
                    await ctx.respond("This command can only be used inside a blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
            else:
                await ctx.respond("You cannot join another table with one still open!", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("This command can only be used inside a blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
    
@blackjack.child
@lightbulb.command("close", "Close the table. Must be used in your own blackjack table.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def close(ctx: lightbulb.SlashContext) -> None:
    if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel) and ctx.get_channel() in blackjack_instances[ctx.author.username]["Thread"]:
        message = blackjack_instances[ctx.author.username]["Original Message"]
        await ctx.app.rest.delete_channel(blackjack_instances[ctx.author.username]["Thread"])
        await ctx.app.rest.edit_message(message.channel_id, message, "Table deleted. This message will delete itself soon.")
        await ctx.app.rest.delete_message(message.channel_id, message)
        del blackjack_instances[ctx.author.username]
    else:
        await ctx.respond("This command can only be used inside your blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
    

# Gamble

def count_for(id):
    believers = []
    for player in gamble_instances[id]["Betters"]:
        if gamble_instances[id]["Betters"][player]["Choice"] == "For":
            believers.append(player)
    return believers
    
def count_against(id):
    nonbelievers = []
    for player in gamble_instances[id]["Betters"]:
        if gamble_instances[id]["Betters"][player]["Choice"] == "Against":
            nonbelievers.append(player)
    return nonbelievers

@gambling_plugin.command
@lightbulb.command("gamble", "Bet basedbucks or keks on something that might happen.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def gamble(ctx: lightbulb.SlashContext) -> None:
    """
    Bet on or against something happening. If nobody is betting against you, win 1.5x the wagered bet. If someone is betting against you, gain 1.5x their wager spread evenly among fellow betters.
    """
    await ctx.respond("invoked gamble")
    
@gamble.child
@lightbulb.option("bet", "What you are betting on happening.", type=str)
@lightbulb.option("betting", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.option("wager", "How much you wish to wager.", type=float)
@lightbulb.option("choice", "Whether or not you're betting on the thing happening or not.", type=str, choices=["For", "Against"])
@lightbulb.command("start", "Bet basedbucks or keks on something that might happen.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def bet_gamble(ctx: lightbulb.Context, bet: str, betting: str, wager: float, choice: str) -> None:
    if not check_if_broke(ctx.author, betting):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    gamba_id = generate_game_id()
    while gamba_id in used_gamba_ids:
        gamba_id = generate_game_id()
    gamble_instances[gamba_id] = {}
    gamble_instances[gamba_id]["Betters"] = {}
    gamble_instances[gamba_id]["Betters"][ctx.author] = {}
    gamble_instances[gamba_id]["Bet"] = bet
    gamble_instances[gamba_id]["Betting"] = betting
    gamble_instances[gamba_id]["Betters"][ctx.author]["Choice"] = choice
    gamble_instances[gamba_id]["Pot"] = wager
    gamble_instances[gamba_id]["Believer Pot"] = wager if choice == "For" else 0
    gamble_instances[gamba_id]["Non-Believer Pot"] = wager if choice == "Against" else 0
    gamble_instances[gamba_id]["Betters"][ctx.author]["Wager"] = wager
    kek_counter.update_one(
        {"user_id": str(ctx.author.id)},
        {
            "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
        },
        upsert=True,
    )
    await ctx.respond(f'{ctx.author.mention} bet {wager} {betting} {"on" if choice == "For" else "against"} "{bet}"! To join in on the bet, use /gamble join with the ID "{gamba_id}".')

@gamble.child
@lightbulb.option("id", "ID of the bet you want to join.", type=str)
@lightbulb.option("wager", "How much you wish to wager.", type=float)
@lightbulb.option("choice", "Whether or not you're betting on the thing happening or not.", type=str, choices=["For", "Against"])
@lightbulb.command("join", "Bet basedbucks or keks on a currently placed bet. Currency used depends on the original bet.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def wager_gamble(ctx: lightbulb.Context, id: str, wager: float, choice: str) -> None:
    for ids in gamble_instances:
        if id == ids:
            for betters in gamble_instances[id]["Betters"]:
                if ctx.author in gamble_instances[id]["Betters"]:
                    await ctx.respond("You already have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)
                    break
                else:
                    if not check_if_broke(ctx.author, gamble_instances[id]["Betting"]):
                        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
                        return
                    gamble_instances[id]["Betters"][ctx.author] = {}
                    gamble_instances[id]["Betters"][ctx.author]["Wager"] = wager
                    gamble_instances[id]["Betters"][ctx.author]["Choice"] = choice
                    gamble_instances[id]["Pot"] += wager
                    gamble_instances[id]["Believer Pot"] += wager if choice == "For" else 0
                    gamble_instances[id]["Non-Believer Pot"] += wager if choice == "Against" else 0
                    kek_counter.update_one(
                        {"user_id": str(ctx.author.id)},
                        {
                            "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": wager * -1}
                        },
                        upsert=True,
                    )
                    await ctx.respond(f'{ctx.author.mention} bet {wager} {gamble_instances[id]["Betting"]} {"on" if choice == "For" else "against"} "{gamble_instances[id]["Bet"]}"! To join in on the bet, use /gamble join with the ID "{id}".')
                break
        else:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            
@gamble.child
@lightbulb.option("id", "ID of the bet you want to join.", type=str)
@lightbulb.option("ante", "How much you wish to raise the bet by.", type=float)
@lightbulb.command("raise", "Raise your bet by a certain amount. Currency used depends on the original bet.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def raise_gamble(ctx: lightbulb.Context, id: str, ante: float) -> None:
    for ids in gamble_instances:
        if id == ids:
            for betters in gamble_instances[id]["Betters"]:
                if ctx.author in gamble_instances[id]["Betters"]:
                    gamble_instances[id]["Betters"][ctx.author]["Wager"] += ante
                    if not check_if_broke(ctx.author, gamble_instances[id]["Betting"]):
                        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
                        return
                    gamble_instances[id]["Pot"] += ante
                    gamble_instances[id]["Believer Pot"] += ante if gamble_instances[id]["Betters"][ctx.author]["Choice"] == "For" else 0
                    gamble_instances[id]["Non-Believer Pot"] += ante if gamble_instances[id]["Betters"][ctx.author]["Choice"] == "Against" else 0
                    kek_counter.update_one(
                        {"user_id": str(ctx.author.id)},
                        {
                            "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": ante * -1}
                        },
                        upsert=True,
                    )
                    await ctx.respond(f'{ctx.author.mention} raised their bet by {ante}, making their total wager {gamble_instances[id]["Betters"][ctx.author]["Wager"]} {gamble_instances[id]["Betting"]} {"on" if gamble_instances[id]["Betters"][ctx.author]["Choice"] == "For" else "against"} "{gamble_instances[id]["Bet"]}"! To join in on the bet, use /gamble join with the ID "{id}".')
                    
                    break
                else:
                    await ctx.respond("You don't have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)
                break
        else:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            
@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet you want to cancel.", type=str)
@lightbulb.command("cancel", "Cancel a currently running bet. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def cancel_gamble(ctx: lightbulb.Context, id: str) -> None:
    for ids in gamble_instances:
        if id == ids:
            original = gamble_instances[id]["Bet"]
            for players in gamble_instances[id]["Betters"]:
                player = await ctx.app.rest.fetch_member(ctx.guild_id, players.id)
                kek_counter.update_one(
                        {"user_id": str(player.id)},
                        {
                            "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": gamble_instances[id]["Betters"][players]["Wager"]}
                        },
                        upsert=True,
                    )
            await ctx.respond(f'Bet with ID {id} deleted! Original bet: "{original}". Wagers have been returned to all betters.')
            del gamble_instances[id]
            break
        else:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)

@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet that succeeded.", type=str)
@lightbulb.command("succeed", "End a bet on the side of the believers. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def win_gamble(ctx: lightbulb.Context, id: str) -> None:
    for ids in gamble_instances:
        if id == ids:
            believer_list = []
            nonbeliever_list = []
            nl = '\n'
            believers = count_for(id)
            nonbelievers = count_against(id)
            for player in believers:
                believer_list.append(player.username)
            for player in nonbelievers:
                nonbeliever_list.append(player.username)
            for players in gamble_instances[id]["Betters"]:
                if gamble_instances[id]["Betters"][players]["Choice"] == "For":
                    player = await ctx.app.rest.fetch_member(ctx.guild_id, players.id)
                    kek_counter.update_one(
                            {"user_id": str(player.id)},
                            {
                                "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": gamble_instances[id]["Betters"][players]["Wager"] * 1.5 if gamble_instances[id]['Non-Believer Pot'] == 0 else (gamble_instances[id]["Betters"][players]["Wager"] + (gamble_instances[id]['Non-Believer Pot']/len(believers))) * 1.5}
                            },
                            upsert=True,
                        )
                else:
                    player = await ctx.app.rest.fetch_member(ctx.guild_id, players)
                    kek_counter.update_one(
                            {"user_id": str(player.id)},
                            {
                                "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": gamble_instances[id]["Betters"][players]["Wager"] * -1}
                            },
                            upsert=True,
                        )
            await ctx.respond(
                f'Bet "{gamble_instances[id]["Bet"]}" is successful! '
                f'Believers win {(gamble_instances[id]["Non-Believer Pot"]/len(believers) if len(believers) > 0 and gamble_instances[id]["Non-Believer Pot"] > 0 else gamble_instances[id]["Non-Believer Pot"]) * 1.5 if gamble_instances[id]["Non-Believer Pot"] > 0 else "their original wagers"} '
                f'{gamble_instances[id]["Betting"] if gamble_instances[id]["Non-Believer Pot"] > 0 else "multiplied by 1.5"}. {"Non-Believers lose their wager." if gamble_instances[id]["Non-Believer Pot"] > 0 else ""}\n\n'
                f'List of winners (Winnings):\n{"* " + nl.join(player + " (" + str((gamble_instances[id]["Non-Believer Pot"]/len(believers) * 1.5) + gamble_instances[id]["Betters"][players]["Wager"]) + " " + gamble_instances[id]["Betting"] + ")" for player in believer_list) if gamble_instances[id]["Non-Believer Pot"] > 0 else "* " + nl.join(player + " (" + str(gamble_instances[id]["Betters"][players]["Wager"] * 1.5) + " " + gamble_instances[id]["Betting"] + ")" for player in believer_list)}\n'
                f'List of losers (Losings):\n{"* " + nl.join(player + " (" + str(gamble_instances[id]["Betters"][players]["Wager"] * -1) + " " + gamble_instances[id]["Betting"] + ")" for player in nonbeliever_list) if gamble_instances[id]["Non-Believer Pot"] > 0 else "None."}'
            )
            del gamble_instances[id]
            break
        else:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)

@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet that succeeded.", type=str)
@lightbulb.command("fail", "End a bet on the side of the non-believers. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def lose_gamble(ctx: lightbulb.Context, id: str) -> None:
    for ids in gamble_instances:
        if id == ids:
            believers = count_for(id)
            nonbelievers = count_against(id)
            for players in gamble_instances[id]["Betters"]:
                if gamble_instances[id]["Betters"][players]["Choice"] == "Against":
                    player = await ctx.app.rest.fetch_member(ctx.guild_id, players.id)
                    kek_counter.update_one(
                            {"user_id": str(player.id)},
                            {
                                "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": gamble_instances[id]["Betters"][players]["Wager"] * 1.5 if gamble_instances[id]['Believer Pot'] == 0 else (gamble_instances[id]["Betters"][players]["Wager"] + (gamble_instances[id]['Believer Pot']/len(nonbelievers))) * 1.5}
                            },
                            upsert=True,
                        )
                else:
                    player = await ctx.app.rest.fetch_member(ctx.guild_id, players)
                    kek_counter.update_one(
                            {"user_id": str(player.id)},
                            {
                                "$inc": {f"{'kek_count' if gamble_instances[id]['Betting'] == 'Keks' else 'basedbucks'}": gamble_instances[id]["Betters"][players]["Wager"] * -1}
                            },
                            upsert=True,
                        )
            await ctx.respond(
                f'Bet "{gamble_instances[id]["Bet"]}" is unsuccessful! '
                f'Non-Believers win {(gamble_instances[id]["Believer Pot"]/len(nonbelievers) if len(nonbelievers) > 0 and gamble_instances[id]["Believer Pot"] > 0 else gamble_instances[id]["Believer Pot"]) * 1.5 if gamble_instances[id]["Believer Pot"] > 0 else "their original wagers"} '
                f'{gamble_instances[id]["Betting"] if gamble_instances[id]["Believer Pot"] > 0 else "multiplied by 1.5"}. {"Believers lose their wager." if gamble_instances[id]["Non-Believer Pot"] > 0 else ""}\n\n'
                f'List of winners (Winnings):\n{"* " + nl.join(player + " (" + str((gamble_instances[id]["Believer Pot"]/len(believers) * 1.5) + gamble_instances[id]["Betters"][players]["Wager"]) + " " + gamble_instances[id]["Betting"] + ")" for player in nonbeliever_list) if gamble_instances[id]["Believer Pot"] > 0 else "* " + nl.join(player + " (" + str(gamble_instances[id]["Betters"][players]["Wager"] * 1.5) + " " + gamble_instances[id]["Betting"] + ")" for player in nonbeliever_list)}\n'
                f'List of losers (Losings):\n{"* " + nl.join(player + " (" + str(gamble_instances[id]["Betters"][players]["Wager"] * -1) + " " + gamble_instances[id]["Betting"] + ")" for player in believer_list) if gamble_instances[id]["Non-Believer Pot"] > 0 else "None."}'
            )
            del gamble_instances[id]
            break
        else:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            
@gamble.child
@lightbulb.command("list", "Get a list of all current bets.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def list_gamble(ctx: lightbulb.Context) -> None:
    games = list(gamble_instances.keys())
    await ctx.respond("Bets currently active:")
    for game in games:
        believers = count_for(game)
        nonbelievers = count_against(game)
        await ctx.app.rest.create_message(ctx.channel_id, content = f"Bet ID: {game}, Bet: {gamble_instances[game]['Bet']}, Betting: {gamble_instances[game]['Betting']}, Believers ({len(believers)}): {', '.join(str(player.username) for player in believers)}, Non-Believers ({len(nonbelievers)}): {', '.join(str(player) for player in nonbelievers)}, Pot: {gamble_instances[game]['Pot']} ({gamble_instances[game]['Believer Pot']} Believer Pot) ({gamble_instances[game]['Non-Believer Pot']} Non-Believer Pot)")
    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(gambling_plugin)