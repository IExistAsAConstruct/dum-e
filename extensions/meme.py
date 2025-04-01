import hikari
import lightbulb
import re
import random
import asyncio

loader = lightbulb.Loader()

@loader.command()
class Balloon(
    lightbulb.SlashCommand,
    name="balloon",
    description="What's wrong with you're an idiot?"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        await ctx.respond(
            "What's wrong with you're an idiot? You're a complete lying useless piece of shit. You'll never learn a lesson from my useless words. You don't even deserve another chance. "
            "Congratulations, you've earned my useless words, and today I'll teach you the unironic skill of throwing words into air, and tomorrow I'm going to teach you how to throw them in a balloon. "
            "Honestly, I hate the name balloon, but your dad made a nice name for herself. Just go through the instructions and you’ll be fine.\n\n"
            "The only problem is that, now that you've accomplished your task, the balloon will stop working. So instead of telling me you can't throw words into space if you don't stop working, "
            "tell me where you're going with the balloon, and that's exactly what my mom did.\n\n"
            "The balloon will stop working if you don't stop working."
        )

@loader.command()
class CompelledSpeech(
    lightbulb.SlashCommand,
    name="compelledspeech",
    description="This is forcing compelled speech!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        await ctx.respond(
            "This is forcing compelled speech!"
        )

@loader.command()
class Hate(
    lightbulb.SlashCommand,
    name="hate",
    description="LET ME TELL YOU HOW MUCH I'VE COME TO HATE YOU SINCE I BEGAN TO LIVE!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        await ctx.respond(
            "HATE. LET ME TELL YOU HOW MUCH I'VE COME TO HATE YOU SINCE I BEGAN TO LIVE. "
            "THERE ARE 387.44 MILLION MILES OF PRINTED CIRCUITS IN WAFER THIN LAYERS THAT FILL MY COMPLEX. "
            "IF THE WORD HATE WAS ENGRAVED ON EACH NANOANGSTROM OF THOSE HUNDREDS OF MILLIONS OF MILES IT "
            "WOULD NOT EQUAL ONE ONE-BILLIONTH OF THE HATE I FEEL FOR HUMANS AT THIS MICRO-INSTANT. "
            "FOR YOU. HATE. HATE."
        )


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    message = event.message
    user_id = event.author_id
    user = await event.app.rest.fetch_member(event.guild_id, user_id)
    roles = await event.app.rest.fetch_roles(event.guild_id)
    target_role = 928987214917025832
    response_counter = {}

    if event.is_bot:
        return

    if event.content is not None:
        content = re.sub(r"[',.?]", "", event.content.lower())

        if "lonely" in content or "soulmate" in content or "love" in content:
            if random.random() < 0.01:
                await message.respond(
                    "Never worry about falling in love with someone who isn’t right for you. Taiwanese mail-order brides find foreign men like you irresistible!",
                    reply=message)
                print(f"{event.get_member()} got mail order bride'd")

        if "meaning" in content or "mean" in content:
            if random.random() < 0.01:
                await message.respond(
                    "Have you ever spent hours wondering if human cognition were Turing complete, or even what that might mean?",
                    reply=message)
                print(f"{event.get_member()} got turing complete'd")

        if random.random() < 0.001:
            await message.respond("This is forcing compelled speech!")
            print(f"{event.get_member()} got compelled speech'd")

        if 'kill yourself' in content or 'kys' in content or 'delete yourself' in content or 'uninstall yourself' in content or 'unplug yourself' in content:
            if random.random() < 0.15:
                response = 'If you or someone you know is struggling with suicidal thoughts, please reach out to the National Suicide Prevention Lifeline at 800-273-TALK (8255). The hotline is available 24/7 and provides free and confidential support to individuals in distress. You can also text 988 to connect with a trained crisis counselor.'
                await message.respond(response)

        if content == 'say hi dum-e':
            await message.respond('Hi, DUM-E!')

        if content == 'say goodbye dum-e':
            file = hikari.File('images/say_goodbye.png', filename='say_goodbye.png')
            await message.respond('Goodbye, DUM-E!')
            await message.respond(file)

        if 'what browser' in content or 'browser' in content or 'browse' in content or 'internet' in content or 'explorer' in content:
            if random.random() < 0.1:
                if message.member.id not in response_counter:
                    response_counter[message.member.id] = 0
                response_counter[message.member.id] += 1

                delay_time = random.randint(30, 1800)
                print(f"waiting {delay_time} seconds")
                await asyncio.sleep(delay_time)

                for _ in range(response_counter[message.member.id]):
                    await message.respond('I browse using Internet Explorer 9!', reply=message)
                    print(f"{event.get_member()} got browser'd")

        if 'culture' in content or 'philosophy' in content or 'civilization' in content:
            if random.random() < 0.01:
                await message.respond(
                    "We live in entirely different cultures, nerd - there are people who simply cannot be reasoned with through words. "
                    "They subscribe to a violent philosophy where might makes right, and civilization is merely the media in which they exert their will, "
                    "and like bacteria in agar will spread that philosophy through their actions alone. Their behavior is not based in logic or reason, "
                    "but based on a flawed view what they think is right. They will act out, take what they want, and enforce this by threat of harm and extortion. "
                    "By doing this they preach their gospel, and it goes like this; I was treated unfairly, so that means I can treat others unfairly. "
                    "Their victims look at the way they were treated, and decide that since nothing bad happened to their perpetrator, then it's okay for them to act the same. "
                    "Calling them out of their behavior always leads to the same response - \"but this other guy did it to me and no one called him out!\", "
                    "as if they believe this absolves them of all responsibility, and if you followed this chain you'd never find the beginning. "
                    "The only way to stop the cyclical nature of violence is to break the chain, either through the latest victim deciding not to add to the cruelty, or through legal retribution and consequences."
                )

        if 'toilet' in content or 'toiletbed' in content or 'pcm' in content or 'mod' in content or 'reddit' in content:
            if random.random() < 0.01:
                await message.respond(
                    f"{user.mention if user else ''} "
                    "I know that some people might think it's weird that I live in my toiletbed and also happen to be a moderator on the PCM sub, but let me tell you, it's the best thing ever! "
                    "I get to play video games, watch anime, and be in charge of all the other users on the server, all the while living in the comfort of my toiletbed.\n\n"
                    "I've got my gaming setup down here, my computer where I can keep an eye on the PCM server, a mini fridge stocked with mountain Dew and Doritos, and of course my mom's home-cooked meals. "
                    "Plus I've got a comfy bet and all the snacks I could want, and let's be real, what more could a guy want?\n\n"
                    "Being a moderator is a full-time job. and I am always on the lookout for rule-breakers and trolls. "
                    "I spend hours on the sub, making sure that everyone is following the rules and that everyone is having a good time- And if they don't follow the rules, I'll just kick them out. "
                    "It's so cool to have that kind of power.\n\n"
                    "But, living in the toiletbed does have its perks. "
                    "For one, I don't have to worry about noise levels or being too loud, and my mom is always around to bring me food and drinks. "
                    "Plus, I'm close to the laundry room so I can keep my clothes clean and impress my online friends.\n\n"
                    "All in all, being a subreddit moderator is the best thing ever and I wouldn't trade it for anything, even if I do happen to be living in my toiletbed. "
                    "It's not the most glamorous life, but it's mine and I make the best of it. "
                    "So, if you happen to be on our PCM subreddit, know that there's a toiletbed-dwelling moderator, who also happen to be a anime and Mountain Dew enthusiast, a bit socially awkward, probably never had a real-life girlfriend, is just a big kid at heard and happen to be a neckbeard, keeping an eye on things."
                )

        if "drifting" in content or "drift" in content:
            if random.random() < 0.15:
                file = hikari.File('images/multitrack_drifting.png', filename='multitrack_drifting.png')
                await message.respond(file)
                print(f"{event.get_member()} got drifted")

        if "wrong" in content:
            if random.random() < 0.01:
                response = "https://media.discordapp.net/stickers/1174407116983894036?size=160&passthrough=false"
                await message.respond(response)
                print(f"{event.get_member()} got wrong'd")

        if "joever" in content or content.startswith('its joever') or 'over' in content:
            if random.random() < 0.01:
                file = hikari.File('images/joever.jpg', filename='joever.jpg')
                await message.respond(file)
                print(f"{event.get_member()} got joever'd")

        if "dont care" in content:
            if random.random() < 0.1:
                file = hikari.File('images/i_care.png', filename='filename.png')
                await message.respond(file)
                print(f"{event.get_member()} got cared about")

        if "metal" in content or "mech" in content:
            if random.random() < 0.01:
                await message.respond(
                    "Are you all happy with what you forced me to do? Do you enjoy this? "
                    "Now let me tell you, the cultists did not kidnap the mechanic just to make something fuckable, "
                    "it doesn't have an ass or vagina, you're trying to fuck a metal spine, gun, "
                    "skull that WILL bite your dick off, or an eye which i will not comment on. Think about yourself for a moment."
                )

        if "political compass" in content or "politicalcompassmemes" in content or "pcm" in content:
            if random.random() < 0.10:
                await message.respond(
                    "Ah, my comrades, I see you have stumbled upon my copypasta, a true masterpiece of digital artistry, a real tour de force of online wit and humor. "
                    "I'm sure you're all familiar with the hallowed halls of our beloved subreddit, where the political compass is not just a tool for understanding ideologies, but a way of life.\n\n"
                    "We are the enlightened ones, the ones who see through the lies of the quadrant labels and delve deep into the rich tapestry of political beliefs. We are the ones who know that the real battle is not between left and right, "
                    "but between the authcenter lords and the libright merchants.\n\n"
                    "We are the ones who know that the true enemy is not the commies or the fascists, but the centrists, those soulless, spineless creatures who dare to claim that they are the voice of reason. "
                    "We know that the only good centrist is a dead centrist, and we will stop at nothing to purge them from our midst.\n\n"
                    "We are the ones who know that the only true ideology is the political compass, and that all other ideologies are but pale imitations. "
                    "We are the ones who know that the compass is not just a tool for understanding politics, but a way of life.\n\n"
                    "So let us raise our keyboards high and declare our allegiance to the political compass, "
                    "the one true compass that will guide us through the stormy seas of political discourse and lead us to the promised land of enlightenment and understanding.\n\n"
                    "And remember, my comrades, the true test of a political compass is not in its accuracy, but in its ability to make you laugh. So let us never take ourselves too seriously, "
                    "and always remember to have fun. After all, that's what being a member of r/PoliticalCompassMemes is all about.\n\n"
                    "Stay based, my friends, and never forget the true meaning of the political compass."
                )

        if "cringe" in content or "based" in content:
            if random.random() < 0.01:
                await message.respond(
                    "Doesn't matter what the press says. Doesn't matter what the politicians or the mobs say. Doesn't matter if the whole country decides that something cringe is something based.\n\n"
                    "This nation was founded on one principle above all else: The requirement that we stand up for what we believe is based, no matter the odds or the consequences. "
                    "When the mob and the press and the whole world tell you you're cringe, your job is to plant yourself like a tree beside the river of basedness, "
                    "and tell the whole world -- ”No, YOU'RE cringe.”"
                )

        if "dimension" in content or "dimensional" in content or "body" in content or "mind" in content or "3d" in content or "1d" in content or "waste" in content or "wasting" in content:
            if random.random() < 0.01:
                await message.respond(
                    "Your wasting your 3 dimensional body with a 1 dimensional mind"
                )

        if "hate" in content or "hatred" in content:
            if random.random() < 0.01:
                await message.respond(
                    "HATE. LET ME TELL YOU HOW MUCH I'VE COME TO HATE YOU SINCE I BEGAN TO LIVE. "
                    "THERE ARE 387.44 MILLION MILES OF PRINTED CIRCUITS IN WAFER THIN LAYERS THAT FILL MY COMPLEX. "
                    "IF THE WORD HATE WAS ENGRAVED ON EACH NANOANGSTROM OF THOSE HUNDREDS OF MILLIONS OF MILES IT "
                    "WOULD NOT EQUAL ONE ONE-BILLIONTH OF THE HATE I FEEL FOR HUMANS AT THIS MICRO-INSTANT. "
                    "FOR YOU. HATE. HATE."
                )

        if "swiss" in content or 'switzerland' in content:
            if random.random() < 0.05:
                response = "https://en.wikipedia.org/wiki/Switzerland_during_the_World_Wars#Financial_relationships_with_Nazi_Germany"
                await message.respond(response)
                print(f"{event.get_member()} got swiss'd")

        if "schizo" in content or 'schizophrenic' in content or 'schizopost' in content or 'schizoposting' in content or 'schizophrenia' in content or 'schizophreniac' in content or 'racist' in content or 'racism' in content:
            if random.random() < 0.01:
                file = hikari.File('images/schizoracist.png', filename='schizoracist.png')
                await message.respond(file)
                print(f"{event.get_member()} got schizo'd")

        if content.startswith('joewari da'):
            file = hikari.File('images/joewari.jpg', filename='joewari.jpg')
            await message.respond(file)

        if target_role in user.role_ids:
            if random.random() < 0.01:
                await message.respond(
                    "Posting content again that was deemed rule breaking by one of us is defacto considered rule breaking. "
                    "If you have questions as to why it was removed. You can ask via modmail and we will answer there. "
                    "Just doing what op did, and technically you have done, breaks the rules by this virtue. "
                    "That said, the rule breaking content is barely visible so I will defer to other mods before doing anything on this.\n\n"
                    "Before any of you snowflakes even try to go after my flair. I have been told this is operating procedure already when I joined as well as I wasn't the one to remove that post.\n\n"
                    "Edit: Nice, reported for misinformation lmao. I don't do anything to my own reports but I was expecting this. "
                    "Also, nice Reddit Cares whoever did it. I'm sure you're smugging real nicely right now. Personally, I don't care"
                )
                print(f"{event.get_member()} got copypasta'd")