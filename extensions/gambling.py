import asyncio
import io
from typing import List, Optional

import anydeck
import hikari
import lightbulb
import random
import string
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
    if ctx.user.id != OWNER_ID:
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
                    "wager": self.wager,
                    "choice": self.choice
                }
            ],
            "total_pot": self.wager,
            "believer_pot": self.wager if self.choice == "For" else 0,
            "nonbeliever_pot": self.wager if self.choice == "Against" else 0
        }

        gambling_list.insert_one(gamble_data)

        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {f"{'kek_count' if self.betting == 'Keks' else 'basedbucks'}": self.wager * -1}
            },
            upsert=True,
        )

        await ctx.respond(
            f'{ctx.member.mention} bet {self.wager} {self.betting} {"on" if self.choice == "For" else "against"} "{self.bet}"! The deadline is on {deadline_dt}. To join in on the bet, use /join-gamble with the ID "{gamble_id}".'
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
            "wager": self.wager,
            "choice": self.choice
        }
        gambling_list.update_one(
            {"bet_id": self.id},
            {
                "$push": {"betters": new_wager},
                "$inc": {"total_pot": self.wager,
                         "believer_pot" if self.choice == "For" else "nonbeliever_pot": self.wager
                         }
            }
        )
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": self.wager * -1}
            },
            upsert=True
        )

        await ctx.respond(
            f'{ctx.member.mention} bet {self.wager} {bet_data["betting"]} {"on" if self.choice == "For" else "against"} "{bet_data["bet"]}"! To join in on the bet, use /join-gamble with the ID "{self.id}".'
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

                better["wager"] += self.wager

                bet_data["total_pot"] += self.wager
                if better["choice"] == "For":
                    bet_data["believer_pot"] += self.wager
                elif better["choice"] == "Against":
                    bet_data["nonbeliever_pot"] += self.wager

                kek_counter.update_one(
                    {"user_id": str(ctx.member.id)},
                    {"$inc": {f"{'kek_count' if bet_data['betting'] == 'Keks' else 'basedbucks'}": -self.wager}},
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
                    f'{ctx.member.mention} raised their bet by {self.wager}, making their total wager {better["wager"]} {bet_data["betting"]} {"on" if better["choice"] == "For" else "against"} "{bet_data["bet"]}" and the total pot {bet_data["total_pot"]}! To join in on the bet, use /join-gamble with the ID "{self.id}".'
                )
                return
        await ctx.respond("You don't have a wager on this bet!", flags=hikari.MessageFlag.EPHEMERAL)

@loader.command
class CancelGamble(
    lightbulb.SlashCommand,
    name="cancel-gamble",
    description="Cancel a currently running bet. Admins and bot owner only.",
    hooks=[me_only or lightbulb.prefab.has_roles(928983928289771560)]
):
    id = lightbulb.string("id", "ID of the bet you want to cancel.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
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
    hooks=[me_only or lightbulb.prefab.has_roles(928983928289771560)]
):
    id = lightbulb.string("id", "ID of the bet that succeeded.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
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
                winnings = wager * 1.5 if bet_data["nonbeliever_pot"] == 0 else (wager + (
                            bet_data["nonbeliever_pot"] / len(believers))) * 1.5
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
    description="End a bet on the side of the non-believers. Admins and bot owner only.",
    hooks=[me_only or lightbulb.prefab.has_roles(928983928289771560)]
):
    id = lightbulb.string("id", "ID of the bet that failed.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
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
                winnings = wager * 1.5 if bet_data["believer_pot"] == 0 else (wager + (
                            bet_data["believer_pot"] / len(nonbelievers))) * 1.5
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

class BlackjackGame:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.deck = generate_deck(blackjack_values)

        # Deal initial hands
        self.player_hand: List[anydeck.Card] = []
        self.dealer_hand: List[anydeck.Card] = []

        # Deal 2 cards to player and dealer
        for _ in range(2):
            self.player_hand.append(self.deck.draw())
            self.dealer_hand.append(self.deck.draw())
            self.is_insurance_offered: bool = True if self.dealer_hand[0].value == 11 else False

        self.player_total = self._calculate_hand_value(self.player_hand)
        self.dealer_total = self._calculate_hand_value(self.dealer_hand)

        # Track bet and game state
        self.bet_amount: Optional[int] = None
        self.secondary_bet: Optional[int] = None
        self.insurance_bet: Optional[int] = None
        self.game_over: bool = False

        # Improved split and double down handling
        self.can_split: bool = self.player_hand[0].value == self.player_hand[1].value
        self.can_double_down: bool = True
        self.can_primary_double_down: bool = True
        self.can_secondary_double_down: bool = True
        self.is_split = False

        self.primary_hand: List[anydeck.Card] = self.player_hand.copy()
        self.secondary_hand: List[anydeck.Card] = []
        self.current_hand_index = 0
        self.primary_hand_total = self._calculate_hand_value(self.primary_hand)
        self.secondary_hand_total = 0

    def calculate_payout(self, result: str, bet: int) -> int:
        """
        Calculate payout based on game result.

        Args:
            result (str): The result string from game outcome
            bet (int): The original bet amount

        Returns:
            int: The payout amount
        """
        if "Blackjack" in result:
            return int(bet * 2.5)  # 3:2 payout for blackjack
        elif "win" in result or "busts" in result:
            return bet * 2  # 1:1 payout
        elif "Push" in result:
            return bet  # Return original bet
        elif "Surrender" in result:
            return bet // 2  # Return half the bet
        else:
            return 0  # Lose entire bet

    async def process_payout(self) -> int:
        """
        Process the payout for the Blackjack game based on the game outcome.

        Returns:
            int: The total payout amount
        """
        # Retrieve user's current Basedbucks
        user_data = kek_counter.find_one({"user_id": str(self.player_id)})
        current_balance = user_data.get('basedbucks', 0)

        # Handle split hand scenario
        if self.is_split:
            # Process primary hand payout
            primary_result = self._determine_hand_result(self.primary_hand, self.primary_hand_total, self.dealer_hand)
            primary_payout = self.calculate_payout(primary_result, self.bet_amount)

            # Process secondary hand payout
            secondary_result = self._determine_hand_result(self.secondary_hand, self.secondary_hand_total,
                                                           self.dealer_hand)
            secondary_payout = self.calculate_payout(secondary_result, self.secondary_bet)

            # Calculate total payout
            total_payout = primary_payout + secondary_payout

        else:
            # Determine result and calculate payout for single hand
            result = self.determine_winner()
            total_payout = self.calculate_payout(result, self.bet_amount)

        # Update user's balance
        new_balance = current_balance + total_payout

        # Update user's Basedbucks in the database
        kek_counter.update_one(
            {"user_id": self.player_id},
            {"$set": {"basedbucks": new_balance}}
        )

        return total_payout

    def _determine_hand_result(self, player_hand: List[anydeck.Card], player_total: int,
                               dealer_hand: List[anydeck.Card]) -> str:
        """
        Determine the result for a single hand when playing split.
        """
        dealer_total = self._calculate_hand_value(dealer_hand)

        if player_total > 21:
            return "Bust! You went over 21. Dealer wins. 💸"
        elif dealer_total > 21:
            return "Dealer busts! You win. Payout is 1:1. 💰"
        elif player_total > dealer_total:
            return "You win! Payout is 1:1. 💰"
        elif player_total < dealer_total:
            return "Dealer wins! You lose your bet. 💸"
        else:
            return "Push! It's a tie. Your bet is returned. 🔄"

    def _calculate_hand_value(self, hand: List[anydeck.Card]) -> int:
        """Calculate the total value of a hand, accounting for Aces."""
        total = sum(card.value for card in hand)
        ace_count = 0
        # Adjust for Aces
        for card in hand:
            if card.face == 'Ace':
                ace_count += 1
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1

        return total

    def create_game_embed(self, reveal_dealer: bool = False) -> hikari.Embed:
        """
        Modify game embed to show split hands if applicable.
        """
        embed = hikari.Embed(title="🃏 Blackjack", color=0x2B2D31)

        # Show current hand
        current_hand_str = ''
        for card in self.player_hand:
            current_hand_str += ' '.join(card.suit) + card.face

        hand_label = "Your Primary Hand" if self.is_split and self.current_hand_index == 0 else \
            "Your Secondary Hand" if self.is_split else "Your Hand"

        embed.add_field(
            name=f"{hand_label} (Total: {self.player_total})",
            value=current_hand_str,
            inline=False
        )

        # Show the other hand if split
        if self.is_split:
            other_hand = self.secondary_hand if self.current_hand_index == 0 else self.primary_hand
            other_hand_total = self.secondary_hand_total if self.current_hand_index == 0 else self.primary_hand_total

            other_hand_str = ''
            for card in other_hand:
                other_hand_str += ' '.join(card.suit) + card.face

            other_hand_label = "Your Secondary Hand" if self.current_hand_index == 0 else "Your Primary Hand"

            embed.add_field(
                name=f"{other_hand_label} (Total: {other_hand_total})",
                value=other_hand_str,
                inline=False
            )

        # Dealer's hand (existing implementation)
        if reveal_dealer:
            dealer_hand_str = ''
            for card in self.dealer_hand:
                dealer_hand_str += ' '.join(card.suit) + card.face
            embed.add_field(
                name=f"Dealer's Hand (Total: {self.dealer_total})",
                value=dealer_hand_str,
                inline=False
            )
        else:
            # Hide second card
            dealer_visible_hand = [self.dealer_hand[0].suit + self.dealer_hand[0].face, '🂠']
            dealer_hand_str = ' '.join(dealer_visible_hand)
            embed.add_field(
                name="Dealer's Hand",
                value=dealer_hand_str,
                inline=False
            )

        return embed

    def check_player_blackjack(self) -> bool:
        """Check if either player or dealer has a blackjack."""
        player_blackjack = self.player_total == 21

        if player_blackjack:
            self.game_over = True
            return True

        return False

    def check_dealer_blackjack(self) -> bool:
        """Check if the dealer has a blackjack."""
        dealer_blackjack = self._calculate_hand_value(self.dealer_hand) == 21

        if dealer_blackjack:
            self.game_over = True
            return True

        return False

    def hit(self) -> bool:
        """
        Modify hit method to work with split hands.
        """
        # Add card to the current hand
        new_card = self.deck.draw()
        self.player_hand.append(new_card)

        # Update the corresponding split hand
        if self.is_split:
            if self.current_hand_index == 0:
                self.primary_hand = self.player_hand.copy()
                self.primary_hand_total = self._calculate_hand_value(self.primary_hand)
            else:
                self.secondary_hand = self.player_hand.copy()
                self.secondary_hand_total = self._calculate_hand_value(self.secondary_hand)

        # Recalculate hand total
        self.player_total = self._calculate_hand_value(self.player_hand)

        # Check for bust
        return self.player_total > 21

    def split(self) -> bool:
        """
        Split the player's hand into two separate hands.

        Returns:
        bool: True if split is successful, False otherwise
        """
        # Check if splitting is possible (same card values)
        if not self.can_split:
            return False

        # Move one card to the secondary hand
        self.secondary_hand.append(self.primary_hand.pop())

        # Draw a new card for each hand
        self.primary_hand.append(self.deck.draw())
        self.secondary_hand.append(self.deck.draw())

        # Recalculate hand totals
        self.primary_hand_total = self._calculate_hand_value(self.primary_hand)
        self.secondary_hand_total = self._calculate_hand_value(self.secondary_hand)

        # Update player hand to current hand
        self.player_hand = self.primary_hand.copy()
        self.player_total = self.primary_hand_total

        # Update game state
        self.is_split = True
        self.current_hand_index = 0
        self.can_split = False  # Can only split once

        # Reset double down for individual hands
        self.can_primary_double_down = True
        self.can_secondary_double_down = True
        self.can_double_down = False  # Disable overall double down

        return True

    def switch_hand(self) -> None:
        """
        Switch between primary and secondary hands during play.
        """
        if not self.is_split:
            return

        # Update current hand index
        self.current_hand_index = 1 if self.current_hand_index == 0 else 0

        # Switch active hand
        if self.current_hand_index == 0:
            self.player_hand = self.primary_hand.copy()
            self.player_total = self.primary_hand_total
        else:
            self.player_hand = self.secondary_hand.copy()
            self.player_total = self.secondary_hand_total

    def dealer_play(self) -> None:
        """Dealer's turn to play according to standard Blackjack rules."""
        while self.dealer_total < 17:
            new_card = self.deck.draw()
            self.dealer_hand.append(new_card)
            self.dealer_total = self._calculate_hand_value(self.dealer_hand)

    def determine_winner(self) -> str:
        """Determine the winner of the game."""
        if self.player_total > 21:
            self.bet_amount = 0
            return "Bust! You went over 21. Dealer wins. You lose your bet. 💸"
        elif self.dealer_total > 21:
            self.bet_amount *= 2
            return "Dealer busts! You win. Payout is 1:1. 💰"
        elif self.player_total > self.dealer_total:
            self.bet_amount *= 2
            return "You win! Payout is 1:1. 💰"
        elif self.player_total < self.dealer_total:
            self.bet_amount = 0
            return "Dealer wins! You lose your bet. 💸"
        else:
            return "Push! It's a tie. Your bet is returned. 🔄"

class BlackjackMenu(lightbulb.components.Menu):
    def __init__(self, game: BlackjackGame) -> None:
        self.game = game

        # Dynamically create buttons based on game state
        self.buttons = []

        # Standard game buttons
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
        # Conditional buttons
        if self.game.can_split:
            self.split_button = self.add_interactive_button(
                hikari.ButtonStyle.PRIMARY,
                self.on_split,
                label="Split"
            )
        if self.game.can_double_down or (self.game.is_split and
                                         (self.game.current_hand_index == 0 and self.game.can_primary_double_down or
                                          self.game.current_hand_index == 1 and self.game.can_secondary_double_down)):
            self.double_down_button = self.add_interactive_button(
                hikari.ButtonStyle.PRIMARY,
                self.on_double_down,
                label="Double Down"
            )
        # Surrender always available early in the game
        self.surrender_button = self.add_interactive_button(
            hikari.ButtonStyle.SECONDARY,
            self.on_surrender,
            label="Surrender"
        )

        # Insurance button if dealer shows an Ace
        if self.game.is_insurance_offered:
            self.insurance_button = self.add_interactive_button(
                hikari.ButtonStyle.SUCCESS,
                self.on_insurance,
                label="Insurance"
            )

    async def predicate(self, ctx: lightbulb.components.MenuContext) -> bool:
        if ctx.user.id != self.game.player_id:
            await ctx.respond("You are not the player in this game.", flags=hikari.MessageFlag.EPHEMERAL)
            return False
        return True

    async def on_hit(self, ctx: lightbulb.components.MenuContext) -> None:
        """
        Modified hit method to handle potential game end and payout.
        """
        is_bust = self.game.hit()

        if is_bust:
            # If split, switch to secondary hand. If no secondary hand, end game
            if self.game.is_split:
                self.game.switch_hand()

                # If secondary hand is also bust, end game
                if self.game.player_total > 21:
                    self.game.secondary_bet = 0

                    # Process payout
                    total_payout = await self.game.process_payout()

                    await ctx.respond(
                        embed=self.game.create_game_embed(reveal_dealer=True),
                        edit=True,
                        content=f"🃏 Both hands bust! You lose.\nPayout: {total_payout} Basedbucks",
                        components=[]
                    )
                    return

                # Continue with secondary hand
                self.game.bet_amount = 0
                await ctx.respond(
                    content="🃏 First hand bust. Switching to secondary hand.",
                    embed=self.game.create_game_embed(),
                    edit=True,
                    components=self
                )
                return

            # Regular bust without split
            self.game.bet_amount = 0

            # Process payout
            total_payout = await self.game.process_payout()

            await ctx.respond(
                embed=self.game.create_game_embed(reveal_dealer=True),
                edit=True,
                content=f"🃏 Bust! You went over 21.\nPayout: {total_payout} Basedbucks",
                components=[]
            )
            return

        # Continue game with updated embed
        await ctx.respond(
            content=f"🃏 Hit! You got a {self.game.player_hand[-1].suit}{self.game.player_hand[-1].face}.",
            embed=self.game.create_game_embed(),
            edit=True,
            components=self
        )

    async def on_stand(self, ctx: lightbulb.components.MenuContext) -> None:
        """
        Modified stand method to handle split hands and payout.
        """
        if self.game.is_split:
            # If currently on primary hand, switch to secondary
            if self.game.current_hand_index == 0:
                self.game.switch_hand()
                await ctx.respond(
                    content="🃏 Switching to secondary hand.",
                    embed=self.game.create_game_embed(),
                    edit=True,
                    components=self
                )
                return

        # Final stand - play dealer's hand
        self.game.dealer_play()

        # Determine winner
        if self.game.is_split:
            # For split hands, handle potential different outcomes
            result_primary = self._determine_hand_result(
                self.game.primary_hand,
                self.game.primary_hand_total,
                self.game.dealer_hand
            )
            result_secondary = self._determine_hand_result(
                self.game.secondary_hand,
                self.game.secondary_hand_total,
                self.game.dealer_hand
            )

            result_text = f"Primary Hand: {result_primary}\nSecondary Hand: {result_secondary}"

            # Process payout for split hands
            total_payout = await self.game.process_payout()

            await ctx.respond(
                embed=self.game.create_game_embed(reveal_dealer=True),
                edit=True,
                content=f"🃏 Game Results:\n{result_text}\nTotal Payout: {total_payout} Basedbucks",
                components=[]
            )
        else:
            # Regular single hand result
            result = self.game.determine_winner()

            # Process payout
            total_payout = await self.game.process_payout()

            await ctx.respond(
                embed=self.game.create_game_embed(reveal_dealer=True),
                edit=True,
                content=f"🃏 {result}\nPayout: {total_payout} Basedbucks",
                components=[]
            )

    async def on_split(self, ctx: lightbulb.components.MenuContext) -> None:
        """
        Handle splitting the player's hand.
        """
        # Attempt to split the hand
        if self.game.split():
            # Update the embed to show both hands
            self.split_button.disabled = True
            self.game.secondary_bet = self.game.bet_amount
            await ctx.respond(
                content="🃏 Hand split! Playing first hand.",
                embed=self.game.create_game_embed(),
                edit=True,
                components=self
            )
        else:
            await ctx.respond(
                content="🃏 Cannot split this hand.",
                edit=True,
                components=self
            )

    async def on_double_down(self, ctx: lightbulb.components.MenuContext) -> None:
        # Handle double down for both regular and split hands
        if self.game.is_split:
            # Check which hand is currently active
            if self.game.current_hand_index == 0 and self.game.can_primary_double_down:
                # Double the bet for primary hand
                self.game.bet_amount *= 2
                self.game.can_primary_double_down = False
            elif self.game.current_hand_index == 1 and self.game.can_secondary_double_down:
                # Double the bet for secondary hand
                self.game.secondary_bet *= 2
                self.game.can_secondary_double_down = False
            else:
                await ctx.respond(
                    content="🃏 Cannot double down on this hand.",
                    edit=True,
                    components=self
                )
                return

            # Take one final card
            is_bust = self.game.hit()

            if is_bust:
                # Switch to secondary hand if available
                self.game.switch_hand()

                # If secondary hand is also bust, end game
                if self.game.player_total > 21:
                    self.game.secondary_bet = 0

                    # Process payout
                    total_payout = await self.game.process_payout()

                    await ctx.respond(
                        embed=self.game.create_game_embed(reveal_dealer=True),
                        edit=True,
                        content=f"🃏 Both hands bust after doubling down!\nPayout: {total_payout} Basedbucks",
                        components=[]
                    )
                    return

                # Continue with secondary hand
                await ctx.respond(
                    content="🃏 First hand bust after doubling down. Switching to secondary hand.",
                    embed=self.game.create_game_embed(),
                    edit=True,
                    components=self
                )
                return

        else:
            # Regular single hand double down
            if self.game.can_double_down:
                # Double the bet
                self.game.bet_amount *= 2
                self.game.can_double_down = False
                is_bust = self.game.hit()

                if is_bust:
                    # Process payout for bust
                    total_payout = await self.game.process_payout()

                    await ctx.respond(
                        embed=self.game.create_game_embed(reveal_dealer=True),
                        edit=True,
                        content=f"🃏 Bust! You went over 21 after doubling down.\nPayout: {total_payout} Basedbucks",
                        components=[]
                    )
                    return

                # Automatically stand after doubling down
                self.game.dealer_play()
                result = self.game.determine_winner()

                # Process payout
                total_payout = await self.game.process_payout()

                await ctx.respond(
                    embed=self.game.create_game_embed(reveal_dealer=True),
                    edit=True,
                    content=f"🃏 {result} (Double Down)\nPayout: {total_payout} Basedbucks",
                    components=[]
                )

    async def on_surrender(self, ctx: lightbulb.components.MenuContext) -> None:
        # Player surrenders, loses half the bet
        # Ensure surrender result is consistent with calculate_payout method
        result = "Surrender! Half your bet is returned. 🏳️"

        # Process payout
        total_payout = await self.game.process_payout()

        await ctx.respond(
            embed=self.game.create_game_embed(reveal_dealer=True),
            edit=True,
            content=f"🃏 {result}\nPayout: {total_payout} Basedbucks",
            components=[]
        )

    async def on_insurance(self, ctx: lightbulb.components.MenuContext) -> None:
        # Check if dealer has blackjack
        self.game.insurance_bet = self.game.bet_amount // 2

        if self.game.check_dealer_blackjack():
            # Insurance pays 2:1 if dealer has blackjack
            self.game.bet_amount = 0
            self.game.bet_amount += self.game.insurance_bet * 2

            # Process payout
            total_payout = await self.game.process_payout()

            await ctx.respond(
                embed=self.game.create_game_embed(reveal_dealer=True),
                edit=True,
                content=f"🃏 Dealer has Blackjack! Insurance pays out.\nPayout: {total_payout} Basedbucks",
                components=[]
            )
        else:
            self.insurance_button.disabled = True
            self.game.insurance_bet = 0

            # Process payout (will result in losing insurance bet)
            total_payout = await self.game.process_payout()

            await ctx.respond(
                embed=self.game.create_game_embed(),
                content=f"🃏 Dealer does not have Blackjack. You lose the insurance bet.\nPayout: {total_payout} Basedbucks",
                edit=True,
                components=self
            )

    def _determine_hand_result(self, player_hand: List[anydeck.Card], player_total: int, dealer_hand: List[anydeck.Card]) -> str:
        """
        Determine the result for a single hand when playing split.
        """
        dealer_total = self.game._calculate_hand_value(dealer_hand)

        if player_total > 21:
            return "Bust! You went over 21. Dealer wins. 💸"
        elif dealer_total > 21:
            return "Dealer busts! You win. Payout is 1:1. 💰"
        elif player_total > dealer_total:
            return "You win! Payout is 1:1. 💰"
        elif player_total < dealer_total:
            return "Dealer wins! You lose your bet. 💸"
        else:
            return "Push! It's a tie. Your bet is returned. 🔄"

@loader.command()
class BlackjackStart(
    lightbulb.SlashCommand,
    name="blackjack",
    description="Start a game of blackjack."
):
    bet = lightbulb.integer("bet", "Amount of basedbucks to bet on the game. CURRENTLY UNUSED", min_value=10, max_value=1000)

    @lightbulb.invoke
    async def blackjack(self, ctx: lightbulb.Context, client: lightbulb.GatewayEnabledClient) -> None:
        # Create game instance
        game = BlackjackGame(ctx.user.id)
        game.bet_amount = self.bet

        # Create menu with initial buttons
        menu = BlackjackMenu(game)

        if game.check_player_blackjack() and game.check_dealer_blackjack():
            await ctx.respond(
                content="🃏 Both you and the dealer have Blackjack! It's a push.",
                embed=game.create_game_embed(reveal_dealer=True),
                components=[]
            )
            return
        # Check for initial blackjack
        if game.check_player_blackjack():
            # Handle blackjack scenario (reveal dealer's hand, determine winner)
            await ctx.respond(
                content="🃏 Blackjack! You have a natural 21. Payout is 3:2.",
                embed=game.create_game_embed(),
                components=[]  # No more buttons if game is over
            )
            return

        # Respond with game embed and interactive buttons
        resp = await ctx.respond(
            content=f"🃏 Blackjack game started! Make your move. {'The dealer has an Ace, and offers insurance.' if game.is_insurance_offered else ''}",
            embed=game.create_game_embed(),
            components=menu
        )

        try:
            await menu.attach(client, wait=True, timeout=120)
        except asyncio.TimeoutError:
            await ctx.edit_response(
                resp,
                content="🃏 Blackjack game timed out. Game over.",
                components=[]
            )

@loader.command()
class BlackjackHelp(
    lightbulb.SlashCommand,
    name="blackjack-help",
    description="Get help with playing Blackjack."
):

        @lightbulb.invoke
        async def blackjack_help(self, ctx: lightbulb.Context) -> None:
            embed = hikari.Embed(
                title="🃏 Blackjack Help",
                color=0x2B2D31,
                description="Blackjack is a card game where the goal is to get as close to 21 as possible without going over."
            )
            embed.add_field(
                name="Game Rules",
                value="• The player and dealer are each dealt two cards.\n"
                    "• The player can choose to hit (draw a card) or stand (end turn).\n"
                    "• The dealer must hit until their hand value is 17 or higher.\n"
                    "• Aces can be counted as 1 or 11, face cards are worth 10.\n"
                    "• If the player's hand value exceeds 21, they bust and lose the game.\n"
                    "• The player wins if their hand value is higher than the dealer's without busting."
            )
            embed.add_field(
                name="Special Actions",
                value="• **Split:** If the player's initial hand has two cards of the same value, they can split the hand into two separate hands. The secondary hand has the same bet as the primary hand and has its own winnings.\n"
                    "• **Double Down:** The player can double their bet and draw one final card.\n"
                    "• **Surrender:** The player can surrender and lose half their bet.\n"
                    "• **Insurance:** If the dealer's visible card is an Ace, the player can buy insurance equal to half your original wager against a dealer Blackjack. If the dealer has Blackjack, the player wins 2:1. If not, the insurance bet is lost and the game continues as normal."
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
        total_loans = sum(debt["loan amount"] for debt in player_data.get("loan_debt", []))
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
                "$inc": {'total_debt': self.amount, 'basedbucks': self.amount},
                "$push": {
                    "loan_debt": {
                        "date": datetime.now(timezone.utc),
                        "loan amount": self.amount,
                        "apr": apr,
                        "last_increase": datetime.now(timezone.utc)
                    }
                },
                "$set": {"credit_score": new_credit_score}
            },
            upsert=True,
        )
        await ctx.respond(f"{ctx.member.mention} borrowed {self.amount} Basedbucks from the bank! Your new credit score is {new_credit_score}.")

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
            {"$set": {"loan_debt": player_data["loan_debt"], "total_debt": total_debt, "credit_score": new_credit_score},
            "$inc": {"basedbucks": original_amount * -1}}
        )

        await ctx.respond(f"{ctx.member.mention} repaid {original_amount} Basedbucks to the bank! Your new credit score is {new_credit_score}.")

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

VOLATILITY_RANGE = (0.01, 0.15)  # 1-15% daily price change
MAX_DAILY_CHANGE = 0.2  # 20% max daily change
MIN_STOCK_PRICE = 1  # Minimum stock price
MAX_STOCK_PRICE = 1000  # Maximum stock price

def initialize_stocks(stocks_collection):
    """
    Initialize stocks with starting prices and custom volatilities.

    Args:
        stocks_collection: MongoDB collection for stocks

    Returns:
        bool: True if stocks were initialized, False if already existed
    """
    # Check if stocks already exist
    existing_stocks = stocks_collection.find_one({})
    if existing_stocks and "stocks" in existing_stocks:
        print("Stocks already initialized. Skipping initialization.")
        return False

    # Initial stock data with custom volatilities
    # Volatility represents the maximum daily price change percentage
    initial_stocks = {
        "KEKI": {
            "name": "Kekistocracy Inc.",
            "price": 100.00,
            "volatility": 0.15,  # High volatility (15%)
            "last_updated": datetime.now(timezone.utc)
        },
        "BSDL": {
            "name": "BasedLife LLC",
            "price": 85.50,
            "volatility": 0.10,  # Moderate volatility (10%)
            "last_updated": datetime.now(timezone.utc)
        },
        "FUNI": {
            "name": "FunniColors",
            "price": 75.25,
            "volatility": 0.08,  # Lower volatility (8%)
            "last_updated": datetime.now(timezone.utc)
        },
        "CRYG": {
            "name": "Cring Cryptoo",
            "price": 55.75,
            "volatility": 0.20,  # Very high volatility (20%)
            "last_updated": datetime.now(timezone.utc)
        }
    }

    # Update the stocks collection
    stocks_collection.update_one(
        {},  # Match the single document
        {"$set": {"stocks": initial_stocks}},
        upsert=True  # Create if doesn't exist
    )

    print("Stocks initialized successfully!")
    return True

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

ECONOMIC_EVENT_PROBABILITY = 0.05  # 5% chance of an original economic event
MARKET_WIDE_BOOM_PROBABILITY = 0.01  # 1% chance of market-wide boom
MARKET_WIDE_BUST_PROBABILITY = 0.01  # 1% chance of market-wide bust
MEGA_EVENT_PROBABILITY = 0.001  # 0.1% chance of massive price swing
INTER_STOCK_EVENT_PROBABILITY = 0.02  # 2% chance of one stock rising while another falls

MEGA_EVENT_MULTIPLIER = 10  # 1000% price change
INTER_STOCK_MULTIPLIER = 1.5  # 50% price change for competing stocks
BOOM_MULTIPLIER = 1.5  # 50% price increase during a boom
BUST_MULTIPLIER = 0.5  # 50% price decrease during a bust


def generate_stock_price_change(
    current_price,
    stock_volatility,
    stocks_data=None,
    symbol=None,
    global_event=None  # New parameter to handle global events
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
    if global_event:
        if global_event['type'] == 'boom':
            return round(current_price * BOOM_MULTIPLIER, 2), "📈 Global Economic Boom! All stocks rise in value!", None
        elif global_event['type'] == 'bust':
            return round(current_price * BUST_MULTIPLIER, 2), "📉 Global Economic Downturn! All stocks fall in value!", None

    # Original economic event logic
    if random.random() < ECONOMIC_EVENT_PROBABILITY:
        event_type = random.choice(['boom', 'bust'])
        if event_type == 'boom':
            return round(current_price * BOOM_MULTIPLIER, 2), f"Economic Boom affecting {symbol}! Stock price rises quickly!"
        else:
            return round(current_price * BUST_MULTIPLIER, 2), f"Economic Bust affecting {symbol}! Stock price falls rapidly!"

    # Mega Event (Ultra-rare massive price swing)
    mega_event_roll = random.random()
    if mega_event_roll < MEGA_EVENT_PROBABILITY:
        direction = random.choice([-1, 1])
        new_price = current_price * (MEGA_EVENT_MULTIPLIER ** direction)
        event_desc = "🚨 MEGA EVENT: " + (
            f"Unprecedented Stock Surge! {symbol} is experiencing an incredibly large price surge!" if direction > 0 else
            f"Catastrophic Stock Collapse! " f"{symbol} is experiencing an incredibly large price crash!"
        )
        return round(new_price, 2), event_desc

    # Inter-Stock Event (One stock rises, another falls)
    if (stocks_data and symbol and
            random.random() < INTER_STOCK_EVENT_PROBABILITY):
        # Select a random competing stock
        competing_stocks = [
            s for s in stocks_data.keys() if s != symbol
        ]
        if competing_stocks:
            competing_symbol = random.choice(competing_stocks)

            # Rise for current stock
            new_price = current_price * INTER_STOCK_MULTIPLIER

            # Fall for competing stock
            competing_current_price = stocks_data[competing_symbol]['price']
            competing_new_price = competing_current_price * (1 / INTER_STOCK_MULTIPLIER)

            event_desc = f"🔀 Competitors face off: {symbol} Rises, {competing_symbol} Falls!"
            return (
                round(new_price, 2),
                event_desc,
                {
                    'symbol': competing_symbol,
                    'new_price': round(competing_new_price, 2)
                }
            )

    # Normal price change logic (if no special event occurs)
    volatility = random.uniform(0.01, stock_volatility)
    price_change = current_price * volatility * random.choice([-1, 1])
    max_change = current_price * MAX_DAILY_CHANGE
    price_change = max(-max_change, min(max_change, price_change))
    new_price = current_price + price_change

    return max(MIN_STOCK_PRICE, min(MAX_STOCK_PRICE, new_price)), None


@loader.task(lightbulb.crontrigger("0,30 * * * *"))
async def update_stock_prices(client: lightbulb.GatewayEnabledClient):
    """
    Periodically update stock prices with enhanced economic events.
    """
    # Fetch existing stocks
    existing_stocks = stocks.find_one({}) or {"stocks": {}}
    stocks_dict = existing_stocks["stocks"]

    global_event = None

    if random.random() < MARKET_WIDE_BOOM_PROBABILITY:
        global_event = {
            'type': 'boom',
            'multiplier': BOOM_MULTIPLIER,
            'message': "📈 Global Economic Boom! All stocks surging!"
        }
    elif random.random() < MARKET_WIDE_BUST_PROBABILITY:
        global_event = {
            'type': 'bust',
            'multiplier': BUST_MULTIPLIER,
            'message': "📉 Global Economic Downturn! All stocks plummeting!"
        }

    # Keep track of any significant events
    significant_events = []

    for symbol, stock_info in existing_stocks["stocks"].items():
        current_price = stock_info.get("price")
        stock_volatility = stock_info.get("volatility", 0.15)

        # Generate the new price and possible event description
        new_price, description, competing_stock_info = generate_stock_price_change(
            current_price,
            stock_volatility,
            stocks_data=stocks_dict,
            symbol=symbol,
            global_event=global_event  # Pass global event
        )

        # Prepare updated stock details
        update_details = {
            "name": stock_info["name"],
            "price": round(new_price, 2),
            "volatility": stock_volatility,
            "last_updated": datetime.now(timezone.utc)
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

            # Then announce specific stock events
            for _, event_description in significant_events:
                await client.app.rest.create_message(
                    channel,
                    content=f"🔔 Economic Event: {event_description}"
                )

async def generate_stock_price_graph():
    """
    Generate a graph of stock prices from historical data.

    Returns:
        hikari.Bytes: Graph image ready to be sent to Discord
    """
    # Retrieve historical stock price data for the last 30 days
    historical_data = list(stock_history.find().sort("timestamp", 1))

    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.title("Stock Prices Over Time", fontsize=15)
    plt.xlabel("Timestamp", fontsize=12)
    plt.ylabel("Price ($)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)

    # Track stocks to plot
    stocks_to_plot = {}

    # Collect and plot data for each stock
    for entry in historical_data:
        for symbol, stock_info in entry.get('stocks', {}).items():
            if symbol not in stocks_to_plot:
                stocks_to_plot[symbol] = {
                    'timestamps': [],
                    'prices': []
                }

            stocks_to_plot[symbol]['timestamps'].append(entry['timestamp'])
            stocks_to_plot[symbol]['prices'].append(stock_info['price'])

    # Plot each stock with a different color
    colors = ['blue', 'green', 'red', 'purple', 'orange']
    for i, (symbol, data) in enumerate(stocks_to_plot.items()):
        plt.plot(
            data['timestamps'],
            data['prices'],
            label=symbol,
            color=colors[i % len(colors)],
            marker='o',
            markersize=4
        )

    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    # Convert to hikari.Bytes for Discord
    return hikari.Bytes(buffer, 'stock_prices.png')

@loader.command
class BuyStock(
    lightbulb.SlashCommand,
    name="buy-stock",
    description="Buy stocks from the market"
):
    symbol = lightbulb.string("symbol", "Stock symbol to buy", choices=[
        lightbulb.Choice("KEKI", "KEKI"),
        lightbulb.Choice("BSDL", "BSDL"),
        lightbulb.Choice("FUNI", "FUNI"),
        lightbulb.Choice("CRYG", "CRYG")
    ])
    quantity = lightbulb.number("quantity", "Number of stocks to buy", min_value=1)

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

        # Update user's stocks and basedbucks
        kek_counter.update_one(
            {"user_id": str(ctx.member.id)},
            {
                "$inc": {"basedbucks": -total_cost},
                "$push": {
                    "stocks": {
                        "symbol": self.symbol,
                        "quantity": self.quantity,
                        "purchase_price": current_stock["price"],
                        "purchase_date": datetime.now(timezone.utc)
                    }
                }
            },
            upsert=True
        )

        await ctx.respond(
            f"Bought {self.quantity} stocks of {current_stock['name']} at ${current_stock['price']:.2f} each. "
            f"Total cost: ${total_cost:.2f} Basedbucks.")

@loader.command
class SellStock(
    lightbulb.SlashCommand,
    name="sell-stock",
    description="Sell stocks from your portfolio"
):
    symbol = lightbulb.string("symbol", "Stock symbol to sell", choices=[
        lightbulb.Choice("KEKI", "KEKI"),
        lightbulb.Choice("BSDL", "BSDL"),
        lightbulb.Choice("FUNI", "FUNI"),
        lightbulb.Choice("CRYG", "CRYG")
    ])
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
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):

        await ctx.defer()
        # Retrieve current stock information
        stock_data = stocks.find_one({})
        user_data = kek_counter.find_one({"user_id": str(ctx.member.id)})

        # Create embedded message for stocks
        embed = hikari.Embed(title="Stock Market Overview", color=hikari.Color.from_hex_code("#2ecc71"))

        # Add current stock prices
        if stock_data and "stocks" in stock_data:
            for symbol, details in stock_data["stocks"].items():
                embed.add_field(
                    name=f"{symbol} - {details['name']}",
                    value=(
                        f"Current Price: ${details['price']:.2f}\n"
                        f"Volatility: {details['volatility'] * 100:.1f}%"
                    ),
                    inline=False
                )

        # Add user's portfolio
        if user_data and "stocks" in user_data:
            portfolio_value = 0
            portfolio_details = ""

            stock_prices = stock_data.get("stocks", {}) if stock_data else {}

            for stock in user_data["stocks"]:
                current_stock = stock_prices.get(stock["symbol"], {})
                current_price = current_stock.get("price", stock["purchase_price"])
                total_value = current_price * stock["quantity"]
                portfolio_value += total_value

                # Calculate profit/loss
                profit_loss = (current_price - stock["purchase_price"]) * stock["quantity"]
                profit_loss_color = "🟢" if profit_loss > 0 else "🔴" if profit_loss < 0 else "➖"

                portfolio_details += (
                    f"{stock['symbol']} - {stock['quantity']} shares\n"
                    f"Purchase Price: ${stock['purchase_price']:.2f}\n"
                    f"Current Price: ${current_price:.2f}\n"
                    f"Total Value: ${total_value:.2f}\n"
                    f"Profit/Loss: {profit_loss_color} ${profit_loss:.2f}\n\n"
                )

            embed.add_field(
                name="Your Portfolio",
                value=portfolio_details or "No stocks owned",
                inline=False
            )
            embed.add_field(
                name="Total Portfolio Value",
                value=f"${portfolio_value:.2f}",
                inline=False
            )

        # Generate stock price graph
        try:
            stock_graph = await generate_stock_price_graph()
            resp = await ctx.respond(
                embed=embed,
                attachment=stock_graph
            )
        except Exception as e:
            # Use edit_initial_response instead of responding again
            await ctx.edit_response(
                resp,
                content=f"Could not generate stock price graph: {str(e)}"
            )