import hikari
import lightbulb
import random
import string
import discord
from enum import Enum

from datetime import datetime, timezone, timedelta
import parsedatetime
from dateutil import parser as dateutil_parser
from lightbulb.ext import tasks
from typing import Optional
from database import db
from database import kek_counter
from database import gambling_list
from anydeck import AnyDeck

gambling_plugin = lightbulb.Plugin("Gambling")

poker_games = {}
hosts = []
poker_instances = {}
blackjack_instances = {}
used_game_ids = []
used_gamba_ids = []
gamble_instances = {}
active_bet_ids = []

def update_active_bet_ids():
    global active_bet_ids
    active_bet_ids = [bet["bet_id"] for bet in gambling_list.find({})]

def add_bet_id(bet_id):
    global active_bet_ids
    if bet_id not in active_bet_ids:
        active_bet_ids.append(bet_id)

def remove_bet_id(bet_id):
    global active_bet_ids
    if bet_id in active_bet_ids:
        active_bet_ids.remove(bet_id)

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
        
def generate_deck(card_values):
    deck = AnyDeck(shuffled=True,
        suits=('♣','♦','♥','♠'),
        cards=('Ace','2','3','4','5','6','7','8','9','10','Jack','Queen','King')
    )
    deck.dict_to_value(card_values)
    return deck
    

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
                debt['loan amount'] = round(new_loan_amount, 2)
                doc['total_debt'] += round(total_debt_increase, 2)
                modified = True
                

        # If any modification has been made, update the document in the database
        if modified:
            kek_counter.update_one({'_id': doc['_id']}, {'$set': {'loan_debt': doc['loan_debt']}})
            kek_counter.update_one({'_id': doc['_id']}, {'$set': {'total_debt': doc['total_debt']}})
            print("data modified")

@gambling_plugin.command
@lightbulb.command("bank", "Use the bank's services to supplement your finances.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def bank(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond("invoked bank")

@bank.child
@lightbulb.option("user", "User to wire money to.", type=hikari.User)
@lightbulb.option("type", "What type of currency to wire. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.option("amount", "Amount to wire.", type=float, min_value=1)
@lightbulb.command("wire", "Wire your Keks or Basedbucks to a fellow user.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def donate(ctx: lightbulb.SlashContext, user: hikari.User, amount: float, type: str) -> None:
    player_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    if player_data and player_data.get("kekbanned", False) and type == "Keks":
        dm_channel = await ctx.app.rest.create_dm_channel(ctx.author.id)
        await ctx.app.rest.create_message(
            channel=dm_channel.id,
            content=f"Sorry {ctx.author.mention}, you are banned from participating in the kekonomy.",
        )
        return
        
    if (type == 'Basedbucks' and amount > player_data["basedbucks"]) or (type == 'Keks' and amount > player_data["kek_count"]):
        await ctx.respond("You don't have enough to make that kind of transanction!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if amount <= 0:
        await ctx.respond("You can't donate zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.author.id == user.id:
        await ctx.respond("You can't donate to yourself!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    kek_counter.update_one(
            {"user_id": str(ctx.author.id)},
            {
                "$inc": {f"{'kek_count' if type == 'Keks' else 'basedbucks'}": amount * -1}
            },
            upsert=True,
        )
    kek_counter.update_one(
            {"user_id": str(user.id)},
            {
                "$inc": {f"{'kek_count' if type == 'Keks' else 'basedbucks'}": amount}
            },
            upsert=True,
        )
    await ctx.respond(f"{ctx.author.mention} wired {amount} {'Kek' if type == 'Keks' and amount == 1 else 'Keks' if type == 'Keks' else 'Basedbuck' if amount == 1 else 'Basedbucks'} to {user.mention}!")

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
            "$inc": {'total_debt': borrow, 'basedbucks': borrow},
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
@lightbulb.option("repay", "Amount of Basedbucks to repay.", type=float, min_value=1)
@lightbulb.command("repay", "Repay Basedbucks to the bank.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def repay_loan(ctx: lightbulb.SlashContext, repay: float) -> None:
    player_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    repay_value = repay
    if repay > player_data["basedbucks"]:
        await ctx.respond("You don't have enough Basedbucks to repay that much!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if repay <= 0:
        await ctx.respond("You can't repay zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    total_debt = player_data.get("total_debt", 0)
    if repay > total_debt:
        await ctx.respond("You're trying to repay more than your total debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    for debt in reversed(player_data["loan_debt"]):
        if debt["loan amount"] > 0:
            repayment_amount = min(repay, debt["loan amount"])  
            debt["loan amount"] -= repayment_amount  
            repay -= repayment_amount  
            total_debt -= repayment_amount 
            if debt["loan amount"] <= 0:
                player_data["loan_debt"].remove(debt) 
            if repay <= 0:
                break
            
    kek_counter.update_one(
        {"user_id": str(ctx.author.id)},
        {"$set": {"loan_debt": player_data["loan_debt"], "total_debt": total_debt}}
    )
    
    await ctx.respond(f"{ctx.author.mention} repaid {repay_value} Basedbucks to the bank!")

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

    embed = hikari.Embed(
        title=f"{ctx.author.username}'s Total Debt",
        description=f"Total Debt: {player_data['total_debt']} Basedbucks"
    )

    for i, (debt_amount, debt_time) in enumerate(zip(debts, debt_date), start=1):
        debt_time_str = discord.utils.format_dt(debt_time, "f") 
        embed.add_field(
            name=f"Debt {i}",
            value=f"Amount: {debt_amount}\nBorrowed at: {debt_time_str}",
            inline=False
        )

    await ctx.respond(embed=embed)

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

blackjack_values = {
    "Ace": 11,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "Jack": 10,
    "Queen": 10,
    "King": 10
}

class Blackjack:
    def __init__(self, table, host, ante, choice):
        self.table = table
        self.players = {}
        self.players_hand_messages = {}
        self.host = host
        self.dealerh = []
        self.dealer_hand_message = 0
        self.ante = ante
        self.insurance = 0
        self.insurance_play = False
        self.dealer_blackjack = False
        self.difficulty = 0 if choice == "Simple" else 1

        
    async def setup(self, ctx):
        self.deck = generate_deck(blackjack_values)
        await self.draw(ctx)
        
    def add_player(self, player, betting, wager):
        self.players[player] = {'hand': [], 'split_hand': [], 'playing_hand': 0, 'split_playing_hand': 0, 'wager': wager, 'betting': betting, 'insurance': 0, 'has_split': False, 'doubled_down': False, 'has_insured': False, 'has_stood': False, 'has_blackjack': False}
        
    def set_value(self, player):
        self.players[player]['playing_hand'] = 0
        for card in self.players[player]['hand']:
            self.players[player]['playing_hand'] += card.value
    
    async def draw(self, ctx):
        await ctx.app.rest.create_message(
            self.table,
            "Cards:\n"
        )
        for _ in range(2):
            for player in self.players:
                self.players[player]['hand'].append(self.deck.draw())
                self.set_value(player)
            self.dealerh.append(self.deck.draw())
        for player in self.players:
            self.players_hand_messages[player] = await ctx.app.rest.create_message(
                self.table,
                f"{player.mention}'s hand: {self.players[player]['hand'][0].suit}{self.players[player]['hand'][0].face}, {self.players[player]['hand'][1].suit}{self.players[player]['hand'][1].face}"
            )
        dealer_hand = await ctx.app.rest.create_message(
            self.table,
            f"Dealer's hand: {self.dealerh[0].suit}{self.dealerh[0].face}, ??"
        )
        if self.dealerh[0].face == "Ace" and self.difficulty == 1:
            await self.offer_insurance(ctx)
    
    def hit(self, player):
        self.players[player]['hand'].append(self.deck.draw())
        self.set_value(player)
        
    def stand(self, player):
        self.players[player]['has_stood'] = True
        
    def split(self, player):
        self.players[player]['has_split'] = True
        self.players[player]['split_hand'] = self.players[player]['hand'].pop()
        
    def double_down(self, player, bet):
        self.players[player]['doubled_down'] = True
        kek_counter.update_one(
            {"user_id": str(ctx.author.id)},
            {
                "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
            },
            upsert=True,
        )
        self.players[player][wager] += self.players[player][wager]
        self.hit()
        self.players[player]['has_stood'] = True
        
    def surrender(self, player):
        self.ante = self.ante/2
        
    async def offer_insurance(self, ctx):
        await ctx.app.rest.create_message(self.table, content= "The dealer has an Ace. Would you like to bet on some insurance? Type !insure or !sidebet with a value to bet insurance, or !continue to refuse.")
        
    def insurance(self, player, bet):
        self.insurance = bet
        
    def pass_turn(self, player):
        pass
        
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
async def hit(ctx: lightbulb.PrefixContext) -> None:
    for user, data in blackjack_instances.items():
        if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel) and ctx.get_channel() == data.get("Thread"):
            table = data.get("Table")
            if ctx.author in data.get("Players", []):
                table.hit(ctx.author)
                await ctx.respond(f"{ctx.author.mention} hit and drew a {table.players[ctx.author]['hand'][-1].suit}{table.players[ctx.author]['hand'][-1].face}.")
                return
    await ctx.respond("This command can only be used inside a blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)

@gambling_plugin.command
@lightbulb.command("stand", "End your turn in blackjack.")
@lightbulb.implements(lightbulb.PrefixCommand)
async def stand(ctx: lightbulb.PrefixContext) -> None:
    for user, data in blackjack_instances.items():
        if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel) and ctx.get_channel() == data.get("Thread"):
            table = data.get("Table")
            if ctx.author in data.get("Players", []):
                table.stand(ctx.author)
                await ctx.respond(f"{ctx.author.mention} stands and ends their turn.")
                return
    await ctx.respond("This command can only be used inside a blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
    
@gambling_plugin.command
@lightbulb.command("blackjackhelp", "Learn how to play blackjack.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def help(ctx: lightbulb.SlashContext) -> None:
    await ctx.respond(
        "Blackjack is a card game where the goal is to beat the dealer at getting as close to 21 points as possible with your hand.\n"
        "Each card is worth the value on their face, except for Jacks, Queens, and Kings, which are worth 10 points; and Aces which are worth either 1 or 11 points, whichever is closest to 21 points without going over.\n"
        "A Blackjack is when you get 21 points total in your hand. A Natural is when you get a Blackjack with your initial hand, consisting of an Ace and a 10 point card. A bust is when you go over 21 points in your hand.\n"
        "Winning a game gives a normal payout of 1:1. Winning with a Natural gives you a 3:2 payout.\n\n"
        "Controls:\n"
        "/blackjack open - Open a Blackjack table.\n"
        "/blackjack join - Join an open table. *Blackjack threads only.*\n"
        "/blackjack close - Close your Blackjack table. *Blackjack threads only.*\n"
        "!hit - Draw a card. *Blackjack threads only.*\n"
        "!stand - Keep your current hand as is. You can't make any other plays. *Blackjack threads only.*\n"
        "!split - Split your initial hand into two separate hands. Your second hand is given the same bet as your first hand, and is played separately, as if you have an extra turn. Splits are only possible with an initial hand with identical point values (e.g: a hand with two Aces, a hand with a Jack and Queen). *Blackjack threads only.*\n"
        "!double - Double down on your initial bet. Double your bet, but only hit once before being forced to stand. *Blackjack threads only.*\n"
        "!surrender - Surrender your hand instead of playing it. Lose 50% of your bet. *Blackjack threads only.*\n"
        "!insure/!sidebet [bet amount] - Insure your bet when the dealer draws an Ace. If you believe the dealer's face down card has a value of 10, you can set an insurance bet equal to or less than your original bet. If the dealer has a Blackjack with their initial hand, your insurance wins 2:1. Otherwise, the insurance is lost. *Blackjack threads only.*\n"
    )

        
@blackjack.child
@lightbulb.option("wager", "How much you want to initially bet.", type=int)
@lightbulb.option("difficulty", "How simple you want your game of blackjack to be.", type=str, choices=["Simple", "Complex"])
@lightbulb.option("betting", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.command("open", "Open a table and set up a quick game of blackjack.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def setup(ctx: lightbulb.SlashContext, wager: int, difficulty: str, betting: str) -> None:
    if not check_if_broke(ctx.author, betting):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.author.username not in blackjack_instances:
        message = await ctx.respond("Setting up table...")
        message = await message.message()
        thread = await ctx.app.rest.create_message_thread(ctx.channel_id, message, f"{ctx.author.username}'s Blackjack Table")
        table = Blackjack(thread, ctx.author, wager, difficulty)
        blackjack_instances[ctx.author.username] = {}
        table.add_player(ctx.author, wager, betting)
        await table.setup(ctx)
        blackjack_instances[ctx.author.username]["Thread"] = thread
        blackjack_instances[ctx.author.username]["Table"] = table
        blackjack_instances[ctx.author.username]["Players"] = []
        blackjack_instances[ctx.author.username]["Players"].append(ctx.author)
        blackjack_instances[ctx.author.username]["Original Message"] = message
        kek_counter.update_one(
            {"user_id": str(ctx.author.id)},
            {
                "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
            },
            upsert=True,
        )
        await ctx.app.rest.edit_message(ctx.channel_id, message, "Table created! You can now play blackjack here. Type \"!blackjackhelp\" or \"/blackjackhelp\" for details on how to play blackjack.")
    else:
        await ctx.respond("You already have a table open!", flags=hikari.MessageFlag.EPHEMERAL)
        
@blackjack.child
@lightbulb.option("wager", "How much you want to initially bet.", type=int)
@lightbulb.option("betting", "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.", type=str, choices=["Keks", "Basedbucks"])
@lightbulb.command("join", "Join a table to play a quick game of blackjack. Must be used in the blackjack table.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def join(ctx: lightbulb.SlashContext, wager: int, betting: str) -> None:
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
    author_username = ctx.author.username
    if author_username in blackjack_instances:
        thread = blackjack_instances[author_username].get("Thread")
        if isinstance(ctx.get_channel(), hikari.channels.GuildThreadChannel) and ctx.get_channel() == thread:
            message = blackjack_instances[author_username].get("Original Message")
            await ctx.app.rest.delete_channel(thread)
            await ctx.app.rest.edit_message(message.channel_id, message, "Table deleted. This message will delete itself soon.")
            await ctx.app.rest.delete_message(message.channel_id, message)
            del blackjack_instances[author_username]
            return
    await ctx.respond("This command can only be used inside your blackjack thread!", flags=hikari.MessageFlag.EPHEMERAL)
    

# Gamble

def count_for(bet_data):
    believers = []
    for better in bet_data["betters"]:
        if better["choice"] == "For":
            believers.append(better)
    return believers
    
def count_against(bet_data):
    nonbelievers = []
    for better in bet_data["betters"]:
        if better["choice"] == "Against":
            nonbelievers.append(better)
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
@lightbulb.option("deadline", "When the bet ends and resolution begins (e.g., '2024-06-01 15:00' or 'next Friday').", type=str)
@lightbulb.command("start", "Bet basedbucks or keks on something that might happen.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def bet_gamble(ctx: lightbulb.Context, bet: str, betting: str, wager: float, choice: str, deadline: str) -> None:
    if not check_if_broke(ctx.author, betting):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    user_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    if user_data and user_data.get("kekbanned", False) and betting == "Keks":
        dm_channel = await ctx.app.rest.create_dm_channel(ctx.author.id)
        await ctx.app.rest.create_message(
            channel=dm_channel.id,
            content=f"Sorry {ctx.author.mention}, you are banned from participating in the kekonomy.",
        )
        return

    # Parse the deadline using parsedatetime
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(deadline)
    
    if parse_status == 0:
        try:
            deadline_dt = dateutil_parser.parse(deadline)
        except ValueError:
            await ctx.respond("Invalid date format! Please try again with a valid date.", flags=hikari.MessageFlag.EPHEMERAL)
            return
    else:
        deadline_dt = datetime(*time_struct[:6])

    # Ensure deadline_dt is timezone-aware
    if deadline_dt.tzinfo is None:
        deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

    if deadline_dt <= datetime.now(timezone.utc):
        await ctx.respond("The deadline must be in the future!", flags=hikari.MessageFlag.EPHEMERAL)
        return

    gamba_id = generate_game_id()
    other_ids = gambling_list.find_one({"bet_id": gamba_id})
    is_unique = False if other_ids is not None and other_ids == gamba_id else True
    while not is_unique:
        gamba_id = generate_game_id()
        other_ids = gambling_list.find_one({"bet_id": gamba_id})
        is_unique = False if other_ids is not None and other_ids == gamba_id else True
    
    gamble_data = {
        "bet": bet,
        "bet_id": gamba_id,
        "bet_date": datetime.now(timezone.utc),
        "deadline": deadline_dt,
        "betting": betting,
        "betters": [
            {
                "name": ctx.author.username,
                "user_id": str(ctx.author.id),
                "wager": wager,
                "choice": choice
            }
        ],
        "total_pot": wager,
        "believer_pot": wager if choice == "For" else 0,
        "nonbeliever_pot": wager if choice == "Against" else 0
    }
    
    gambling_list.insert_one(gamble_data)
    add_bet_id(gamba_id)
    
    kek_counter.update_one(
        {"user_id": str(ctx.author.id)},
        {
            "$inc": {f"{'kek_count' if betting == 'Keks' else 'basedbucks'}": wager * -1}
        },
        upsert=True,
    )
    
    await ctx.respond(f'{ctx.author.mention} bet {wager} {betting} {"on" if choice == "For" else "against"} "{bet}"! The deadline is on {deadline_dt}. To join in on the bet, use /gamble join with the ID "{gamba_id}".')

@gamble.child
@lightbulb.option("id", "ID of the bet you want to join.", type=str)
@lightbulb.option("wager", "How much you wish to wager.", type=float)
@lightbulb.option("choice", "Whether or not you're betting on the thing happening or not.", type=str, choices=["For", "Against"])
@lightbulb.command("join", "Bet basedbucks or keks on a currently placed bet. Currency used depends on the original bet.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def wager_gamble(ctx: lightbulb.Context, id: str, wager: float, choice: str) -> None:
    bet_data = gambling_list.find_one({"bet_id": id})
    if not bet_data:
        await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    user_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    if user_data and user_data.get("kekbanned", False) and bet_data["betting"] == "Keks":
        dm_channel = await event.app.rest.create_dm_channel(user.id)
        await event.app.rest.create_message(
            channel=dm_channel.id,
            content=f"Sorry {ctx.author.mention}, you are banned from participating in the kekonomy.",
        )
        return
        
    for better in bet_data["betters"]:
        if better["name"] == ctx.author.username:
            await ctx.respond("You already have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)
            return

    if not check_if_broke(ctx.author, bet_data["betting"]):
        await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
        return

    new_wager = {
        "name": ctx.author.username,
        "user_id": str(ctx.author.id),
        "wager": wager,
        "choice": choice
    }
    gambling_list.update_one(
        {"bet_id": id},
        {"$push": {"betters": new_wager},
         "$inc": {"total_pot": wager,
                  "believer_pot" if choice == "For" else "nonbeliever_pot": wager}}
    )

    kek_counter.update_one(
        {"user_id": str(ctx.author.id)},
        {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": -wager}},
        upsert=True
    )

    await ctx.respond(f'{ctx.author.mention} bet {wager} {bet_data["betting"]} {"on" if choice == "For" else "against"} "{bet_data["bet"]}"! To join in on the bet, use /gamble join with the ID "{id}".')
            
@gamble.child
@lightbulb.option("id", "ID of the bet you want to join.", type=str)
@lightbulb.option("ante", "How much you wish to raise the bet by.", type=float)
@lightbulb.command("raise", "Raise your bet by a certain amount. Currency used depends on the original bet.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def raise_gamble(ctx: lightbulb.Context, id: str, ante: float) -> None:
    bet_data = gambling_list.find_one({"bet_id": id})
    if not bet_data:
        await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    user_data = kek_counter.find_one({"user_id": str(ctx.author.id)})
    if user_data and user_data.get("kekbanned", False) and bet_data["betting"] == "Keks":
        dm_channel = await event.app.rest.create_dm_channel(user.id)
        await event.app.rest.create_message(
            channel=dm_channel.id,
            content=f"Sorry {ctx.author.mention}, you are banned from participating in the kekonomy.",
        )
        return
    
    for better in bet_data["betters"]:
        if better["name"] == ctx.author.username:
            
            if not check_if_broke(ctx.author, bet_data["betting"]):
                await ctx.respond("You're in the red! You'll need to get some money first before you can go putting yourself in more debt!", flags=hikari.MessageFlag.EPHEMERAL)
                return
            
            better["wager"] += ante
            
            bet_data["total_pot"] += ante
            if better["choice"] == "For":
                bet_data["believer_pot"] += ante
            elif better["choice"] == "Against":
                bet_data["nonbeliever_pot"] += ante
                
            kek_counter.update_one(
                {"user_id": str(ctx.author.id)},
                {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": -ante}},
                upsert=True
            )
            
            gambling_list.update_one(
                {"bet_id": id},
                {"$set": {"betters": bet_data["betters"],
                          "total_pot": bet_data["total_pot"],
                          "believer_pot": bet_data["believer_pot"],
                          "nonbeliever_pot": bet_data["nonbeliever_pot"]}}
            )
            
            await ctx.respond(f'{ctx.author.mention} raised their bet by {ante}, making their total wager {better["wager"]} {bet_data["betting"]} {"on" if better["choice"] == "For" else "against"} "{bet_data["bet"]}" and the total pot {bet_data["total_pot"]}! To join in on the bet, use /gamble join with the ID "{id}".')
            return
        
    await ctx.respond("You don't have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)
            
@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet you want to cancel.", type=str)
@lightbulb.command("cancel", "Cancel a currently running bet. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def cancel_gamble(ctx: lightbulb.Context, id: str) -> None:
    bet_data = gambling_list.find_one({"bet_id": id})
    if not bet_data:
        await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    original = bet_data["bet"]
        
    for better in bet_data["betters"]:
        user_id = better["user_id"]
        wager = better["wager"]
        kek_counter.update_one(
            {"user_id": user_id},
            {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": wager}},
            upsert=True
        )
        
    await ctx.respond(f'Bet with ID {id} deleted! Original bet: "{original}". Wagers have been returned to all betters.')

    remove_bet_id(bet_data["bet_id"])
    gambling_list.delete_one({"bet_id": id})

@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet that succeeded.", type=str)
@lightbulb.command("succeed", "End a bet on the side of the believers. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def win_gamble(ctx: lightbulb.Context, id: str) -> None:
    bet_data = gambling_list.find_one({"bet_id": id})
    if not bet_data:
        await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    believers = count_for(bet_data)
    nonbelievers = count_against(bet_data)
    for better in bet_data["betters"]:
        if better["choice"] == "For":
            user_id = better["user_id"]
            wager = better["wager"]
            winnings = wager * 1.5 if bet_data["nonbeliever_pot"] == 0 else (wager + (bet_data["nonbeliever_pot"] / len(believers))) * 1.5
            kek_counter.update_one(
                {"user_id": user_id},
                {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": round(winnings, 2)}},
                upsert=True
            )
            
    await ctx.respond(
        f'Bet "{bet_data["bet"]}" is successful! '
        f'Believers win their original wagers '
        f'{"plus " if len(believers) > 0 else ""}'
        f'{bet_data["nonbeliever_pot"]/len(believers) if len(believers) > 0 and bet_data["nonbeliever_pot"] > 0 else bet_data["nonbeliever_pot"] * 1.5 if bet_data["nonbeliever_pot"] > 0 else ""} '
        f'{bet_data["betting"] if bet_data["nonbeliever_pot"] > 0 else "multiplied by 1.5"}. {"Non-Believers lose their wager." if bet_data["nonbeliever_pot"] > 0 else ""}\n\n'
        f'List of winners (Winnings):\n{"* ".join(player["name"] + " (" + str((bet_data["nonbeliever_pot"]/len(believers) * 1.5) + player["wager"]) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["nonbeliever_pot"] > 0 else "* ".join(player["name"] + " (" + str(player["wager"] * 1.5) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["nonbeliever_pot"] == 0 and len(believers) > 0 else "None."}\n\n'
        f'List of losers (Losings):\n{"* ".join(player["name"] + " (" + str(player["wager"] * -1) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["nonbeliever_pot"] > 0 else "None."}'
    )
    
    remove_bet_id(bet_data["bet_id"])
    gambling_list.delete_one({"bet_id": id})
    
@gamble.child
@lightbulb.add_checks(lightbulb.owner_only | lightbulb.has_roles(928983928289771560))
@lightbulb.option("id", "ID of the bet that failed.", type=str)
@lightbulb.command("fail", "End a bet on the side of the non-believers. Admins and bot owner only.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def lose_gamble(ctx: lightbulb.Context, id: str) -> None:
    bet_data = gambling_list.find_one({"bet_id": id})
    if not bet_data:
        await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
        return
        
    believers = count_for(bet_data)
    nonbelievers = count_against(bet_data)
    for better in bet_data["betters"]:
        if better["choice"] == "Against":
            user_id = better["user_id"]
            wager = better["wager"]
            winnings = wager * 1.5 if bet_data["believer_pot"] == 0 else (wager + (bet_data["believer_pot"] / len(nonbelievers))) * 1.5
            kek_counter.update_one(
                {"user_id": user_id},
                {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": winnings}},
                upsert=True
            )
            
    await ctx.respond(
        f'Bet "{bet_data["bet"]}" is unsuccessful! '
        f'Non-Believers win their original wagers '
        f'{"plus " if len(nonbelievers) > 0 else ""}'
        f'{bet_data["believer_pot"]/len(nonbelievers) if len(nonbelievers) > 0 and bet_data["believer_pot"] > 0 else bet_data["believer_pot"] * 1.5 if bet_data["believer_pot"] > 0 else ""} '
        f'{bet_data["betting"] if bet_data["believer_pot"] > 0 else "multiplied by 1.5"}. {"Believers lose their wager." if bet_data["believer_pot"] > 0 else ""}\n\n'
        f'List of winners (Winnings):\n{"* ".join(player["name"] + " (" + str((bet_data["believer_pot"]/len(nonbelievers) * 1.5) + player["wager"]) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["believer_pot"] > 0 else "* ".join(player["name"] + " (" + str(player["wager"] * 1.5) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["believer_pot"] == 0 and len(nonbelievers) > 0 else "None."}\n\n'
        f'List of losers (Losings):\n{"* ".join(player["name"] + " (" + str(player["wager"] * -1) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["believer_pot"] > 0 else "None."}'
    )
    
    remove_bet_id(bet_data["bet_id"])
    gambling_list.delete_one({"bet_id": id})
            
@gamble.child
@lightbulb.command("list", "Get a list of all current bets.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def list_gamble(ctx: lightbulb.Context) -> None:
    bets = gambling_list.find({})
    embed = hikari.Embed(
        title="Bets currently active:",
        color=hikari.Color.from_hex_code("#ffa500")
    )
    for bet in bets:
        believers = count_for(bet)
        nonbelievers = count_against(bet)
        believers_list = "\n".join([f"• {player['name']} ({player['wager']})" for player in believers])
        nonbelievers_list = "\n".join([f"• {player['name']} ({player['wager']})" for player in nonbelievers])
        
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon=ctx.author.display_avatar_url,
        )
        embed.add_field(
            name=f"Bet ID: {bet['bet_id']}",
            value=f"**Bet:** {bet['bet']}\n"
                  f"**Betting:** {bet['betting']}\n"
                  f"**Bet Date:** {bet['bet_date']}\n"
                  f"**Bet Deadline:** {bet['deadline']}\n",
            inline=False
        )
        embed.add_field(
            name=f"Believers ({len(believers)}):",
            value=f"{believers_list if believers_list else 'None'}",
            inline=True
        )
        embed.add_field(
            name=f"Non-Believers ({len(nonbelievers)}):",
            value=f"{nonbelievers_list if nonbelievers_list else 'None'}",
            inline=True
        )
        embed.add_field(
            name="Pot:",
            value=f"{bet['total_pot']} ({bet['believer_pot']} Believer Pot) ({bet['nonbeliever_pot']} Non-Believer Pot)",
            inline=False
        )
    await ctx.respond(embed=embed)
    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(gambling_plugin)
    update_active_bet_ids()