import asyncio
import io
from typing import List, Optional, Dict, Any

import anydeck
import hikari
import lightbulb
import random
import string

from hikari import Snowflakeish
from matplotlib import pyplot as plt

from database import kek_counter, gambling_list, stocks, stock_history

from datetime import datetime, timezone, timedelta
from lightbulb import Choice
from dateutil import parser as dateutil_parser
from anydeck import AnyDeck

import parsedatetime

loader = lightbulb.Loader()
OWNER_ID = 453445704690434049

@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
async def me_only(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    for role in ctx.member.role_ids:
        if ctx.user.id != OWNER_ID or role == 928983928289771560:
            await ctx.respond("You can't use this command!", flags=hikari.MessageFlag.EPHEMERAL)
            raise RuntimeError("You can't use this command!")

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

def check_if_broke(player, betting) -> bool:
    player_data = kek_counter.find_one({"user_id": str(player.id)})
    if (player_data["basedbucks"] > 0 and betting == "Basedbucks") or (player_data["kek_count"] > 0 and betting == "Keks"):
        return True
    else:
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

# Gambling Module

@loader.command
class BetGamble(
    lightbulb.SlashCommand,
    name="start-gamble",
    description="Bet basedbucks or keks on something that might happen."
):
    bet = lightbulb.string("bet", "What you are betting on happening.")
    betting = lightbulb.string(
        "betting",
        "What type of currency to bet. Keks affect kek count, Basedbucks are only used for gambling.",
        choices=[
            Choice("Keks", "Keks"),
            Choice("Basedbucks", "Basedbucks")
        ]
    )
    wager = lightbulb.number("wager", "How much you wish to wager.")
    choice = lightbulb.string(
        "choice",
        "Whether or not you're betting on the thing happening or not.",
        choices=[
            Choice("For", "For"),
            Choice("Against", "Against")
        ]
    )
    deadline = lightbulb.string(
        "deadline",
        "When the bet ends and resolution begins (e.g., '2024-06-01 15:00' or 'next Friday')."
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        is_unique:bool = False

        if not check_if_broke(ctx.member, self.betting):
            await ctx.respond(
                "You're in the red! You'll need to get some money first before you can go putting yourself in more debt!",
                flags=hikari.MessageFlag.EPHEMERAL)
            return

        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        if user_data and user_data.get("kekbanned", False) and self.betting == "Keks":
            dm_channel = await ctx.user.fetch_dm_channel()
            await ctx.client.app.rest.create_message(
                channel=dm_channel.id,
                content=f"Sorry {ctx.user.mention}, you are banned from participating in the kekonomy.",
            )
            return

        # Parse the deadline using parsedatetime
        cal = parsedatetime.Calendar()
        local_timezone = datetime.now().astimezone().tzinfo
        time_struct, parse_status = cal.parse(self.deadline)
        if parse_status == 0:
            try:
                deadline_dt = dateutil_parser.parse(self.deadline)
            except ValueError:
                await ctx.respond("Invalid date format! Please try again with a valid date.",
                                  flags=hikari.MessageFlag.EPHEMERAL)
                return
        else:
            deadline_dt = datetime(*time_struct[:6], tzinfo=local_timezone)

        # Ensure deadline_dt is timezone-aware
        if deadline_dt.tzinfo is None:
            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

        if deadline_dt <= datetime.now(timezone.utc):
            await ctx.respond("The deadline must be in the future!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        while not is_unique:
            gamble_id = generate_game_id()
            other_ids = gambling_list.find_one({"bet_id": gamble_id})
            is_unique = False if other_ids is not None and other_ids == gamble_id else True

        gamble_data = {
            "bet": self.bet,
            "bet_id": gamble_id,
            "bet_date": datetime.now(timezone.utc),
            "deadline": deadline_dt,
            "betting": self.betting,
            "betters": [
                {
                    "name": ctx.member.username,
                    "user_id": str(ctx.member.id),
                    "wager": round(self.wager, 2),
                    "choice": self.choice
                }
            ],
            "total_pot": round(self.wager, 2),
            "believer_pot": round(self.wager, 2) if self.choice == "For" else 0,
            "nonbeliever_pot": round(self.wager, 2) if self.choice == "Against" else 0
        }

        gambling_list.insert_one(gamble_data)

        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {f"{'kek_count' if self.betting == 'Keks' else 'basedbucks'}": round(self.wager * -1, 2)}
            },
            upsert=True,
        )

        await ctx.respond(
            f'{ctx.member.mention} bet {round(self.wager, 2)} {self.betting} {"on" if self.choice == "For" else "against"} "{self.bet}"! The deadline is on {deadline_dt}. To join in on the bet, use /join-gamble with the ID "{gamble_id}".'
        )

@loader.command
class JoinGamble(
    lightbulb.SlashCommand,
    name="join-gamble",
    description="Bet basedbucks or keks on a currently placed bet. Currency used depends on the original bet."
):
    id = lightbulb.string("id", "ID of the bet you want to join.")
    wager = lightbulb.number("wager", "How much you wish to wager.")
    choice = lightbulb.string(
        "choice",
        "Whether or not you're betting on the thing happening or not.",
        choices=[
            Choice("For", "For"),
            Choice("Against", "Against")
        ]
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        bet_data = gambling_list.find_one({"bet_id": self.id})
        if not bet_data:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        if user_data and user_data.get("kekbanned", False) and bet_data["betting"] == "Keks":
            dm_channel = await ctx.user.fetch_dm_channel()
            await ctx.client.app.rest.create_message(
                channel=dm_channel.id,
                content=f"Sorry {ctx.user.mention}, you are banned from participating in the kekonomy.",
            )
            return

        for better in bet_data["betters"]:
            if better["name"] == ctx.member.username:
                await ctx.respond("You already have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)
                return

        if not check_if_broke(ctx.member, bet_data["betting"]):
            await ctx.respond(
                "You're in the red! You'll need to get some money first before you can go putting yourself in more debt!",
                flags=hikari.MessageFlag.EPHEMERAL)
            return

        new_wager = {
            "name": ctx.member.username,
            "user_id": str(ctx.member.id),
            "wager": round(self.wager, 2),
            "choice": self.choice
        }
        gambling_list.update_one(
            {"bet_id": self.id},
            {
                "$push": {"betters": new_wager},
                "$inc": {"total_pot": round(self.wager, 2),
                         "believer_pot" if self.choice == "For" else "nonbeliever_pot": round(self.wager, 2)
                         }
            }
        )
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": round(self.wager * -1, 2)}
            },
            upsert=True
        )

        await ctx.respond(
            f'{ctx.member.mention} bet {round(self.wager, 2)} {bet_data["betting"]} {"on" if self.choice == "For" else "against"} "{bet_data["bet"]}"! To join in on the bet, use /join-gamble with the ID "{self.id}".'
        )

@loader.command
class RaiseGamble(
    lightbulb.SlashCommand,
    name="raise-gamble",
    description="Raise your bet by a certain amount. Currency used depends on the original bet."
):
    id = lightbulb.string("id", "ID of the bet you want to join.")
    wager = lightbulb.number("wager", "How much you wish to raise the bet by.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        bet_data = gambling_list.find_one({"bet_id": self.id})
        if not bet_data:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        if user_data and user_data.get("kekbanned", False) and bet_data["betting"] == "Keks":
            dm_channel = await ctx.user.fetch_dm_channel()
            await ctx.client.app.rest.create_message(
                channel=dm_channel.id,
                content=f"Sorry {ctx.user.mention}, you are banned from participating in the kekonomy.",
            )
            return

        for better in bet_data["betters"]:
            if better["name"] == ctx.member.username:

                if not check_if_broke(ctx.member, bet_data["betting"]):
                    await ctx.respond(
                        "You're in the red! You'll need to get some money first before you can go putting yourself in more debt!",
                        flags=hikari.MessageFlag.EPHEMERAL)
                    return

                better["wager"] += round(self.wager, 2)

                bet_data["total_pot"] += round(self.wager, 2)
                if better["choice"] == "For":
                    bet_data["believer_pot"] += round(self.wager, 2)
                elif better["choice"] == "Against":
                    bet_data["nonbeliever_pot"] += round(self.wager, 2)

                kek_counter.update_one(
                    {"user_id": str(ctx.member.id)},
                    {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": round(-self.wager, 2)}},
                    upsert=True
                )

                gambling_list.update_one(
                    {"bet_id": self.id},
                    {"$set": {"betters": bet_data["betters"],
                              "total_pot": bet_data["total_pot"],
                              "believer_pot": bet_data["believer_pot"],
                              "nonbeliever_pot": bet_data["nonbeliever_pot"]}}
                )

                await ctx.respond(
                    f'{ctx.member.mention} raised their bet by {round(self.wager, 2)}, making their total wager {better["wager"]} {bet_data["betting"]} {"on" if better["choice"] == "For" else "against"} "{bet_data["bet"]}" and the total pot {bet_data["total_pot"]}! To join in on the bet, use /join-gamble with the ID "{self.id}".'
                )
                return
        await ctx.respond("You don't have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)

@loader.command
class CancelGamble(
    lightbulb.SlashCommand,
    name="cancel-gamble",
    description="Cancel a currently running bet. Admins and bot owner only."
):
    id = lightbulb.string("id", "ID of the bet you want to cancel.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        await ctx.defer()

        bet_data = gambling_list.find_one({"bet_id": self.id})
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

        await ctx.respond(
            f'Bet with ID {self.id} deleted! Original bet: "{original}". Wagers have been returned to all betters.')

        gambling_list.delete_one({"bet_id": self.id})

@loader.command
class WinGamble(
    lightbulb.SlashCommand,
    name="succeed-gamble",
    description="End a bet on the side of the believers. Admins and bot owner only.",
):
    id = lightbulb.string("id", "ID of the bet that succeeded.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        await ctx.defer()

        bet_data = gambling_list.find_one({"bet_id": self.id})
        if not bet_data:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        believers = count_for(bet_data)
        nonbelievers = count_against(bet_data)
        for better in bet_data["betters"]:
            if better["choice"] == "For":
                user_id = better["user_id"]
                wager = better["wager"]
                winnings = round(wager * 1.5, 2) if bet_data["nonbeliever_pot"] == 0 else round((wager + (
                            bet_data["nonbeliever_pot"] / len(believers))) * 1.5, 2)
                kek_counter.update_one(
                    {"user_id": user_id},
                    {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": round(winnings, 2)}},
                    upsert=True
                )

        await ctx.respond(
            f'Bet "{bet_data["bet"]}" is successful! '
            f'Believers win their original wagers '
            f'{"plus " if len(believers) > 0 else ""}'
            f'{bet_data["nonbeliever_pot"] / len(believers) if len(believers) > 0 and bet_data["nonbeliever_pot"] > 0 else bet_data["nonbeliever_pot"] * 1.5 if bet_data["nonbeliever_pot"] > 0 else ""} '
            f'{bet_data["betting"] if bet_data["nonbeliever_pot"] > 0 else "multiplied by 1.5"}. {"Non-Believers lose their wager." if bet_data["nonbeliever_pot"] > 0 else ""}\n\n'
            f'List of winners (Winnings):\n'
            f'{"* ".join(player["name"] + " (" + str((bet_data["nonbeliever_pot"] / len(believers) * 1.5) + player["wager"]) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["nonbeliever_pot"] > 0 else "* ".join(player["name"] + " (" + str(player["wager"] * 1.5) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["nonbeliever_pot"] == 0 and len(believers) > 0 else "None."}\n\n'
            f'List of losers (Losings):\n'
            f'{"* ".join(player["name"] + " (" + str(player["wager"] * -1) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["nonbeliever_pot"] > 0 else "None."}'
        )

        gambling_list.delete_one({"bet_id": self.id})

@loader.command
class LoseGamble(
    lightbulb.SlashCommand,
    name="fail-gamble",
    description="End a bet on the side of the non-believers. Admins and bot owner only."
):
    id = lightbulb.string("id", "ID of the bet that failed.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):

        await ctx.defer()

        bet_data = gambling_list.find_one({"bet_id": self.id})
        if not bet_data:
            await ctx.respond("There is no bet with that ID!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        believers = count_for(bet_data)
        nonbelievers = count_against(bet_data)
        for better in bet_data["betters"]:
            if better["choice"] == "Against":
                user_id = better["user_id"]
                wager = better["wager"]
                winnings = round(wager * 1.5, 2) if bet_data["believer_pot"] == 0 else round((wager + (
                            bet_data["believer_pot"] / len(nonbelievers))) * 1.5, 2)
                kek_counter.update_one(
                    {"user_id": user_id},
                    {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": winnings}},
                    upsert=True
                )

        await ctx.respond(
            f'Bet "{bet_data["bet"]}" is unsuccessful! '
            f'Non-Believers win their original wagers '
            f'{"plus " if len(nonbelievers) > 0 else ""}'
            f'{bet_data["believer_pot"] / len(nonbelievers) if len(nonbelievers) > 0 and bet_data["believer_pot"] > 0 else bet_data["believer_pot"] * 1.5 if bet_data["believer_pot"] > 0 else ""} '
            f'{bet_data["betting"] if bet_data["believer_pot"] > 0 else "multiplied by 1.5"}. {"Believers lose their wager." if bet_data["believer_pot"] > 0 else ""}\n\n'
            f'List of winners (Winnings):\n'
            f'{"* ".join(player["name"] + " (" + str((bet_data["believer_pot"] / len(nonbelievers) * 1.5) + player["wager"]) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["believer_pot"] > 0 else "* ".join(player["name"] + " (" + str(player["wager"] * 1.5) + " " + bet_data["betting"] + ")" for player in nonbelievers) if bet_data["believer_pot"] == 0 and len(nonbelievers) > 0 else "None."}\n\n'
            f'List of losers (Losings):\n'
            f'{"* ".join(player["name"] + " (" + str(player["wager"] * -1) + " " + bet_data["betting"] + ")" for player in believers) if bet_data["believer_pot"] > 0 else "None."}'
        )

        gambling_list.delete_one({"bet_id": self.id})

@loader.command
class GetList(
    lightbulb.SlashCommand,
    name="list-gambles",
    description="Get a list of all current bets."
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
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
                text=f"Requested by {ctx.member}",
                icon=ctx.member.display_avatar_url,
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

# Blackjack Module
CARD_VALUES = {
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

OUTCOME_PAYOUTS = {
    "blackjack": 2.5,  # 3:2 payout for blackjack
    "win": 2.0,        # 1:1 payout for regular win
    "push": 1.0,       # Return original bet
    "surrender": 0.5,  # Return half the bet
    "loss": 0.0        # Lose entire bet
}


class Hand:
    """Represents a blackjack hand with cards and methods to evaluate its value."""

    def __init__(self, cards: List[anydeck.Card] = None):
        """Initialize a hand with optional starting cards."""
        self.cards = cards or []

    def add_card(self, card: anydeck.Card) -> None:
        """Add a card to the hand."""
        self.cards.append(card)

    @property
    def value(self) -> int:
        """Calculate the total value of the hand, accounting for Aces."""
        total = sum(card.value for card in self.cards)
        ace_count = sum(1 for card in self.cards if card.face == 'Ace')

        # Adjust aces from 11 to 1 as needed to avoid busting
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1

        return total

    @property
    def is_blackjack(self) -> bool:
        """Check if the hand is a natural blackjack (21 with exactly 2 cards)."""
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_busted(self) -> bool:
        """Check if the hand is busted (over 21)."""
        return self.value > 21

    @property
    def can_split(self) -> bool:
        """Check if the hand can be split (2 cards of same value)."""
        return (len(self.cards) == 2 and
                self.cards[0].value == self.cards[1].value)

    def to_string(self, hide_second_card: bool = False) -> str:
        """
        Convert the hand to a string representation.

        Args:
            hide_second_card: If True, the second card will be hidden (for dealer's initial hand)
        """
        if not self.cards:
            return "Empty hand"

        if hide_second_card and len(self.cards) > 1:
            visible_card = f"{self.cards[0].suit}{self.cards[0].face}"
            return f"{visible_card} 🂠"

        return " ".join(f"{card.suit}{card.face}" for card in self.cards)


class BlackjackGame:
    """Main class for managing a blackjack game session."""

    def __init__(self, player_id: int, bet_amount: int, message_id = Snowflakeish):
        """
        Initialize a new blackjack game.

        Args:
            player_id: The ID of the player
            bet_amount: The amount of basedbucks bet on the game
        """
        self.player_id = player_id
        self.initial_bet = bet_amount
        self.message_id = message_id

        # Initialize game state
        self.deck = self._create_deck()
        self.main_hand = Hand()
        self.split_hand = None  # Will be set if player splits
        self.dealer_hand = Hand()
        self.current_hand = self.main_hand  # Reference to the active hand

        # Bet tracking
        self.main_bet = bet_amount
        self.split_bet = 0
        self.insurance_bet = 0

        # Game state flags
        self.active_hand_index = 0  # 0 for main hand, 1 for split hand
        self.is_complete = False
        self.has_surrendered = False
        self.insurance_available = False
        self.insurance_resolved = False

        # Deal initial cards
        self._deal_initial_cards()

    def _create_deck(self) -> AnyDeck:
        """Create and shuffle a standard 52-card deck with blackjack values."""
        deck = AnyDeck(
            shuffled=True,
            suits=('♣', '♦', '♥', '♠'),
            cards=('Ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King')
        )
        deck.dict_to_value(CARD_VALUES)
        return deck

    def _deal_initial_cards(self) -> None:
        """Deal the initial two cards to player and dealer."""
        for _ in range(2):
            self.main_hand.add_card(self.deck.draw())
            self.dealer_hand.add_card(self.deck.draw())

        # Check if insurance is available (dealer's up-card is an Ace)
        self.insurance_available = self.dealer_hand.cards[0].face == 'Ace'

        # Check for immediate game end conditions (player or dealer blackjack)
        self._check_initial_blackjacks()

    def _check_initial_blackjacks(self) -> None:
        """Check for blackjack in the initial deal and update game state accordingly."""
        player_blackjack = self.main_hand.is_blackjack
        dealer_blackjack = self.dealer_hand.is_blackjack

        if player_blackjack or dealer_blackjack:
            self.is_complete = True

    def hit(self) -> anydeck.Card:
        """
        Add a card to the current hand.

        Returns:
            The card that was drawn.
        """
        card = self.deck.draw()
        self.current_hand.add_card(card)

        # Check if the hand is busted
        if self.current_hand.is_busted:
            # If this is the first hand in a split, move to the second hand
            if self.split_hand and self.active_hand_index == 0:
                self.switch_to_split_hand()
            else:
                # Game is complete if main hand busts or both hands bust
                self.is_complete = True

        return card

    def stand(self) -> None:
        """Stand on the current hand, potentially switching to split hand or ending the game."""
        # If this is the first hand in a split, move to the second hand
        if self.split_hand and self.active_hand_index == 0:
            self.switch_to_split_hand()
        else:
            # Player's turn is over, resolve dealer's hand
            self._play_dealer_hand()
            self.is_complete = True

    def double_down(self) -> anydeck.Card:
        """
        Double the bet on the current hand and draw exactly one card.

        Returns:
            The card that was drawn.
        """
        # Double the appropriate bet
        if self.active_hand_index == 0:
            self.main_bet *= 2
        else:
            self.split_bet *= 2

        # Draw one card
        card = self.hit()

        # If the hand didn't bust, stand automatically
        if not self.current_hand.is_busted:
            self.stand()

        return card

    def split(self) -> bool:
        """
        Split the player's hand into two separate hands.

        Returns:
            True if the split was successful, False otherwise.
        """
        # Check if split is possible
        if not self.main_hand.can_split or self.split_hand is not None:
            return False

        # Create the split hand with the second card from the main hand
        self.split_hand = Hand([self.main_hand.cards.pop()])

        # Add a new card to each hand
        self.main_hand.add_card(self.deck.draw())
        self.split_hand.add_card(self.deck.draw())

        # Set the split bet equal to the main bet
        self.split_bet = self.main_bet

        # Ensure current hand is still the main hand
        self.current_hand = self.main_hand
        self.active_hand_index = 0

        return True

    def surrender(self) -> bool:
        """
        Surrender the hand, recovering half the bet.

        Returns:
            True if surrender was successful, False if not allowed.
        """
        # Can only surrender on initial hand
        if len(self.main_hand.cards) > 2 or self.split_hand is not None:
            return False

        self.has_surrendered = True
        self.is_complete = True
        return True

    def take_insurance(self) -> bool:
        """
        Take insurance against dealer blackjack.

        Returns:
            True if insurance was successful, False if not available.
        """
        if not self.insurance_available or self.insurance_resolved:
            return False

        # Insurance bet is half the original bet
        self.insurance_bet = self.main_bet // 2

        # If dealer has blackjack, resolve insurance immediately
        if self.dealer_hand.is_blackjack:
            self.insurance_resolved = True
            self.is_complete = True

        return True

    def switch_to_split_hand(self) -> None:
        """Switch the active hand to the split hand."""
        if self.split_hand:
            self.current_hand = self.split_hand
            self.active_hand_index = 1

    def _play_dealer_hand(self) -> None:
        """Play the dealer's hand according to standard rules (hit on 16, stand on 17)."""
        # Dealer only plays if player hasn't busted all hands
        if (self.main_hand.is_busted and
                (self.split_hand is None or self.split_hand.is_busted)):
            return

        # Dealer hits until reaching at least 17
        while self.dealer_hand.value < 17:
            self.dealer_hand.add_card(self.deck.draw())

    def get_outcome(self) -> Dict[str, Any]:
        """
        Determine the game outcome and calculate payouts.

        Returns:
            Dictionary containing outcome details and payout information.
        """
        results = {
            "main_hand": self._get_hand_outcome(self.main_hand, self.main_bet),
            "split_hand": None,
            "insurance": None,
            "total_payout": 0
        }

        # Calculate main hand payout
        main_payout = results["main_hand"]["payout"]

        # Calculate split hand payout if applicable
        split_payout = 0
        if self.split_hand:
            results["split_hand"] = self._get_hand_outcome(self.split_hand, self.split_bet)
            split_payout = results["split_hand"]["payout"]

        # Calculate insurance payout if applicable
        insurance_payout = 0
        if self.insurance_bet > 0:
            if self.dealer_hand.is_blackjack:
                # Insurance pays 2:1
                insurance_payout = self.insurance_bet * 2
                results["insurance"] = {
                    "outcome": "win",
                    "bet": self.insurance_bet,
                    "payout": insurance_payout
                }
            else:
                results["insurance"] = {
                    "outcome": "loss",
                    "bet": self.insurance_bet,
                    "payout": 0
                }

        # Calculate total payout
        results["total_payout"] = main_payout + split_payout + insurance_payout

        return results

    def _get_hand_outcome(self, hand: Hand, bet: int) -> Dict[str, Any]:
        """
        Determine the outcome for a specific hand.

        Args:
            hand: The hand to evaluate
            bet: The bet amount for this hand

        Returns:
            Dictionary with outcome details
        """
        # Handle surrender
        if self.has_surrendered:
            return {
                "outcome": "surrender",
                "message": "Surrender! Half your bet is returned. 🏳️",
                "bet": bet,
                "payout": bet * OUTCOME_PAYOUTS["surrender"]
            }

        # Handle bust
        if hand.is_busted:
            return {
                "outcome": "loss",
                "message": "Bust! You went over 21. Dealer wins. 💸",
                "bet": bet,
                "payout": 0
            }

        # Handle player blackjack
        if hand.is_blackjack and not self.dealer_hand.is_blackjack:
            return {
                "outcome": "blackjack",
                "message": "Blackjack! Payout is 3:2. 💰💰💰",
                "bet": bet,
                "payout": bet * OUTCOME_PAYOUTS["blackjack"]
            }

        # Handle dealer blackjack
        if self.dealer_hand.is_blackjack and not hand.is_blackjack:
            return {
                "outcome": "loss",
                "message": "Dealer has Blackjack! You lose. 💸",
                "bet": bet,
                "payout": 0
            }

        # Handle push with blackjack
        if hand.is_blackjack and self.dealer_hand.is_blackjack:
            return {
                "outcome": "push",
                "message": "Both have Blackjack! It's a push. 🔄",
                "bet": bet,
                "payout": bet
            }

        # Handle dealer bust
        if self.dealer_hand.is_busted:
            return {
                "outcome": "win",
                "message": "Dealer busts! You win. 💰",
                "bet": bet,
                "payout": bet * OUTCOME_PAYOUTS["win"]
            }

        # Compare hand values for regular outcomes
        if hand.value > self.dealer_hand.value:
            return {
                "outcome": "win",
                "message": "You win! Your hand beats the dealer. 💰",
                "bet": bet,
                "payout": bet * OUTCOME_PAYOUTS["win"]
            }
        elif hand.value < self.dealer_hand.value:
            return {
                "outcome": "loss",
                "message": "Dealer wins! Your hand loses. 💸",
                "bet": bet,
                "payout": 0
            }
        else:
            return {
                "outcome": "push",
                "message": "Push! It's a tie. Your bet is returned. 🔄",
                "bet": bet,
                "payout": bet
            }

    def can_double_down(self) -> bool:
        """Check if the player can double down on the current hand."""
        # Can only double down on initial 2 cards
        return len(self.current_hand.cards) == 2

    def can_surrender(self) -> bool:
        """Check if the player can surrender."""
        # Can only surrender on initial hand with no split
        return (len(self.main_hand.cards) == 2 and
                self.split_hand is None and
                not self.is_complete)

    def create_game_embed(self, reveal_dealer: bool = False) -> hikari.Embed:
        """
        Create an embed displaying the current game state.

        Args:
            reveal_dealer: Whether to reveal the dealer's hidden card

        Returns:
            A hikari.Embed object representing the game state
        """
        embed = hikari.Embed(title="🃏 Blackjack", color=0x2B2D31)

        # Show player's main hand
        main_hand_label = "Your Hand" if self.split_hand is None else "Your First Hand"
        embed.add_field(
            name=f"{main_hand_label} (Total: {self.main_hand.value})",
            value=self.main_hand.to_string(),
            inline=False
        )

        # Show split hand if applicable
        if self.split_hand:
            active_marker = " ← Current" if self.active_hand_index == 1 else ""
            embed.add_field(
                name=f"Your Second Hand (Total: {self.split_hand.value}){active_marker}",
                value=self.split_hand.to_string(),
                inline=False
            )

        # Show dealer's hand
        if reveal_dealer:
            embed.add_field(
                name=f"Dealer's Hand (Total: {self.dealer_hand.value})",
                value=self.dealer_hand.to_string(),
                inline=False
            )
        else:
            embed.add_field(
                name="Dealer's Hand",
                value=self.dealer_hand.to_string(hide_second_card=True),
                inline=False
            )

        # Show bet information
        bet_info = f"Main Bet: {self.main_bet} Basedbucks"
        if self.split_hand:
            bet_info += f" | Split Bet: {self.split_bet} Basedbucks"
        if self.insurance_bet > 0:
            bet_info += f" | Insurance: {self.insurance_bet} Basedbucks"

        embed.set_footer(text=bet_info)

        return embed


class BlackjackMenu(lightbulb.components.Menu):
    """Interactive menu for the blackjack game with buttons for game actions."""

    def __init__(self, game: BlackjackGame) -> None:
        """
        Initialize the menu with buttons based on the game state.

        Args:
            game: The BlackjackGame instance to control
        """
        super().__init__()
        self.game = game

        # Standard game buttons always available
        self.hit_button = self.add_interactive_button(
            hikari.ButtonStyle.SUCCESS,
            self.on_hit,
            label="Hit"
        )
        self.stand_button = self.add_interactive_button(
            hikari.ButtonStyle.DANGER,
            self.on_stand,
            label="Stand"
        )

        # Conditional buttons based on game state
        if self.game.main_hand.can_split and not self.game.split_hand:
            self.split_button = self.add_interactive_button(
                hikari.ButtonStyle.PRIMARY,
                self.on_split,
                label="Split"
            )

        if self.game.can_double_down():
            self.double_down_button = self.add_interactive_button(
                hikari.ButtonStyle.PRIMARY,
                self.on_double_down,
                label="Double Down"
            )

        if self.game.can_surrender():
            self.surrender_button = self.add_interactive_button(
                hikari.ButtonStyle.SECONDARY,
                self.on_surrender,
                label="Surrender"
            )

        if self.game.insurance_available and not self.game.insurance_resolved:
            self.insurance_button = self.add_interactive_button(
                hikari.ButtonStyle.SUCCESS,
                self.on_insurance,
                label="Insurance"
            )

    async def predicate(self, ctx: lightbulb.components.MenuContext) -> bool:
        """Check if the user is the player in this game."""
        if ctx.user.id != self.game.player_id:
            await ctx.respond("You are not the player in this game.", flags=hikari.MessageFlag.EPHEMERAL)
            return False
        return True

    async def on_hit(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Hit button action."""
        card = self.game.hit()

        if self.game.is_complete:
            # Game has ended due to bust
            await self._show_game_result(ctx)
            return

        # Game continues - show updated state
        content = f"🃏 Hit! You got a {card.suit}{card.face}."
        if self.game.active_hand_index == 1:
            content = f"🃏 Hit on second hand! You got a {card.suit}{card.face}."

        await ctx.edit_response(
            response_id=self.game.message_id,
            content=content,
            embed=self.game.create_game_embed(),
            components=self._get_updated_menu()
        )

    async def on_stand(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Stand button action."""
        self.game.stand()

        if self.game.is_complete:
            # Game has ended
            await self._show_game_result(ctx)
            return

        # Switched to split hand - update display
        await ctx.edit_response(
            response_id=self.game.message_id,
            content="🃏 Standing on first hand. Playing second hand.",
            embed=self.game.create_game_embed(),
            components=self._get_updated_menu()
        )

    async def on_double_down(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Double Down button action."""
        card = self.game.double_down()

        if self.game.is_complete:
            # Game has ended
            await self._show_game_result(ctx)
            return

        # Switched to split hand - update display
        await ctx.edit_response(
            response_id=self.game.message_id,
            content=f"🃏 Double Down on first hand! You got a {card.suit}{card.face}. Playing second hand.",
            embed=self.game.create_game_embed(),
            components=self._get_updated_menu()
        )

    async def on_split(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Split button action."""
        if self.game.split():
            await ctx.edit_response(
                response_id=self.game.message_id,
                content="🃏 Hand split! Playing first hand.",
                embed=self.game.create_game_embed(),
                components=self._get_updated_menu()
            )
        else:
            await ctx.respond(
                content="🃏 Cannot split this hand.",
                flags=hikari.MessageFlag.EPHEMERAL
            )

    async def on_surrender(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Surrender button action."""
        if self.game.surrender():
            await self._show_game_result(ctx)
        else:
            await ctx.respond(
                content="🃏 Cannot surrender at this point.",
                flags=hikari.MessageFlag.EPHEMERAL
            )

    async def on_insurance(self, ctx: lightbulb.components.MenuContext) -> None:
        """Handle the Insurance button action."""
        if self.game.take_insurance():
            if self.game.is_complete:
                # Dealer had blackjack - game ends
                await self._show_game_result(ctx)
            else:
                # Game continues
                await ctx.edit_response(
                    response_id=self.game.message_id,
                    content="🃏 Insurance taken. Dealer does not have Blackjack.",
                    embed=self.game.create_game_embed(),
                    components=self._get_updated_menu()
                )
        else:
            await ctx.respond(
                content="🃏 Insurance not available.",
                flags=hikari.MessageFlag.EPHEMERAL
            )

    async def _show_game_result(self, ctx: lightbulb.components.MenuContext) -> None:
        """Display the final game result and process payout."""
        outcome = self.game.get_outcome()

        # Process payout
        payout = await self._process_payout(outcome["total_payout"])

        # Prepare result messages
        result_messages = []

        # Main hand result
        result_messages.append(outcome["main_hand"]["message"])

        # Split hand result if applicable
        if outcome["split_hand"]:
            result_messages.append(outcome["split_hand"]["message"])

        # Insurance result if applicable
        if outcome["insurance"]:
            insurance_result = "won" if outcome["insurance"]["outcome"] == "win" else "lost"
            result_messages.append(f"Insurance: You {insurance_result} your insurance bet.")

        # Format the final result message
        result_text = "\n".join(result_messages)
        content = f"🃏 Game Results:\n{result_text}\nTotal Payout: {payout} Basedbucks"

        await ctx.edit_response(
            response_id=self.game.message_id,
            content=content,
            embed=self.game.create_game_embed(reveal_dealer=True),
            components=[]
        )

    async def _process_payout(self, amount: int) -> int:
        """
        Process the payout to the player's account.

        Args:
            amount: The amount to pay out

        Returns:
            The amount paid out
        """
        # Get user's current balance
        user_data = kek_counter.find_one({"user_id": str(self.game.player_id)})
        if not user_data:
            return 0

        # Calculate total bet
        total_bet = self.game.main_bet
        if self.game.split_hand:
            total_bet += self.game.split_bet
        if self.game.insurance_bet:
            total_bet += self.game.insurance_bet

        # Calculate net winnings (can be negative)
        net_change = amount - total_bet

        # Update user's balance
        kek_counter.update_one(
            {"user_id": str(self.game.player_id)},
            {"$inc": {"basedbucks": net_change}}
        )

        return amount

    def _get_updated_menu(self) -> 'BlackjackMenu':
        """Create an updated menu with buttons reflecting the current game state."""
        return BlackjackMenu(self.game)


@loader.command
class BlackjackCommand(
    lightbulb.SlashCommand,
    name="blackjack",
    description="Play a game of blackjack with Basedbucks."
):
    bet = lightbulb.integer("bet", "Amount of Basedbucks to bet on the game.", min_value=10, max_value=1000)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cl: lightbulb.Client) -> None:
        """Handle the blackjack command invocation."""
        await ctx.defer()  # Defer the response to avoid timeout issues

        # Check if user has enough Basedbucks
        user_data = kek_counter.find_one({"user_id": str(ctx.user.id)})

        if not user_data or user_data.get("basedbucks", 0) < self.bet:
            await ctx.respond(
                "You don't have enough Basedbucks to make that bet!",
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        # Deduct initial bet
        kek_counter.update_one(
            {"user_id": str(ctx.user.id)},
            {"$inc": {"basedbucks": -self.bet}}
        )

        msg = await ctx.interaction.fetch_initial_response()
        # Create game instance
        game = BlackjackGame(ctx.user.id, self.bet, msg.id)

        # Check for immediate blackjack scenarios
        if game.is_complete:
            outcome = game.get_outcome()

            # Process payout
            total_payout = outcome["total_payout"]
            await self._process_payout(ctx.user.id, total_payout, self.bet)

            # Display result
            if game.main_hand.is_blackjack and game.dealer_hand.is_blackjack:
                await ctx.respond(
                    content="🃏 Both you and the dealer have Blackjack! It's a push.",
                    embed=game.create_game_embed(reveal_dealer=True)
                )
            elif game.main_hand.is_blackjack:
                await ctx.respond(
                    content=f"🃏 Blackjack! You have a natural 21. Payout is 3:2. You win {total_payout} Basedbucks!",
                    embed=game.create_game_embed(reveal_dealer=True)
                )
            elif game.dealer_hand.is_blackjack:
                await ctx.respond(
                    content=f"🃏 Dealer has Blackjack! You lose your bet of {self.bet} Basedbucks.",
                    embed=game.create_game_embed(reveal_dealer=True)
                )
            return

        # Create interactive menu
        menu = BlackjackMenu(game)

        # Show initial game state
        content = "🃏 Blackjack game started! Make your move."
        if game.insurance_available:
            content += " The dealer has an Ace, and offers insurance."

        # Use the deferred response
        await ctx.respond(
            content=content,
            embed=game.create_game_embed(),
            components=menu
        )

        # Wait for player interactions
        try:
            await menu.attach(cl, wait=True, timeout=120)
        except asyncio.TimeoutError:
            # Avoid using ctx.edit_response which can cause interaction issues
            try:
                # Get the message ID from the interaction
                message = await ctx.interaction.fetch_initial_response()
                await ctx.client.app.rest.edit_message(
                    message.channel_id,
                    message.id,
                    content="🃏 Blackjack game timed out. Your bet has been forfeited.",
                    components=[]
                )
            except (hikari.NotFoundError, hikari.ForbiddenError):
                # Handle case where message cannot be edited
                pass

    async def _process_payout(self, user_id: int, amount: int, bet: int) -> None:
        """
        Process the payout for an immediate blackjack result.

        Args:
            user_id: The player's user ID
            amount: The amount to pay out
            bet: The original bet amount
        """
        # Calculate net gain/loss (amount includes original bet)
        net_change = amount - bet

        # Update user's balance
        kek_counter.update_one(
            {"user_id": str(user_id)},
            {"$inc": {"basedbucks": amount}}
        )


@loader.command
class BlackjackHelp(
    lightbulb.SlashCommand,
    name="blackjack-help",
    description="Get help with playing Blackjack."
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Display comprehensive help information for the blackjack game."""
        embed = hikari.Embed(
            title="🃏 Blackjack Help",
            color=0x2B2D31,
            description="Blackjack is a card game where the goal is to get as close to 21 as possible without going over."
        )

        embed.add_field(
            name="Game Rules",
            value=(
                "• The player and dealer are each dealt two cards.\n"
                "• The player can see both their cards but only one of the dealer's cards.\n"
                "• Number cards (2-10) are worth their face value.\n"
                "• Face cards (Jack, Queen, King) are worth 10 points.\n"
                "• Aces are worth 11 points, but change to 1 point if the total would exceed 21.\n"
                "• The player can choose to hit (draw a card) or stand (end turn).\n"
                "• If the player's total exceeds 21, they bust and lose the game.\n"
                "• The dealer must hit until their hand value is 17 or higher.\n"
                "• The player wins if their final total is higher than the dealer's without busting.\n"
                "• A 'blackjack' is an Ace and a 10-value card on the initial deal (pays 3:2)."
            ),
            inline=False
        )

        embed.add_field(
            name="Special Actions",
            value=(
                "• **Split**: If your initial two cards have the same value, you can split them into two separate hands, each with its own bet.\n"
                "• **Double Down**: Double your bet and receive exactly one more card, then stand automatically.\n"
                "• **Surrender**: Give up your hand and lose only half your bet. Only available on your initial two cards.\n"
                "• **Insurance**: If the dealer's up-card is an Ace, you can place an insurance bet (half your original bet) against the dealer having blackjack. Pays 2:1 if the dealer has blackjack."
            ),
            inline=False
        )

        embed.add_field(
            name="Payouts",
            value=(
                "• **Blackjack**: 3:2 (bet 100, win 150)\n"
                "• **Regular Win**: 1:1 (bet 100, win 100)\n"
                "• **Push** (tie): Bet returned\n"
                "• **Insurance Win**: 2:1 on insurance bet\n"
                "• **Surrender**: Lose half your bet"
            ),
            inline=False
        )

        embed.add_field(
            name="How to Play",
            value=(
                "1. Use `/blackjack bet:[amount]` to start a game with a bet between 10 and 1000 Basedbucks.\n"
                "2. Click on the action buttons to play your hand.\n"
                "3. The game will automatically resolve once all decisions are made.\n"
                "4. Your winnings (or losses) will be automatically calculated and added to your balance."
            ),
            inline=False
        )

        await ctx.respond(embed=embed)

# Banking Module

def calculate_loan_apr(loan_amount: float, credit_score: int, max_safe_loan: float = 50000) -> float:
    """
    Calculate APR with exponential penalties for excessive loan amounts.

    Args:
    - loan_amount: Amount requested for loan
    - credit_score: Borrower's credit score
    - max_safe_loan: Threshold for what's considered a 'normal' loan

    Returns:
    - APR with escalating penalties for large loans
    """
    # Implement hard limits
    if loan_amount > 1000000:  # Extreme loan cap
        raise ValueError("Loan amount exceeds maximum allowed limit")

    # Base rate calculation
    base_rate = 0.05  # 5% base

    # Credit score factor
    credit_score_factor = max(0, (850 - credit_score) * 0.0003)

    # Exponential loan penalty
    if loan_amount > max_safe_loan:
        # Quadratic penalty for loans beyond safe threshold
        # This makes large loans prohibitively expensive
        excess_multiplier = ((loan_amount - max_safe_loan) / max_safe_loan) ** 2
        loan_penalty = base_rate * excess_multiplier
    else:
        loan_penalty = 0

    # Calculate final APR
    apr = base_rate + credit_score_factor + loan_penalty

    # Hard cap on APR
    return min(apr, 0.50)  # 50% max APR to prevent infinite debt

def can_take_loan(credit_score: int, loan_amount: float, total_existing_debt: float) -> bool:
    """
    Enhanced loan eligibility check

    Args:
    - credit_score: User's credit score
    - loan_amount: Requested loan amount
    - total_existing_debt: Total current debt

    Returns:
    - Boolean indicating loan eligibility
    """
    # Absolute credit score threshold
    if credit_score < 350:
        return False

    # Debt-to-income ratio check
    max_debt_ratio = 0.4  # 40% of total potential debt
    if total_existing_debt + loan_amount > credit_score * 100:
        return False

    # Graduated loan limits based on credit score
    if 350 <= credit_score < 500:
        max_allowed_loan = 5000 * ((credit_score - 350) / 150)
        return loan_amount <= max_allowed_loan

    # Additional large loan restrictions
    if loan_amount > 50000 and credit_score < 700:
        return False

    return True

def calculate_credit_score_change(loan_amount: float, current_score: int, is_repayment: bool = False) -> int:
    """
    Calculate dynamic credit score changes based on loan behavior

    Args:
    - loan_amount: Amount of the loan or repayment
    - current_score: Current credit score
    - is_repayment: Whether this is a loan repayment

    Returns:
    - Credit score change
    """
    if is_repayment:
        # Repayment bonuses
        if loan_amount >= 10000:
            return 10  # Significant repayment bonus
        elif loan_amount >= 5000:
            return 5  # Moderate repayment bonus
        else:
            return 2  # Small repayment bonus
    else:
        # Loan penalties
        if loan_amount >= 50000:
            return -20  # Severe penalty for large loans
        elif loan_amount >= 10000:
            return -10  # Moderate penalty
        else:
            return -5  # Minor penalty

@loader.task(lightbulb.uniformtrigger(hours=24))
async def daily_interest():
    debt_query = {
        'loan_debt': {'$exists': True, '$ne': []}
    }

    # Find documents
    documents = kek_counter.find(debt_query)
    for doc in documents:
        modified = False
        for debt in doc['loan_debt']:
            # Determine the latest date
            latest_date = max(debt['date'], debt['last_increase'])
            # Calculate new loan amount if it has been one week since the latest date
            if (datetime.now() - latest_date).days >= 7:
                debt['last_increase'] = datetime.now()
                new_loan_amount = debt['loan amount'] * (1 + debt['apr'])
                debt['loan amount'] = round(new_loan_amount, 2)
                modified = True

        # If any modification has been made, update the document in the database
        if modified:
            kek_counter.update_one({'_id': doc['_id']}, {'$set': {'loan_debt': doc['loan_debt']}})
            kek_counter.update_one({'_id': doc['_id']}, {'$set': {'total_debt': doc['total_debt']}})
            print("data modified")

@loader.command
class BankLoan(
    lightbulb.SlashCommand,
    name="bank-loan",
    description="Borrow Basedbucks from the bank. Low credit scores are prohibited from taking loans."
):
    amount = lightbulb.number("amount", "Amount of Basedbucks to borrow.", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        player_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        total_debt = player_data.get("total_debt", 0)
        credit_score = player_data.get("credit_score", 700)  # Assuming a default credit score of 700

        debt_threshold = 500000  # Set your debt threshold here
        loan_threshold = 10  # Set your loan threshold here

        if total_debt >= debt_threshold:
            await ctx.respond("You cannot take any more loans because your total debt exceeds the allowed limit!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if len(player_data.get("loan_debt", [])) >= loan_threshold:
            await ctx.respond("You cannot take any more loans because you have too many loans!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if not can_take_loan(credit_score, self.amount, total_debt):
            await ctx.respond("You cannot take this loan due to credit restrictions!",
                              flags=hikari.MessageFlag.EPHEMERAL)
            return

        apr = calculate_loan_apr(self.amount, credit_score)
        if self.amount <= 0:
            await ctx.respond("You can't borrow zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Calculate new credit score
        credit_score_change = calculate_credit_score_change(self.amount, credit_score)
        new_credit_score = max(0, min(850, credit_score + credit_score_change))

        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {'total_debt': round(self.amount, 2), 'basedbucks': round(self.amount, 2)},
                "$push": {
                    "loan_debt": {
                        "date": datetime.now(timezone.utc),
                        "loan amount": round(self.amount, 2),
                        "apr": apr,
                        "last_increase": datetime.now(timezone.utc)
                    }
                },
                "$set": {"credit_score": new_credit_score}
            },
            upsert=True,
        )
        await ctx.respond(f"{ctx.member.mention} borrowed {round(self.amount, 2)} Basedbucks from the bank! Your new credit score is {new_credit_score}.")

@loader.command
class RepayBank(
    lightbulb.SlashCommand,
    name="bank-repay",
    description="Repay Basedbucks to the bank."
):
    amount = lightbulb.number("amount", "Amount of Basedbucks to repay.", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):

        player_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        original_amount = self.amount

        if self.amount > player_data["basedbucks"]:
            await ctx.respond("You don't have enough Basedbucks to repay that much!", flags=hikari.MessageFlag.EPHEMERAL)
            return
        if self.amount <= 0:
            await ctx.respond("You can't repay zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        total_debt = player_data.get("total_debt", 0)
        if self.amount > total_debt:
            await ctx.respond("You're trying to repay more than your total debt!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        for debt in reversed(player_data["loan_debt"]):
            if debt["loan amount"] > 0:
                repayment_amount = min(self.amount, debt["loan amount"])
                debt["loan amount"] -= repayment_amount
                self.amount -= repayment_amount
                total_debt -= repayment_amount
                if debt["loan amount"] <= 0:
                    player_data["loan_debt"].remove(debt)
                if self.amount <= 0:
                   break

        # Calculate new credit score
        credit_score_change = calculate_credit_score_change(self.amount, player_data.get("credit_score", 700), is_repayment=True)
        new_credit_score = min(850, player_data.get("credit_score") + credit_score_change)

        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {"$set": {"loan_debt": player_data["loan_debt"], "total_debt": round(total_debt, 2), "credit_score": new_credit_score},
            "$inc": {"basedbucks": round(original_amount * -1, 2)}}
        )

        await ctx.respond(f"{ctx.member.mention} repaid {round(original_amount, 2)} Basedbucks to the bank! Your new credit score is {new_credit_score}.")

@loader.command
class CheckDebt(
    lightbulb.SlashCommand,
    name="bank-alldebt",
    description="Check how much total debt you have."
):

        @lightbulb.invoke
        async def invoke(self, ctx: lightbulb.Context):

            player_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
            debts = []
            debt_date = []
            for data in player_data['loan_debt']:
                debts.append(data['loan amount'])
                debt_date.append(data['date'])

            embed = hikari.Embed(
                title=f"{ctx.member.username}'s Total Debt",
                description=f"Total Debt: {player_data['total_debt']} Basedbucks"
            )

            for i, (debt_amount, debt_time) in enumerate(zip(debts, debt_date), start=1):
                debt_time_str = debt_time.strftime("%Y-%m-%d %H:%M:%S")
                embed.add_field(
                    name=f"Debt {i}",
                    value=f"Amount: {debt_amount}\nBorrowed at: {debt_time_str}\nAPR: {player_data['loan_debt'][i-1]['apr']}",
                    inline=False
                )

            await ctx.respond(embed=embed)

@loader.command
class WireMoney(
    lightbulb.SlashCommand,
    name="bank-wire",
    description="Wire your Keks or Basedbucks to a fellow user."
):

    user = lightbulb.user("user", "User to wire money to.")
    type = lightbulb.string(
        "type",
        "What type of currency to wire. Keks affect kek count, Basedbucks are only used for gambling.",
        choices=[
            Choice("Keks", "Keks"),
            Choice("Basedbucks", "Basedbucks")
        ]
    )
    amount = lightbulb.number("amount", "Amount to wire.", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):

        player_data = kek_counter.find_one({"user_id": str(ctx.member.id)})

        self.amount = round(self.amount, 2)

        if player_data and player_data.get("kekbanned", False) and self.type == "Keks":
            dm_channel = await ctx.user.fetch_dm_channel()
            await ctx.client.app.rest.create_message(
                channel=dm_channel.id,
                content=f"Sorry {ctx.user.mention}, you are banned from participating in the kekonomy.",
            )
            return

        if (self.type == 'Basedbucks' and self.amount > player_data["basedbucks"]) or (self.type == 'Keks' and self.amount > player_data["kek_count"]):
            await ctx.respond("You don't have enough to make that kind of transanction!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if self.amount <= 0:
            await ctx.respond("You can't donate zero or negative money!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if ctx.member.id == self.user.id:
            await ctx.respond("You can't donate to yourself!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {f"{'kek_count' if self.type == 'Keks' else 'basedbucks'}": self.amount * -1}
            },
            upsert=True,
        )
        kek_counter.update_one(
            {"user_id": str(self.user.id)},
            {
                "$inc": {f"{'kek_count' if self.type == 'Keks' else 'basedbucks'}": self.amount}
            },
            upsert=True,
        )

        await ctx.respond(
            f"{ctx.member.mention} wired {self.amount} {'Kek' if self.type == 'Keks' and self.amount == 1 else 'Keks' if self.type == 'Keks' else 'Basedbuck' if self.amount == 1 else 'Basedbucks'} to {self.user.mention}!"
        )

# The Stock Market

ECONOMIC_UPDATE_CHANNELS = [1178375823812735069, 1121479899841044510]  # Channel IDs for economic updates

VOLATILITY_RANGE = (0.01, 0.15)
MAX_DAILY_CHANGE = 0.25
MIN_STOCK_PRICE = 0.01
MAX_STOCK_PRICE = 10000

def initialize_stocks(stocks_collection):
    """
    Initialize stocks with smart updating: adds new stocks and updates missing fields
    while preserving existing data.
    """
    # Get existing stocks
    existing_data = stocks_collection.find_one({})
    existing_stocks = existing_data.get("stocks", {}) if existing_data else {}

    # Template for new stocks with default values
    initial_stocks = {
        # TECH SECTOR
        "KEKI": {
            "name": "Kekistocracy Tech Inc.",
            "sector": "TECH",
            "price": 100.00,
            "volatility": 0.18,
            "market_cap": 1000000,
            "dividend_yield": 0.02,
            "last_split": None,
            "description": "Pioneer in meme-based artificial intelligence"
        },
        "WOJK": {
            "name": "Wojak Systems",
            "sector": "TECH",
            "price": 85.50,
            "volatility": 0.20,
            "market_cap": 750000,
            "dividend_yield": 0.01,
            "last_split": None,
            "description": "Emotional recognition AI powered by wojak technology"
        },
        "PEPE": {
            "name": "PepeTech Solutions",
            "sector": "TECH",
            "price": 69.42,
            "volatility": 0.22,
            "market_cap": 800000,
            "dividend_yield": 0.00,
            "last_split": None,
            "description": "Rare digital asset authentication systems"
        },

        # FINANCE SECTOR
        "BSDL": {
            "name": "BasedLife Financial",
            "sector": "FINANCE",
            "price": 85.50,
            "volatility": 0.12,
            "market_cap": 750000,
            "dividend_yield": 0.04,
            "last_split": None,
            "description": "Traditional banking with based principles"
        },
        "YELO": {
            "name": "LibRight Capital",
            "sector": "FINANCE",
            "price": 158.99,
            "volatility": 0.15,
            "market_cap": 900000,
            "dividend_yield": 0.05,
            "last_split": None,
            "description": "Yellow quadrant investment strategies"
        },
        "ANCP": {
            "name": "AnCap Holdings",
            "sector": "FINANCE",
            "price": 177.77,
            "volatility": 0.17,
            "market_cap": 850000,
            "dividend_yield": 0.03,
            "last_split": None,
            "description": "Private currency and gold-based investments"
        },

        # ENTERTAINMENT SECTOR
        "FUNI": {
            "name": "FunniColors Entertainment",
            "sector": "ENTERTAINMENT",
            "price": 75.25,
            "volatility": 0.15,
            "market_cap": 500000,
            "dividend_yield": 0.01,
            "last_split": None,
            "description": "Political compass meme streaming platform"
        },
        "QUAD": {
            "name": "Quadrant Media",
            "sector": "ENTERTAINMENT",
            "price": 42.00,
            "volatility": 0.16,
            "market_cap": 450000,
            "dividend_yield": 0.02,
            "last_split": None,
            "description": "Cross-compass unity content production"
        },
        "GRIL": {
            "name": "Grillmaster Networks",
            "sector": "ENTERTAINMENT",
            "price": 133.70,
            "volatility": 0.13,
            "market_cap": 600000,
            "dividend_yield": 0.03,
            "last_split": None,
            "description": "Centrist cooking shows and grilling content"
        },

        # CRYPTO SECTOR
        "CRYG": {
            "name": "Cring Crypto Exchange",
            "sector": "CRYPTO",
            "price": 55.75,
            "volatility": 0.25,
            "market_cap": 250000,
            "dividend_yield": 0.00,
            "last_split": None,
            "description": "Meme-based cryptocurrency exchange"
        },
        "REDP": {
            "name": "RedPilled Chain",
            "sector": "CRYPTO",
            "price": 88.88,
            "volatility": 0.28,
            "market_cap": 300000,
            "dividend_yield": 0.00,
            "last_split": None,
            "description": "Decentralized philosophy token platform"
        },
        "MEME": {
            "name": "MemeCoin Technologies",
            "sector": "CRYPTO",
            "price": 42.69,
            "volatility": 0.30,
            "market_cap": 200000,
            "dividend_yield": 0.00,
            "last_split": None,
            "description": "Political compass NFT marketplace"
        }
    }

    updates = {}
    new_stocks = False

    for symbol, template_data in initial_stocks.items():
        if symbol not in existing_stocks:
            # This is a completely new stock
            updates[f"stocks.{symbol}"] = template_data
            new_stocks = True
            print(f"Adding new stock: {symbol}")
        else:
            # Stock exists, check for missing fields
            existing_stock = existing_stocks[symbol]
            missing_fields = {}

            for field, default_value in template_data.items():
                if field not in existing_stock:
                    missing_fields[field] = default_value
                    print(f"Adding missing field '{field}' to {symbol}")

            if missing_fields:
                updates[f"stocks.{symbol}"] = {
                    **existing_stock,  # Preserve existing data
                    **missing_fields  # Add missing fields
                }

    if updates:
        # Use $set to update only specific fields
        stocks_collection.update_one(
            {},
            {"$set": updates},
            upsert=True
        )

        if new_stocks:
            print("Added new stocks and updated existing ones!")
        else:
            print("Updated existing stocks with missing fields!")
        return True
    else:
        print("No updates needed - all stocks are fully initialized.")
        return False

def check_stock_initialization(stocks_collection):
    """
    Check which stocks and fields are initialized.
    Useful for debugging and verification.
    """
    existing_data = stocks_collection.find_one({})
    if not existing_data or "stocks" not in existing_data:
        print("No stocks initialized yet")
        return

    template_fields = {
        "name", "sector", "price", "volatility", "market_cap",
        "dividend_yield", "last_split",
        "description", "last_updated"
    }

    print("\nStock Initialization Status:")
    print("-" * 50)

    for symbol, stock_data in existing_data["stocks"].items():
        print(f"\n{symbol}:")
        print("  Fields present:", ", ".join(stock_data.keys()))
        missing = template_fields - set(stock_data.keys())
        if missing:
            print("  Missing fields:", ", ".join(missing))
        else:
            print("  ✓ Fully initialized")

def save_stock_price_history(stock_data):
    """
    Save current stock prices to historical tracking collection.

    Args:
        stock_data (dict): Current stock data to be saved
    """
    # Add timestamp to the document
    history_entry = {
        "timestamp": datetime.now(timezone.utc),
        "stocks": {}
    }

    # Copy stock data, ensuring we don't modify the original
    for symbol, details in stock_data.get("stocks", {}).items():
        history_entry["stocks"][symbol] = {
            "name": details["name"],
            "price": details["price"],
            "volatility": details["volatility"]
        }

    # Insert the historical entry
    stock_history.insert_one(history_entry)

    # Prune old historical data (keep last 30 days)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    stock_history.delete_many({"timestamp": {"$lt": cutoff_date}})

ECONOMIC_EVENT_PROBABILITY = 0.005  # 0.5% chance of an original economic event
MARKET_WIDE_BOOM_PROBABILITY = 0.005  # 0.5% chance of market-wide boom
MARKET_WIDE_BUST_PROBABILITY = 0.002  # 0.2% chance of market-wide bust
MEGA_EVENT_PROBABILITY = 0.0005  # 0.05% chance of massive price swing
INTER_STOCK_EVENT_PROBABILITY = 0.008  # 0.8% chance of one stock rising while another falls
SECTOR_EVENT_PROBABILITY = 0.004  # 0.4% chance of sector-wide event
DIVIDEND_EVENT_PROBABILITY = 0.0075  # 0.75% chance of dividend payout
STOCK_SPLIT_PROBABILITY = 0.002  # 0.2% chance of stock split
PENNY_STOCK_THRESHOLD = 1.00  # Price below which a stock is considered a penny stock
PENNY_STOCK_DURATION = timedelta(hours=4)  # Time period to track low prices
PENNY_STOCK_RECOVERY_PROBABILITY = 0.25  # 25% chance of recovery event
PENNY_STOCK_RECOVERY_MULTIPLIER = (1.5, 4.0)  # 150-400% price increase

MEGA_EVENT_MULTIPLIER = 15  # Increased to 1500% price change
INTER_STOCK_MULTIPLIER = 2.0  # Increased to 100% price change for competing stocks
SECTOR_EVENT_MULTIPLIER = 1.3  # 30% sector-wide change
NORMAL_BOOM_MULTIPLIER = (1.10, 1.50)  # 10-50% increase
NORMAL_BUST_MULTIPLIER = (0.65, 0.90)  # 10-35% decrease

STOCK_SECTORS = {
    # TECH SECTOR
    "KEKI": "TECH",
    "WOJK": "TECH",
    "PEPE": "TECH",

    # FINANCE SECTOR
    "BSDL": "FINANCE",
    "YELO": "FINANCE",
    "ANCP": "FINANCE",

    # ENTERTAINMENT SECTOR
    "FUNI": "ENTERTAINMENT",
    "QUAD": "ENTERTAINMENT",
    "GRIL": "ENTERTAINMENT",

    # CRYPTO SECTOR
    "CRYG": "CRYPTO",
    "REDP": "CRYPTO",
    "MEME": "CRYPTO"
}

SECTOR_EVENTS = {
    "TECH": [
        "🤖 AI Revolution: Auth-detection algorithms breakthrough!",
        "💻 Political Compass Browser Extension goes viral!",
        "🔒 Wojak-based security systems seeing massive adoption!",
    ],
    "FINANCE": [
        "💰 Gold standard discussions impact market!",
        "📈 LibRight investment strategies gaining popularity!",
        "🏦 New political compass-based credit scoring system!",
    ],
    "ENTERTAINMENT": [
        "🎮 New Political Compass game tops charts!",
        "🎬 Quadrant Unity show becomes streaming hit!",
        "🍖 Centrist grilling content surges in popularity!",
    ],
    "CRYPTO": [
        "⛓️ New BasedCoin blockchain launched!",
        "🌐 Political compass NFTs trending!",
        "💱 Compass-token trading volume explodes!"
    ]
}

# Mega event multiplier ranges for each type
MEGA_EVENT_RANGES = {
    "breakthrough": {
        "multiplier_range": (3.0, 15.0),  # 300-1500% increase
        "events": {
            "TECH": [
                "🚀 Revolutionary AI Breakthrough! {symbol} creates sentient PCM bot!",
                "💡 Quantum Political Compass Computing achieved by {symbol}!",
                "🧠 {symbol} develops Based-AI that can detect cringe with 100% accuracy!"
            ],
            "FINANCE": [
                "💰 {symbol} invents new financial instrument based on based-to-cringe ratio!",
                "📈 {symbol} algorithm predicts political shifts with 99% accuracy!",
                "🏦 {symbol} creates revolutionary political alignment credit score!"
            ],
            "ENTERTAINMENT": [
                "🎮 {symbol}'s new PCM metaverse takes over social media!",
                "🎬 {symbol} launches mind-reading political compass test!",
                "📱 {symbol}'s AR political compass overlay goes viral!"
            ],
            "CRYPTO": [
                "⛓️ {symbol} solves political alignment verification on blockchain!",
                "🌐 {symbol} creates unified theory of political cryptocurrency!",
                "💱 {symbol}'s new consensus mechanism revolutionizes digital politics!"
            ]
        }
    },
    "scandal": {
        "multiplier_range": (0.15, 0.40),  # 60-85% decrease
        "events": {
            "ALL": [
                "⚠️ {symbol} CEO caught being unflaired!",
                "📉 {symbol} executives accused of hiding their true quadrant!",
                "🚨 Whistleblower reveals {symbol} manipulated based count!",
                "💥 {symbol} caught using orange left talking points!",
                "❌ {symbol} accused of radical centrism!"
            ]
        }
    },
    "acquisition": {
        "multiplier_range": (1.50, 4.0),  # 50-300% increase
        "events": {
            "ALL": [
                "🤝 Mega Based Corporation announces {symbol} buyout!",
                "💰 Cross-Compass Unity Fund acquiring {symbol}!",
                "🌟 Political Unity achieved as {symbol} merges with competitor!",
                "📈 Radical Centrist Conglomerate absorbing {symbol}!"
            ]
        }
    },
    "regulatory": {
        "multiplier_range": (0.50, 0.70),  # 30-50% decrease
        "events": {
            "TECH": ["📱 Anti-bias regulations hit {symbol}'s AI algorithms!"],
            "FINANCE": ["📜 New political disclosure requirements affect {symbol}!"],
            "ENTERTAINMENT": ["📺 Content neutrality laws impact {symbol}!"],
            "CRYPTO": ["🏛️ Political token regulations shake {symbol}!"]
        }
    },
    "viral": {
        "multiplier_range": (2.0, 5.0),  # 200-500% increase
        "events": {
            "ALL": [
                "📱 {symbol} trending after epic political compass moment!",
                "🌟 Famous PCM personality endorses {symbol}!",
                "🚀 {symbol}'s based department post breaks internet!",
                "💫 {symbol} achieves perfect compass unity score!"
            ]
        }
    }
}

def generate_market_event(symbol, sector):
    """Generate a market event with appropriate message and multiplier."""
    event_type = random.choice(list(MEGA_EVENT_RANGES.keys()))
    event_data = MEGA_EVENT_RANGES[event_type]

    # Get event messages for sector or general
    messages = event_data["events"].get(sector, event_data["events"].get("ALL", []))
    if not messages:
        messages = event_data["events"]["ALL"]

    message = random.choice(messages).format(symbol=symbol)
    multiplier = random.uniform(*event_data["multiplier_range"])

    return {
        "type": event_type,
        "message": message,
        "multiplier": multiplier
    }

def generate_stock_price_change(
    current_price,
    stock_volatility,
    stocks_data=None,
    symbol=None,
    global_event=None
):
    """
    Enhanced stock price change generation with multiple economic event types.

    Args:
        current_price (float): Current stock price
        stock_volatility (float): Stock's default volatility
        stocks_data (dict, optional): All stocks data for inter-stock events
        symbol (str, optional): Current stock symbol
        global_event (dict, optional): Global market event details

    Returns:
        tuple: (new_price, event_description, competing_stock_info)
    """

    events = []
    price_multiplier = 1.0
    split_info = None

    if symbol == "REDP" and stocks_data.get("REDP", {}).get('price') > 0.92:
        multiplier = 0.1
        return round(current_price * multiplier,
                     2), f"Economic Bust affecting {symbol}! Stock price falls rapidly!", None, split_info

    if stocks_data and symbol and current_price < PENNY_STOCK_THRESHOLD:
        stock_info = stocks_data.get(symbol, {})
        last_updated = stock_info.get('last_updated')

        if last_updated:
            # Ensure last_updated has timezone if it doesn't
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - last_updated > PENNY_STOCK_DURATION:
                if random.random() < PENNY_STOCK_RECOVERY_PROBABILITY:
                    recovery_multiplier = random.uniform(*PENNY_STOCK_RECOVERY_MULTIPLIER)
                    price_multiplier *= recovery_multiplier
                    events.append(f"💫 Penny Stock Surge! {symbol} sees massive recovery!")
                    return round(current_price * price_multiplier, 2), events, None, None

    # Check for global event
    if global_event:
        if global_event['type'] == 'boom':
            multiplier = random.uniform(*NORMAL_BOOM_MULTIPLIER)
            return round(current_price * multiplier, 2), [
                "🌟 Global Based Event! All stocks mooning!",
                "📈 Cross-Compass Unity achieved! Markets soaring!",
                "💫 Political Compass alignment perfect! Stocks surge!"
            ], None, None
        elif global_event['type'] == 'bust':
            multiplier = random.uniform(*NORMAL_BUST_MULTIPLIER)
            return round(current_price * multiplier, 2), [
                "💥 Global Cringe Event! Markets crashing!",
                "📉 Compass Unity broken! Stocks plummeting!",
                "🚨 Political alignment chaos! Markets in shambles!"
            ], None, None

    #Check for mega event
    if random.random() < MEGA_EVENT_PROBABILITY:
        sector = STOCK_SECTORS.get(symbol, "ALL")
        event = generate_market_event(symbol, sector)
        events.append(event["message"])
        price_multiplier *= event["multiplier"]
        return round(current_price * price_multiplier, 2), events, None, None

    # Check for stock split
    base_split_prob = 0.002
    price_factor = max(0, (current_price - 100) / 100)  # Starts at $100
    split_probability = min(0.20, base_split_prob + (price_factor * 0.02))  # Caps at 20%

    # Check for stock split with dynamic probability
    if random.random() < split_probability and current_price > 100:
        # Higher split ratios for higher prices
        if current_price > 1000:
            split_ratio = random.choice([4, 5, 6, 8])
        elif current_price > 500:
            split_ratio = random.choice([3, 4, 5])
        else:
            split_ratio = random.choice([2, 3])

        new_price = current_price / split_ratio
        events.append(f"📈 Stock Split! {symbol} shares split {split_ratio}:1")
        price_multiplier *= (1 / split_ratio)

        split_info = {
            "symbol": symbol,
            "ratio": split_ratio,
            "old_price": current_price,
            "new_price": new_price
        }

    # Check for dividend payout
    if random.random() < DIVIDEND_EVENT_PROBABILITY and stocks_data[symbol].get('dividend_yield', 0) > 0:
        dividend_yield = stocks_data[symbol].get('dividend_yield', 0.02)
        dividend_amount = current_price * dividend_yield
        events.append(f"💰 Dividend Alert! {symbol} pays ${dividend_amount:.2f} per share!")
        # Small price drop after dividend
        price_multiplier *= 0.98

    # Check for sector event
    if random.random() < SECTOR_EVENT_PROBABILITY and stocks_data:
        current_sector = STOCK_SECTORS.get(symbol)
        if current_sector:
            direction = random.choice([-1, 1])
            sector_multiplier = SECTOR_EVENT_MULTIPLIER ** direction
            price_multiplier *= sector_multiplier
            event_type = "boom" if direction > 0 else "bust"
            events.append(f"🏢 {current_sector} Sector {event_type.title()}! All {current_sector} stocks affected!")

    # Check for inter-stock event
    if stocks_data and symbol and random.random() < INTER_STOCK_EVENT_PROBABILITY:
        competing_stocks = [
            s for s, info in stocks_data.items()
            if s != symbol and STOCK_SECTORS.get(s) == STOCK_SECTORS.get(symbol)
        ]

        if competing_stocks:
            competing_symbol = random.choice(competing_stocks)
            price_multiplier *= INTER_STOCK_MULTIPLIER
            events.append(f"🔄 Market Share Shift! {symbol} gains advantage over {competing_symbol}!")

            return (
                round(current_price * price_multiplier, 2),
                events,
                {
                    'symbol': competing_symbol,
                    'new_price': round(stocks_data[competing_symbol]['price'] * (1 / INTER_STOCK_MULTIPLIER), 2)
                },
                split_info
            )

    # Original economic event logic
    if random.random() < ECONOMIC_EVENT_PROBABILITY:
        event_type = random.choice(['boom', 'bust'])
        if event_type == 'boom':
            multiplier = random.uniform(*NORMAL_BOOM_MULTIPLIER)
            return round(current_price * multiplier, 2), f"Economic Boom affecting {symbol}! Stock price rises quickly!", None, split_info
        else:
            multiplier = random.uniform(*NORMAL_BUST_MULTIPLIER)
            return round(current_price * multiplier, 2), f"Economic Bust affecting {symbol}! Stock price falls rapidly!", None, split_info

    # Normal price change logic (if no special event occurs)
    if not events:
        base_volatility = random.uniform(0.01, stock_volatility)
        trend_momentum = random.uniform(0.9, 1.4)  # Add slight trend momentum
        price_multiplier *= (1 + (base_volatility * random.choice([-1, 1]) * trend_momentum))

        # Apply final price changes with limits
    base_growth = 1.0015
    new_price = current_price * price_multiplier * base_growth
    new_price = max(MIN_STOCK_PRICE, min(MAX_STOCK_PRICE, new_price))

    return round(new_price, 2), events if events else None, None, split_info

@loader.task(lightbulb.crontrigger("0 */2 * * *"))
async def update_stock_prices(client: lightbulb.GatewayEnabledClient):
    """
    Periodically update stock prices with enhanced economic events.
    """
    # Fetch existing stocks
    existing_stocks = stocks.find_one({}) or {"stocks": {}}
    stocks_dict = existing_stocks["stocks"]

    global_event = None
    split_updates = []

    if random.random() < MARKET_WIDE_BOOM_PROBABILITY:
        global_event = {
            'type': 'boom',
            'multiplier': NORMAL_BOOM_MULTIPLIER,
            'message': "📈 Global Economic Boom! All stocks surging!"
        }
    elif random.random() < MARKET_WIDE_BUST_PROBABILITY:
        global_event = {
            'type': 'bust',
            'multiplier': NORMAL_BUST_MULTIPLIER,
            'message': "📉 Global Economic Downturn! All stocks plummeting!"
        }

    # Keep track of any significant events
    significant_events = []

    for symbol, stock_info in existing_stocks["stocks"].items():
        current_price = stock_info.get("price")
        stock_volatility = stock_info.get("volatility", 0.15)

        # Generate the new price and possible event description
        new_price, description, competing_stock_info, split_info = generate_stock_price_change(
            current_price,
            stock_volatility,
            stocks_data=stocks_dict,
            symbol=symbol,
            global_event=global_event  # Pass global event
        )

        if split_info:
            split_updates.append(split_info)
            if description:
                significant_events.append((symbol, description))

        # Prepare updated stock details
        update_details = {
            "name": stock_info["name"],
            "price": round(new_price, 2),
            "volatility": stock_volatility,
            "last_updated": datetime.now(timezone.utc),
            "sector": STOCK_SECTORS.get(symbol),
            "market_cap": stock_info.get("market_cap", 1000000),
            "dividend_yield": stock_info.get("dividend_yield", 0.02),
            "last_split": stock_info.get("last_split"),
            "description": stock_info.get("description")
        }

        # Add event information if an event occurred
        if description:
            update_details["event"] = {
                "type": description,
                "timestamp": datetime.now(timezone.utc)
            }
            significant_events.append((symbol, description))

        # Update the stock in the database
        stocks.update_one(
            {},
            {"$set": {f"stocks.{symbol}": update_details}},
            upsert=True
        )

        # Handle competing stock price change for inter-stock events
        if competing_stock_info:
            competing_symbol = competing_stock_info['symbol']
            competing_new_price = competing_stock_info['new_price']

            competing_stock = existing_stocks["stocks"][competing_symbol]
            competing_update_details = {
                "name": competing_stock["name"],
                "price": competing_new_price,
                "volatility": competing_stock.get("volatility", 0.15),
                "last_updated": datetime.now(timezone.utc)
            }

            stocks.update_one(
                {},
                {"$set": {f"stocks.{competing_symbol}": competing_update_details}},
                upsert=True
            )

    updated_stocks = stocks.find_one({})

    if split_updates:
        # Find all users with stocks
        users_with_stocks = kek_counter.find({"stocks": {"$exists": True}})

        for user in users_with_stocks:
            updated_portfolio = []
            portfolio_modified = False

            for stock in user.get("stocks", []):
                # Check if this stock had a split
                split_event = next((s for s in split_updates if s["symbol"] == stock["symbol"]), None)

                if split_event:
                    # Multiply quantity by split ratio, adjust purchase price
                    updated_portfolio.append({
                        "symbol": stock["symbol"],
                        "quantity": stock["quantity"] * split_event["ratio"],
                        "purchase_price": stock["purchase_price"] / split_event["ratio"],
                        "purchase_date": stock["purchase_date"]
                    })
                    portfolio_modified = True
                else:
                    updated_portfolio.append(stock)

            if portfolio_modified:
                kek_counter.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"stocks": updated_portfolio}}
                )

    # Save historical data
    save_stock_price_history(updated_stocks)

    # Announce significant events
    if global_event or significant_events:
        for channel in ECONOMIC_UPDATE_CHANNELS:
            # Announce global event first
            if global_event:
                await client.app.rest.create_message(
                    channel,
                    content=global_event['message']
                )
                continue

            # Then announce specific stock events
            for _, event_description in significant_events:
                await client.app.rest.create_message(
                    channel,
                    content=f"🔔 Economic Event: {event_description}"
                )


def format_portfolio_details(portfolio_items, stock_prices, sector=None):
    """
    Format portfolio details with pagination to stay within Discord limits.

    Args:
        portfolio_items (list): List of stock portfolio items
        stock_prices (dict): Current stock prices data
        sector (str, optional): Filter by sector

    Returns:
        tuple: (list of portfolio detail chunks, total portfolio value)
    """
    portfolio_chunks = []
    current_chunk = ""
    portfolio_value = 0

    for stock in portfolio_items:
        if sector and STOCK_SECTORS.get(stock["symbol"]) != sector:
            continue

        current_stock = stock_prices.get(stock["symbol"], {})
        current_price = current_stock.get("price", stock["purchase_price"])
        total_value = current_price * stock["quantity"]
        portfolio_value += total_value

        # Calculate profit/loss
        profit_loss = (current_price - stock["purchase_price"]) * stock["quantity"]
        profit_loss_color = "🟢" if profit_loss > 0 else "🔴" if profit_loss < 0 else "➖"

        stock_detail = (
            f"{stock['symbol']} - {stock['quantity']} shares\n"
            f"Sector: {STOCK_SECTORS.get(stock['symbol'], 'N/A')}\n"
            f"Purchase: ${stock['purchase_price']:.2f} → Current: ${current_price:.2f}\n"
            f"Total: ${total_value:.2f} ({profit_loss_color} ${profit_loss:.2f})\n\n"
        )

        # Check if adding this stock would exceed Discord's limit
        if len(current_chunk + stock_detail) > 1000:  # Using 1000 to leave some margin
            portfolio_chunks.append(current_chunk)
            current_chunk = stock_detail
        else:
            current_chunk += stock_detail

    if current_chunk:
        portfolio_chunks.append(current_chunk)

    return portfolio_chunks, portfolio_value


def format_market_overview(stocks_data, symbol=None, sector=None):
    """
    Format market overview with sector grouping and pagination.

    Args:
        stocks_data (dict): Current stock market data
        symbol (str, optional): Filter by symbol
        sector (str, optional): Filter by sector

    Returns:
        list: List of market overview chunks
    """
    # Group stocks by sector
    sector_groups = {}
    for stock_symbol, details in stocks_data.items():
        if (symbol and stock_symbol != symbol) or \
                (sector and STOCK_SECTORS.get(stock_symbol) != sector):
            continue

        stock_sector = STOCK_SECTORS.get(stock_symbol, 'Other')
        if stock_sector not in sector_groups:
            sector_groups[stock_sector] = []

        sector_groups[stock_sector].append((stock_symbol, details))

    # Format each sector's stocks
    overview_chunks = []
    current_chunk = ""
    current_sector = None

    for sector_name in sorted(sector_groups.keys()):
        sector_stocks = sector_groups[sector_name]
        sector_content = f"__**{sector_name} SECTOR**__\n"

        # Start a new chunk if this is a new sector
        if current_sector != sector_name:
            if current_chunk:
                overview_chunks.append(current_chunk)
            current_chunk = sector_content
            current_sector = sector_name

        for stock_symbol, details in sorted(sector_stocks):
            stock_info = (
                f"**{stock_symbol}** - {details['name']}\n"
                f"Price: ${details['price']:.2f} | Vol: {details['volatility'] * 100:.1f}% | "
                f"Div: {details.get('dividend_yield', 0.02) * 100:.1f}%\n"
                f"{details.get('description', '')}\n\n"
            )

            # Check if adding this stock would exceed Discord's limit
            if len(current_chunk + stock_info) > 1024:
                overview_chunks.append(current_chunk)
                current_chunk = sector_content + stock_info  # Start new chunk with sector header
            else:
                current_chunk += stock_info

    if current_chunk:
        overview_chunks.append(current_chunk)

    return overview_chunks

STOCK_CHOICES = [
    lightbulb.Choice("KEKI", "KEKI"),
    lightbulb.Choice("WOJK", "WOJK"),
    lightbulb.Choice("PEPE", "PEPE"),
    lightbulb.Choice("BSDL", "BSDL"),
    lightbulb.Choice("YELO", "YELO"),
    lightbulb.Choice("ANCP", "ANCP"),
    lightbulb.Choice("FUNI", "FUNI"),
    lightbulb.Choice("QUAD", "QUAD"),
    lightbulb.Choice("GRIL", "GRIL"),
    lightbulb.Choice("CRYG", "CRYG"),
    lightbulb.Choice("REDP", "REDP"),
    lightbulb.Choice("MEME", "MEME")
]

SECTOR_CHOICES = [
    lightbulb.Choice("TECH", "TECH"),
    lightbulb.Choice("FINANCE", "FINANCE"),
    lightbulb.Choice("ENTERTAINMENT", "ENTERTAINMENT"),
    lightbulb.Choice("CRYPTO", "CRYPTO")
]

SYMBOLS = [
    "KEKI",
    "WOJK",
    "PEPE",
    "BSDL",
    "YELO",
    "ANCP",
    "FUNI",
    "QUAD",
    "GRIL",
    "CRYG",
    "REDP",
    "MEME"
]

@loader.command
class BuyStock(
    lightbulb.SlashCommand,
    name="buy-stock",
    description="Buy stocks from the market"
):
    symbol = lightbulb.string("symbol", "Stock symbol to buy", choices=STOCK_CHOICES)
    quantity = lightbulb.number("quantity", "Number of stocks to buy. Max limit is 1M.", min_value=1, max_value=1000000)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        # Retrieve current stock information
        stock_data = stocks.find_one({})
        if not stock_data or self.symbol not in stock_data.get("stocks", {}):
            await ctx.respond("Stock not found!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        current_stock = stock_data["stocks"][self.symbol]
        total_cost = current_stock["price"] * self.quantity

        # Check user's basedbucks
        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        if not user_data or user_data.get("basedbucks", 0) < total_cost:
            await ctx.respond(
                f"You don't have enough Basedbucks to buy {self.quantity} stocks of {current_stock['name']}!",
                flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Look for existing stock with same purchase price
        user_stocks = user_data.get("stocks", [])
        matching_stock = None
        new_stocks_list = []
        stock_merged = False

        for stock in user_stocks:
            if (stock["symbol"] == self.symbol and
                abs(stock["purchase_price"] - current_stock["price"]) < 0.01):  # Using small threshold for float comparison
                # Merge with existing stock
                new_stocks_list.append({
                    "symbol": stock["symbol"],
                    "quantity": stock["quantity"] + self.quantity,
                    "purchase_price": stock["purchase_price"],
                    "purchase_date": stock["purchase_date"]
                })
                stock_merged = True
            else:
                new_stocks_list.append(stock)

        # If no matching stock found, add as new entry
        if not stock_merged:
            new_stocks_list.append({
                "symbol": self.symbol,
                "quantity": self.quantity,
                "purchase_price": current_stock["price"],
                "purchase_date": datetime.now(timezone.utc)
            })

        # Update user's stocks and basedbucks
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {"basedbucks": -total_cost},
                "$set": {"stocks": new_stocks_list}
            },
            upsert=True
        )

        merge_message = " (Merged with existing shares)" if stock_merged else ""
        await ctx.respond(
            f"Bought {self.quantity} stocks of {current_stock['name']} at ${current_stock['price']:.2f} each. "
            f"Total cost: ${total_cost:.2f} Basedbucks{merge_message}")

@loader.command
class SellStock(
    lightbulb.SlashCommand,
    name="sell-stock",
    description="Sell stocks from your portfolio"
):
    symbol = lightbulb.string("symbol", "Stock symbol to sell", choices=STOCK_CHOICES)
    quantity = lightbulb.number("quantity", "Number of stocks to sell", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        # Retrieve current stock information
        stock_data = stocks.find_one({})
        if not stock_data or self.symbol not in stock_data.get("stocks", {}):
            await ctx.respond("Stock not found!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        current_stock = stock_data["stocks"][self.symbol]
        current_price = current_stock["price"]

        # Check user's stock portfolio
        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})
        if not user_data or "stocks" not in user_data:
            await ctx.respond("You don't have any stocks to sell!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Find matching stocks in portfolio
        user_stocks = user_data["stocks"]
        matching_stocks = [s for s in user_stocks if s["symbol"] == self.symbol]

        total_user_stocks = sum(s["quantity"] for s in matching_stocks)
        if total_user_stocks < self.quantity:
            await ctx.respond(f"You only have {total_user_stocks} stocks of {current_stock['name']} to sell!",
                              flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Calculate sale and potential profit/loss
        total_sale_value = current_price * self.quantity

        # Calculate total purchase price for sold stocks
        remaining_quantity = self.quantity
        total_purchase_price = 0
        updated_portfolio = []

        for stock in user_stocks:
            if stock["symbol"] == self.symbol and remaining_quantity > 0:
                sell_qty = min(stock["quantity"], remaining_quantity)

                # Calculate the purchase price for sold stocks
                if sell_qty == stock["quantity"]:
                    total_purchase_price += stock["purchase_price"] * sell_qty
                    remaining_quantity -= sell_qty
                else:
                    total_purchase_price += stock["purchase_price"] * sell_qty
                    stock["quantity"] -= sell_qty
                    updated_portfolio.append(stock)
                    remaining_quantity = 0
            else:
                updated_portfolio.append(stock)

        # Update user's stocks and basedbucks
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {"basedbucks": total_sale_value},
                "$set": {"stocks": updated_portfolio}
            }
        )

        # Calculate profit/loss
        profit_loss = total_sale_value - total_purchase_price
        profit_loss_text = f"Profit/Loss: ${profit_loss:.2f} " + \
                           ("(Profit)" if profit_loss > 0 else "(Loss)" if profit_loss < 0 else "")

        await ctx.respond(
            f"Sold {self.quantity} stocks of {current_stock['name']} at ${current_price:.2f} each.\n"
            f"Total sale: ${total_sale_value:.2f} Basedbucks\n"
            f"{profit_loss_text}")

@loader.command
class CheckStocks(
    lightbulb.SlashCommand,
    name="check-stocks",
    description="Check current stock prices and your portfolio"
):
    days = lightbulb.integer("days", "Number of days to view (default: 30, max: 30)",
                             default=30,
                             min_value=1,
                             max_value=30
                             )
    symbol = lightbulb.string("symbol", "Stock symbol to view specifically. Leave empty for all stocks.", default=None, choices=STOCK_CHOICES)

    sector = lightbulb.string("sector", "Stock sector to view specifically. Leave empty for all sectors.", default=None, choices=SECTOR_CHOICES)

    def validate_symbol_sector(self, symbol, sector):
        """
        Validate that the symbol and sector combination is valid.
        Returns a tuple of (is_valid, error_message)
        """
        if symbol and sector:
            stock_sector = STOCK_SECTORS.get(symbol)
            if stock_sector != sector:
                return False, f"❌ Error: Stock {symbol} belongs to {stock_sector} sector, not {sector} sector. Please choose matching symbol and sector or use them separately."
        return True, None

    def find_peaks_troughs(self, prices, min_distance=2):
        """
        Find peaks and troughs in price data.

        Args:
            prices (list): List of price values
            min_distance (int): Minimum distance between peaks/troughs

        Returns:
            tuple: Lists of peak and trough indices
        """
        peaks = []
        troughs = []

        if len(prices) < 3:
            return peaks, troughs

        for i in range(1, len(prices) - 1):

            is_peak = prices[i-1] < prices[i] and prices[i] > prices[i+1]
            is_trough = prices[i-1] > prices[i] and prices[i] < prices[i+1]

            if is_peak or is_trough:
                if peaks or troughs:
                    last_point = max(peaks[-1] if peaks else 0, troughs[-1] if troughs else 0)
                    if i - last_point < min_distance:
                        continue

                if is_peak:
                    peaks.append(i)
                else:
                    troughs.append(i)

        # Check first and last points
        if len(prices) > 1:
            if prices[0] > prices[1]:
                peaks.insert(0, 0)
            elif prices[0] < prices[1]:
                troughs.insert(0, 0)

            if prices[-1] > prices[-2]:
                peaks.append(len(prices) - 1)
            elif prices[-1] < prices[-2]:
                troughs.append(len(prices) - 1)

        return peaks, troughs

    async def generate_stock_price_graph(self):
        """
        Generate a graph of stock prices from historical data.

        Returns:
            hikari.Bytes: Graph image ready to be sent to Discord
        """
        symbol = self.symbol
        sector = self.sector
        days = self.days

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Retrieve historical stock price data for the last 30 days
        historical_data = list(stock_history.find(
            {"timestamp": {"$gte": start_date}},
        ).sort("timestamp", 1))

        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)

        title = f"Stock Prices Over Past {days} Days"
        if sector:
            title = f"{sector} Sector - {title}"
        plt.title(title, fontsize=15, pad=20)
        plt.xlabel("Timestamp", fontsize=12)
        plt.ylabel("Price ($)", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)

        # Track stocks to plot
        stocks_to_plot = {}

        # Collect and plot data for each stock
        for entry in historical_data:

            for stock_symbol, stock_info in entry.get('stocks', {}).items():

                if symbol and stock_symbol != symbol and symbol is not None:
                    continue

                if sector and STOCK_SECTORS.get(stock_symbol) != sector and sector is not None:
                    continue

                if stock_symbol not in stocks_to_plot:
                    stocks_to_plot[stock_symbol] = {
                        'timestamps': [],
                        'prices': []
                    }

                stocks_to_plot[stock_symbol]['timestamps'].append(entry['timestamp'])
                stocks_to_plot[stock_symbol]['prices'].append(stock_info['price'])

        # Plot each stock with a different color
        colors = ['blue', 'green', 'red', 'purple', 'orange', 'cyan', 'magenta', 'yellow', 'brown', 'pink', 'indigo', 'gold']

        for i, (stock_symbol, data) in enumerate(stocks_to_plot.items()):

            plt.plot(
                data['timestamps'],
                data['prices'],
                label=f"{stock_symbol}",
                color=colors[i % len(colors)],
                linewidth=2,
                zorder=1
            )

            min_distance = max(2, len(data['prices']) // 200)
            peaks, troughs = self.find_peaks_troughs(data['prices'], min_distance)

            plt.scatter(
                [data['timestamps'][i] for i in peaks],
                [data['prices'][i] for i in peaks],
                color='green',
                edgecolors=colors[i % len(colors)],
                marker='^',
                s=50,
                zorder=2
            )

            plt.scatter(
                [data['timestamps'][i] for i in troughs],
                [data['prices'][i] for i in troughs],
                color='red',
                edgecolors=colors[i % len(colors)],
                marker='v',
                s=50,
                zorder=2
            )

            if peaks:
                highest_peak = max(peaks, key=lambda x: data['prices'][x])
                ax.annotate(
                    f'${data["prices"][highest_peak]:.2f}',
                    (data['timestamps'][highest_peak], data['prices'][highest_peak]),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=8,
                    bbox=dict(facecolor='white', edgecolor=colors[i % len(colors)], alpha=0.7, pad=1)
                )

            if troughs:
                lowest_trough = min(troughs, key=lambda x: data['prices'][x])
                ax.annotate(
                    f'${data["prices"][lowest_trough]:.2f}',
                    (data['timestamps'][lowest_trough], data['prices'][lowest_trough]),
                    xytext=(0, -10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=8,
                    bbox=dict(facecolor='white', edgecolor=colors[i % len(colors)], alpha=0.7, pad=1)
                )

        plt.gcf().autofmt_xdate()

        if len(stocks_to_plot) > 1:
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        else:
            ax.legend(loc='best', fontsize='10')

        plt.tight_layout()

        # Save plot to a bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        plt.close()

        # Convert to hikari.Bytes for Discord
        return hikari.Bytes(buffer, 'stock_prices.png')

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        await ctx.defer()

        symbol = self.symbol
        sector = self.sector

        is_valid, error_message = self.validate_symbol_sector(symbol, sector)
        if not is_valid:
            await ctx.respond(error_message, flags=hikari.MessageFlag.EPHEMERAL)
            return

        stock_data = stocks.find_one({})
        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})

        title = "Stock Market Overview"
        if sector:
            title = f"{sector} Sector Overview"
        elif symbol:
            title = f"Stock Overview: {symbol}"

        embed = hikari.Embed(
            title=title,
            color=hikari.Color.from_hex_code("#2ecc71")
        )

        # Add market overview with sector grouping
        if stock_data and "stocks" in stock_data:
            overview_chunks = format_market_overview(
                stock_data["stocks"],
                symbol,
                sector
            )

            for i, chunk in enumerate(overview_chunks, 1):
                field_name = "Market Overview"
                if len(overview_chunks) > 1:
                    field_name += f" (Part {i}/{len(overview_chunks)})"
                embed.add_field(name=field_name, value=chunk, inline=False)

        # Add portfolio with pagination
        if user_data and "stocks" in user_data:
            portfolio_chunks, total_value = format_portfolio_details(
                user_data["stocks"],
                stock_data.get("stocks", {}),
                sector
            )

            for i, chunk in enumerate(portfolio_chunks, 1):
                field_name = f"Your Portfolio{' (' + sector + ' Sector)' if sector else ''}"
                if len(portfolio_chunks) > 1:
                    field_name += f" (Part {i}/{len(portfolio_chunks)})"
                embed.add_field(name=field_name, value=chunk, inline=False)

            if portfolio_chunks:
                embed.add_field(
                    name=f"Total Portfolio Value{' (' + sector + ' Sector)' if sector else ''}",
                    value=f"${total_value:.2f}",
                    inline=False
                )

        # Generate and add stock price graph
        try:
            stock_graph = await self.generate_stock_price_graph()
            await ctx.respond(embed=embed, attachment=stock_graph)
        except Exception as e:
            await ctx.respond(
                f"Error: Could not process request. The portfolio might be too large to display.",
                flags=hikari.MessageFlag.EPHEMERAL
            )


# Slot Machine Module

# Define slot symbols with their display characters, values, and weights
SLOT_SYMBOLS = {
    "🍒": {"value": 1, "weight": 35},  # Very common (increased)
    "🍊": {"value": 2, "weight": 30},  # Common (increased)
    "🍋": {"value": 3, "weight": 18},  # Uncommon (decreased)
    "🍇": {"value": 5, "weight": 12},  # Uncommon (decreased)
    "🍉": {"value": 10, "weight": 4},  # Rare (significantly decreased)
    "💎": {"value": 25, "weight": 1},  # Very rare (significantly decreased)
}


@loader.command(guilds=[1178375822105657384], global_=False)
class TriggerMarketEvent(
    lightbulb.SlashCommand,
    name="trigger-market-event",
    description="Trigger a stock market event [Owner Only]"
):
    event_type = lightbulb.string(
        "event_type",
        "Type of event to trigger",
        choices=[
            Choice("boom", "Boom - Stock price increase"),
            Choice("bust", "Bust - Stock price decrease"),
            Choice("mega", "Mega - Major price swing"),
            Choice("sector", "Sector - Affects all stocks in a sector"),
            Choice("split", "Split - Trigger a stock split")
        ]
    )
    magnitude = lightbulb.number(
        "magnitude",
        "Magnitude of the event (1-10, with 10 being most extreme)",
        min_value=1,
        max_value=10
    )
    symbol = lightbulb.string(
        "symbol",
        "Stock symbol to affect (optional - random if not provided)",
        default=None,
        choices=STOCK_CHOICES
    )
    sector = lightbulb.string(
        "sector",
        "Sector to affect (for sector events)",
        default=None,
        choices=SECTOR_CHOICES
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        await ctx.defer()

        # Get current stock data
        stock_data = stocks.find_one({})
        if not stock_data or "stocks" not in stock_data:
            await ctx.respond("Error: No stock data found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        stocks_dict = stock_data["stocks"]

        # Select a random symbol if none provided
        selected_symbol = self.symbol
        if not selected_symbol:
            selected_symbol = random.choice(list(stocks_dict.keys()))

        # Set default magnitude if not provided
        magnitude_factor = (self.magnitude or 5) / 5.0  # Default to middle value

        # Determine multiplier based on event type and magnitude
        multiplier = 1.0
        event_description = ""
        affected_stocks = []

        if self.event_type == "boom":
            # Boom: 5-100% increase based on magnitude
            multiplier = 1.0 + (0.1 * magnitude_factor * random.uniform(0.5, 1.5))
            event_description = f"📈 Economic Boom! {selected_symbol} stock surges dramatically!"
            affected_stocks = [(selected_symbol, multiplier)]

        elif self.event_type == "bust":
            # Bust: 5-70% decrease based on magnitude
            multiplier = 1.0 - (0.1 * magnitude_factor * random.uniform(0.5, 0.7))
            event_description = f"📉 Economic Bust! {selected_symbol} stock plummets!"
            affected_stocks = [(selected_symbol, multiplier)]

        elif self.event_type == "mega":
            # Use existing mega event system
            sector = STOCK_SECTORS.get(selected_symbol, "ALL")
            event = generate_market_event(selected_symbol, sector)

            # Adjust the multiplier based on the magnitude
            base_multiplier = event["multiplier"]
            adjusted_multiplier = ((
                                               base_multiplier - 1.0) * magnitude_factor) + 1.0 if base_multiplier > 1.0 else 1.0 - (
                        (1.0 - base_multiplier) * magnitude_factor)

            event_description = event["message"]
            affected_stocks = [(selected_symbol, adjusted_multiplier)]

        elif self.event_type == "sector":
            if not self.sector:
                await ctx.respond("Error: Sector must be specified for sector events.",
                                  flags=hikari.MessageFlag.EPHEMERAL)
                return

            # Sector event: affects all stocks in the chosen sector
            sector_stocks = [s for s in stocks_dict.keys() if STOCK_SECTORS.get(s) == self.sector]
            if not sector_stocks:
                await ctx.respond(f"Error: No stocks found in the {self.sector} sector.",
                                  flags=hikari.MessageFlag.EPHEMERAL)
                return

            sector_event = random.choice(SECTOR_EVENTS[self.sector])
            event_description = sector_event

            # Adjust multiplier based on magnitude (positive or negative randomly)
            direction = random.choice([-1, 1])
            base_sector_impact = SECTOR_EVENT_MULTIPLIER ** direction

            # Increase impact based on magnitude
            sector_multiplier = 1.0 + (
                        (base_sector_impact - 1.0) * magnitude_factor) if base_sector_impact > 1.0 else 1.0 - (
                        (1.0 - base_sector_impact) * magnitude_factor)

            affected_stocks = [(s, sector_multiplier) for s in sector_stocks]

        elif self.event_type == "split":
            # Stock split
            current_price = stocks_dict[selected_symbol]["price"]
            if current_price < 50:
                await ctx.respond(f"Error: {selected_symbol} price (${current_price:.2f}) is too low for a split.",
                                  flags=hikari.MessageFlag.EPHEMERAL)
                return

            # Determine split ratio based on price and magnitude
            if current_price > 1000:
                split_options = [4, 5, 6, 8, 10]
            elif current_price > 500:
                split_options = [3, 4, 5]
            else:
                split_options = [2, 3]

            # Higher magnitude increases chance of higher split ratio
            split_ratio = split_options[min(int(self.magnitude / 10.0 * len(split_options)), len(split_options) - 1)]

            event_description = f"📈 Stock Split! {selected_symbol} shares split {split_ratio}:1"
            affected_stocks = [(selected_symbol, 1.0 / split_ratio)]

            # Handle split for all users with this stock
            users_with_stocks = kek_counter.find({"stocks": {"$exists": True}})

            for user in users_with_stocks:
                updated_portfolio = []
                portfolio_modified = False

                for stock in user.get("stocks", []):
                    if stock["symbol"] == selected_symbol:
                        updated_portfolio.append({
                            "symbol": stock["symbol"],
                            "quantity": stock["quantity"] * split_ratio,
                            "purchase_price": stock["purchase_price"] / split_ratio,
                            "purchase_date": stock["purchase_date"]
                        })
                        portfolio_modified = True
                    else:
                        updated_portfolio.append(stock)

                if portfolio_modified:
                    kek_counter.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"stocks": updated_portfolio}}
                    )

        # Apply changes to affected stocks
        for stock_symbol, stock_multiplier in affected_stocks:
            if stock_symbol in stocks_dict:
                current_price = stocks_dict[stock_symbol]["price"]
                new_price = current_price * stock_multiplier

                # Ensure price stays within bounds
                new_price = max(MIN_STOCK_PRICE, min(MAX_STOCK_PRICE, new_price))

                # Update the stock price
                stocks.update_one(
                    {},
                    {"$set": {
                        f"stocks.{stock_symbol}.price": round(new_price, 2),
                        f"stocks.{stock_symbol}.last_updated": datetime.now(timezone.utc),
                        f"stocks.{stock_symbol}.event": {
                            "type": event_description,
                            "timestamp": datetime.now(timezone.utc)
                        }
                    }}
                )

        # Save historical data for the updated stocks
        updated_stocks = stocks.find_one({})
        save_stock_price_history(updated_stocks)

        # Announce the event to economic channels
        for channel_id in ECONOMIC_UPDATE_CHANNELS:
            await ctx.client.app.rest.create_message(
                channel=channel_id,
                content=f"🔔 Economic Event: {event_description}"
            )

        # Respond with success message
        affected_symbols = ", ".join([symbol for symbol, _ in affected_stocks])
        await ctx.respond(
            f"Event triggered successfully!\n\nEvent: {event_description}\nAffected stocks: {affected_symbols}")

# Create weighted symbol list for random selection
WEIGHTED_SYMBOLS = []
for symbol, data in SLOT_SYMBOLS.items():
    WEIGHTED_SYMBOLS.extend([symbol] * data["weight"])


def get_biased_reel_result(previous_results=None):
    """
    Get a result for a slot reel with bias against matching previous results.
    This creates a subtle house edge by making matches less likely.

    Args:
        previous_results: List of symbols already shown in previous reels

    Returns:
        A symbol chosen with weighted probability but biased against matches
    """
    if not previous_results:
        # For the first reel, just use normal weighted random
        return random.choice(WEIGHTED_SYMBOLS)

    roll = random.random()

    if len(previous_results) == 1:
        if roll < 0.25:
            non_matching = [s for s in SLOT_SYMBOLS.keys() if s != previous_results[0]]
            return random.choice(non_matching)
    elif len(previous_results) == 2:
        if roll < 0.40:
            if previous_results[0] == previous_results[1]:
                if random.random() < 0.80:
                    non_matching = [s for s in SLOT_SYMBOLS.keys() if s != previous_results[0]]
                    return random.choice(non_matching)
            else:
                non_matching = [s for s in SLOT_SYMBOLS.keys()
                                if s != previous_results[0] and s != previous_results[1]]
                if non_matching:
                    return random.choice(non_matching)

    choices = []
    for symbol, data in SLOT_SYMBOLS.items():
        is_match = symbol in previous_results

        weight = data["weight"] * (0.4 if is_match else 1.0)

        choices.extend([symbol] * int(weight))

    return random.choice(choices) if choices else random.choice(WEIGHTED_SYMBOLS)

@loader.command
class SlotMachine(
    lightbulb.SlashCommand,
    name="slots",
    description="Play a slot machine game for Basedbucks."
):
    bet = lightbulb.number("bet", "Amount of basedbucks to bet on the slot machine. Min bet is 10, max bet is 1000.", min_value=10, max_value=1000)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        # Check if user has enough basedbucks
        player_data = kek_counter.find_one({"user_id": str(ctx.member.id)})

        if not player_data or player_data.get("basedbucks", 0) < self.bet:
            await ctx.respond(
                "You don't have enough Basedbucks to make that bet!",
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        # Deduct bet amount from player's basedbucks
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {"$inc": {"basedbucks": self.bet * -1}}
        )

        msg = await ctx.respond("🎰 Spinning the slots...")

        spinning_symbols = list(SLOT_SYMBOLS.keys())

        final_slots = ["", "", ""]

        for _ in range(5):
            # Generate random symbols for the spinning effect
            spin = [random.choice(spinning_symbols) for _ in range(3)]
            await ctx.edit_response(msg, f"🎰 | {spin[0]} | {spin[1]} | {spin[2]} |")
            await asyncio.sleep(0.2)

        final_slots[0] = get_biased_reel_result()# Determine first reel result
        for _ in range(5):
            spin = [final_slots[0], random.choice(spinning_symbols), random.choice(spinning_symbols)]
            await ctx.edit_response(msg, f"🎰 | {spin[0]} | {spin[1]} | {spin[2]} |")
            await asyncio.sleep(0.2)

        final_slots[1] = get_biased_reel_result([final_slots[0]])  # Determine second reel result
        for _ in range(5):
            spin = [final_slots[0], final_slots[1], random.choice(spinning_symbols)]
            await ctx.edit_response(msg, f"🎰 | {spin[0]} | {spin[1]} | {spin[2]} |")
            await asyncio.sleep(0.3)

        final_slots[2] = get_biased_reel_result([final_slots[0], final_slots[1]])  # Determine third reel result
        slot_display = f"🎰 | {final_slots[0]} | {final_slots[1]} | {final_slots[2]} |"
        await ctx.edit_response(msg, slot_display)

        # Determine if user won and calculate prize
        result_message = ""
        payout = 0

        if final_slots[0] == final_slots[1] == final_slots[2]:
            # Jackpot - all three symbols match
            symbol_value = SLOT_SYMBOLS[final_slots[0]]["value"]
            prize_multiplier = 10
            payout = self.bet * symbol_value * prize_multiplier
            result_message = f"🎉 **JACKPOT!** 🎉\nYou got three {final_slots[0]} symbols!\nPrize: {payout} Basedbucks!"

        elif final_slots[0] == final_slots[1] or final_slots[1] == final_slots[2] or final_slots[0] == final_slots[2]:
            # Two matching symbols
            if final_slots[0] == final_slots[1]:
                matching_symbol = final_slots[0]
            elif final_slots[1] == final_slots[2]:
                matching_symbol = final_slots[1]
            else:
                matching_symbol = final_slots[0]

            symbol_value = SLOT_SYMBOLS[matching_symbol]["value"]
            prize_multiplier = 2
            payout = self.bet * symbol_value * prize_multiplier
            result_message = f"🎊 **WIN!** 🎊\nYou matched two {matching_symbol} symbols!\nPrize: {payout} Basedbucks!"

        else:
            # No matches
            result_message = "😢 **Better luck next time!**\nNo matching symbols found."

        # Add payout to user's account if they won
        if payout > 0:
            kek_counter.update_one(
                {"user_id": str(ctx.member.id)},
                {"$inc": {"basedbucks": payout}}
            )

            net_gain = payout - self.bet
            gain_loss_text = f"You won {net_gain} Basedbucks!"
        else:
            gain_loss_text = f"You lost {self.bet} Basedbucks."

        # Show the final result with the prize message
        final_message = f"{slot_display}\n\n{result_message}\n\n{gain_loss_text}"
        await ctx.edit_response(msg, final_message)


@loader.command
class SlotsHelp(
    lightbulb.SlashCommand,
    name="slots-help",
    description="Get help with playing the slot machine."
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        embed = hikari.Embed(
            title="🎰 Slot Machine Help",
            color=0x2B2D31,
            description="Try your luck with the slot machine! Bet Basedbucks and win prizes based on matching symbols."
        )

        embed.add_field(
            name="How to Play",
            value="Use `/slots bet:[amount]` to place a bet between 10 and 1000 Basedbucks.",
            inline=False
        )

        embed.add_field(
            name="Winning Combinations",
            value="• Three matching symbols: JACKPOT! Win 10× your bet multiplied by symbol value.\n"
                  "• Two matching symbols: Win 2× your bet multiplied by symbol value.\n"
                  "• No matches: You lose your bet.",
            inline=False
        )

        embed.add_field(
            name="Symbol Values",
            value="🍒 Cherry: 1× multiplier (common)\n"
                  "🍊 Orange: 2× multiplier (common)\n"
                  "🍋 Lemon: 3× multiplier (uncommon)\n"
                  "🍇 Grapes: 5× multiplier (uncommon)\n"
                  "🍉 Watermelon: 10× multiplier (rare)\n"
                  "💎 Diamond: 25× multiplier (very rare)",
            inline=False
        )

        await ctx.respond(embed=embed)