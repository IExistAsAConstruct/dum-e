from datetime import datetime, timedelta, timezone
import random
import re
import os
import asyncio
import httpx

from database import daily_word, kek_counter

import hikari
import lightbulb

loader = lightbulb.Loader()

WORDSAPI_KEY = os.getenv("WORDSAPI_KEY")
WORDS_URL = "https://wordsapiv1.p.rapidapi.com/words/"
BOT_CHANNEL_ID = 1147008618894471188
#BOT_CHANNEL_ID = 1178375823812735069
MAX_RETRIES = 100

def is_single_word(word: str) -> bool:
    return " " not in word and "-" not in word

def is_variant_of(word: str, synonym: str) -> bool:
    """
    Checks if the synonym is a spaced, hyphenated, or minor case variant of the original word.
    """
    word_normal = re.sub(r"[-_\s]", "", word.lower())
    synonym_normal = re.sub(r"[-_\s]", "", synonym.lower())
    return word_normal == synonym_normal

async def get_random_word() -> dict:
    headers = {
        "X-RapidAPI-Key": WORDSAPI_KEY,
        "X-RapidAPI-Host": "wordsapiv1.p.rapidapi.com"
    }
    params = {
        "random": "true",
        "hasDetails": "definitions,synonyms,antonyms,examples",
        "frequencyMin": "2.5"
    }

    async with httpx.AsyncClient() as client:
        for _ in range(MAX_RETRIES):
            resp = await client.get(WORDS_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            word = data.get("word", "")
            if is_single_word(word):
                return data
        raise ValueError("Could not find a single word with clueable data in time.")

def get_clean_synonyms(data: dict) -> list:
    raw_synonyms = []
    for result in data.get("results", []):
        raw_synonyms += result.get("synonyms", [])
    return list({
        syn for syn in raw_synonyms
        if not is_variant_of(data["word"], syn)
    })

def make_clue(data: dict) -> str:
    templates = []
    removed = ""
    for sense in data.get("results", []):
        defn = sense.get("definition", "")
        if defn and data["word"].lower() in defn.lower():
            removed = re.sub(re.escape(data["word"]), "_____", defn, flags=re.IGNORECASE)
        templates.append(f"{removed if removed else defn} ({len(data['word'])} letters)")

    syns = get_clean_synonyms(data)
    if syns:
        syn = random.choice(syns)
        templates.append(f"Synonym of {syn}")

    ants = data.get("results", [{}])[0].get("antonyms", [])
    if ants:
        ant = random.choice(ants)
        templates.append(f"Antonym of {ant}")

    example_sentence = data.get("results", [{}])[0].get("examples", [])
    if example_sentence:
        example = random.choice(example_sentence)
        blanked = example.replace(re.escape(data["word"]), "_____")
        templates.append(f"{blanked}")

    return random.choice(templates) if templates else "No clue available."

def build_daily_hint_embed(word: str, hint: str) -> hikari.Embed:
    embed = hikari.Embed(
        title="📅 New Daily Word Challenge",
        description="A new word has been selected!\n\n" +
                    f"**Hint:** {hint}\n" +
                    "Earn **100 Basedbucks** if you get it right!",
        color=0x3498db,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{len(word)} letters • Guess with /guessword")
    return embed

@loader.task(lightbulb.crontrigger("0 4 * * *"))
async def rotate_daily_word(client: lightbulb.Client) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = await get_random_word()
    word = data["word"]
    hint = make_clue(data)

    daily_word.update_one(
        {"date": today},
        {"$set": {"word": word, "hint": hint, "solved": False, "solvers": []}},
        upsert=True
    )

    embed = build_daily_hint_embed(word, hint)
    channel = await client.app.rest.fetch_channel(BOT_CHANNEL_ID)
    await client.app.rest.create_message(channel,
        embed=embed
    )

@loader.command()
class WordGame(
    lightbulb.SlashCommand,
    name="wordhint",
    description="Get the hint of the word of the day."
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, client: lightbulb.Client) -> None:
        await ctx.defer()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = daily_word.find_one({"date": today})

        if not data:
            await ctx.respond("No word of the day found.")
            return

        solved_message = "✅ You’ve already solved this!" if ctx.user.id in [s["user_id"] for s in data["solvers"]] else "❌ You haven't solved this yet."

        embed = hikari.Embed(
            title="🧠 Daily Word Challenge",
            description=f"**Hint:** {data['hint']}\n\n" +
                        solved_message,
            color=0x5865F2
        )
        embed.add_field(
            name="Solvers",
            value="\n".join(
                f"<@{s['user_id']}>" for s in data["solvers"]
            ) if data["solvers"] else "No one has solved it yet.",
            inline=False
        )
        embed.set_footer(text="Use /guessword to submit your answer!")
        await ctx.respond(embed=embed)
        channel = await client.app.rest.fetch_channel(BOT_CHANNEL_ID)

@loader.command()
class GuessWord(
    lightbulb.SlashCommand,
    name="guessword",
    description="Submit your guess for the daily word."
):

    guess = lightbulb.string('guess', "Your guess for the daily word.")
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, client: lightbulb.Client) -> None:

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = daily_word.find_one({"date": today})

        if not data:
            await ctx.respond("No word of the day found.")
            return

        if data["solved"] and ctx.user.username in [s["user_id"] for s in data["solvers"]]:
            await ctx.respond("This word has already been solved by you!")
            return

        guess = self.guess.lower()
        if guess == data["word"].lower():
            channel = await client.app.rest.fetch_channel(BOT_CHANNEL_ID)
            daily_word.update_one(
                {"date": today},
               {"$set": {"solved": True}, "$push": {"solvers": {"user_id": ctx.user.id}}}
            )
            await ctx.respond(f"Congratulations! You guessed the word: **{data['word']}** 🎉", ephemeral=True)
            await client.app.rest.create_message(channel,
                f"<@{ctx.user.id}> guessed the word and earned 100 Basedbucks! 🎉")
            kek_counter.update_one(
                {"user_id": str(ctx.member.id)},
                {"$inc": {"basedbucks": 100}}
            )
        else:
            await ctx.respond(f"Incorrect guess! Try again.")