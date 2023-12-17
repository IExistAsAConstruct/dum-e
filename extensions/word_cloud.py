from wordcloud import WordCloud
import matplotlib.pyplot as plt
from pymongo import MongoClient
from typing import Optional
import re
import os
import dotenv

import hikari
import lightbulb

dotenv.load_dotenv()

wordcloud_plugin = lightbulb.Plugin("Word Cloud")

cluster = MongoClient(f"{os.environ['DB_URI']}")
db = cluster["based_count"]
collection = db["messages"]

target_usernames = []

@wordcloud_plugin.command
@lightbulb.option("user", "The user to get a word cloud from.", hikari.User, required=False)
@lightbulb.command("wordcloud", "Generates a word cloud based on a user's messages.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def wordcloud(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    try:
        user = user.username if user else ctx.author.username
        target_usernames = [user]
        
        url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

            # Retrieve text contents from MongoDB for specified usernames
        text_data = " ".join([message["content"] for message in collection.find({
            "author_username": {"$in": target_usernames},
            "content": {"$not": re.compile(url_regex)}  # Exclude messages with URLs
        })])

            # Preprocess text data (you may need to adjust this based on your specific requirements)
            # For example, you might want to use a more sophisticated text preprocessing library like nltk.
        processed_text = text_data.lower()  # Convert to lowercase for consistency

            # Generate Word Cloud
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(processed_text)

            # Alternatively, save the Word Cloud to a file
        wordcloud.to_file("wordcloud.png")
        file = hikari.File('wordcloud.png', filename='wordcloud.png')
        await ctx.respond(file)
    except ValueError:
        await ctx.respond(f"Error! Could not get value for word cloud.")

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(wordcloud_plugin)