import hikari
import lightbulb
import random
import string


from database import kek_counter, gambling_list, stocks

from datetime import datetime, timezone
from lightbulb import Choice
from dateutil import parser as dateutil_parser

import parsedatetime

loader = lightbulb.Loader()
OWNER_ID = 453445704690434049

STOCK_SYMBOLS = {
    "KEKI": "Kekistocracy Inc.",
    "BSDL": "BasedLife LLC",
    "FUNI": "FunniColors",
    "CRYG": "Cring Cryptoo"
}

@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
async def me_only(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if ctx.user.id != OWNER_ID:
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


# You'll need to modify the generate_stock_price_change function to use stock-specific volatility
def generate_stock_price_change(current_price, stock_volatility):
    """
    Generate a more realistic stock price change using a random walk model
    with stock-specific volatility.

    Args:
        current_price (float): Current stock price
        stock_volatility (float): Maximum daily volatility for this stock

    Returns:
        float: New stock price after simulated change
    """
    # Randomly choose volatility within the stock's volatility range
    volatility = random.uniform(0.01, stock_volatility)

    # Generate price change with some randomness and trend
    change_direction = random.choice([-1, 1])  # Randomly go up or down
    price_change = current_price * volatility * change_direction

    # Limit the maximum change percentage
    max_change = current_price * MAX_DAILY_CHANGE
    price_change = max(-max_change, min(max_change, price_change))

    new_price = current_price + price_change

    # Enforce price boundaries
    return max(MIN_STOCK_PRICE, min(MAX_STOCK_PRICE, new_price))


# Update the update_stock_prices function to use stock-specific volatility
@loader.task(lightbulb.uniformtrigger(minutes=30))
async def update_stock_prices():
    """
    Periodically update stock prices with some randomness in timing.
    """
    # Randomize the actual update interval slightly
    variation = random.uniform(0.8, 1.2)

    # Find existing stocks or initialize if not present
    existing_stocks = stocks.find_one({}) or {"stocks": {}}

    for symbol, stock_info in existing_stocks["stocks"].items():
        # Get current stock price and volatility
        current_price = stock_info.get("price", 100)
        stock_volatility = stock_info.get("volatility", 0.15)  # Default to 15% if not specified

        # Generate new price with stock-specific volatility
        new_price = generate_stock_price_change(current_price, stock_volatility)

        # Update stock data
        stocks.update_one(
            {},  # Update the single document
            {
                "$set": {
                    f"stocks.{symbol}": {
                        "name": stock_info["name"],
                        "price": round(new_price, 2),
                        "volatility": stock_volatility,
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            },
            upsert=True  # Create document if it doesn't exist
        )


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

        await ctx.respond(embed=embed)