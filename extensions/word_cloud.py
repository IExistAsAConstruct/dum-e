import re
from typing import Optional

import hikari
import lightbulb
from dotenv import main

from database import collection
from wordcloud import WordCloud, STOPWORDS

main.load_dotenv()

loader = lightbulb.Loader()

@loader.command
class WordCloudGenerate(
    lightbulb.SlashCommand,
    name="wordcloud",
    description="Generates a word cloud based on a user's messages."
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, user: Optional[hikari.User] = None) -> None:
        length = 0
        try:
            user = user.username if user else ctx.member.username
            target_usernames = [user]
            await ctx.respond(f"Generating {user}'s wordcloud...")
            url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

            # Retrieve text contents from MongoDB for specified usernames
            text_data = " ".join([
                message["content"] for message in collection.find({
                    "author_username": {"$in": target_usernames},
                    "content": {"$not": re.compile(url_regex), "$ne": None}  # Exclude messages with URLs
                })
            ])
            for message in collection.find({
                "author_username": {"$in": target_usernames},
                "content": {"$not": re.compile(url_regex), "$ne": None}  # Exclude messages with URLs
            }):
                length += 1

            # Preprocess text data
            processed_text = text_data.lower()  # Convert to lowercase for consistency

            # Remove short words and single letters
            words = processed_text.split()
            words = [word for word in words if len(word) > 2]

            # Remove stop words
            stop_words = set(STOPWORDS)
            words = [word for word in words if word not in stop_words]

            # Join the words back into a single string
            processed_text = " ".join(words)

            # Generate Word Cloud
            wordcloud = WordCloud(width=800, height=400, background_color="white").generate(processed_text)

            # Alternatively, save the Word Cloud to a file
            wordcloud.to_file("wordcloud.png")
            file = hikari.File('wordcloud.png', filename='wordcloud.png')
            await ctx.client.app.rest.create_message(ctx.channel_id,
                                              content=f"{user}'s wordcloud generated. Messages considered: {length}",
                                              attachment=file)
        except ValueError:
            await ctx.respond(f"Error! Could not generate word cloud.")