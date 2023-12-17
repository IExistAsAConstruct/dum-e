from datetime import datetime
from typing import Optional
import re
import random
import asyncio

import hikari
import lightbulb

meme_plugin = lightbulb.Plugin("Memes")

target_user_id = 146996859183955968


@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("balloon", "What's wrong with you're an idiot...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def balloon(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "What's wrong with you're an idiot? You're a complete lying useless piece of shit. You'll never learn a lesson from my useless words. You don't even deserve another chance. "
        "Congratulations, you've earned my useless words, and today I'll teach you the unironic skill of throwing words into air, and tomorrow I'm going to teach you how to throw them in a balloon. "
        "Honestly, I hate the name balloon, but your dad made a nice name for herself. Just go through the instructions and you’ll be fine.\n\n"
        "The only problem is that, now that you've accomplished your task, the balloon will stop working. So instead of telling me you can't throw words into space if you don't stop working, "
        "tell me where you're going with the balloon, and that's exactly what my mom did.\n\n"
        "The balloon will stop working if you don't stop working."
    )
        
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("toiletbed", "I know that some people might think it's weird that I live in my toilet bed...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def toiletbed(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
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
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("navyseals", "What the fuck did you just fucking say about me, you little bitch?", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def navyseals(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "What the fuck did you just fucking say about me, you little bitch? " 
        "I'll have you know I graduated top of my class in the Navy Seals, and I've been involved in numerous secret raids on Al-Quaeda, and I have over 300 confirmed kills. "
        "I am trained in gorilla warfare and I'm the top sniper in the entire US armed forces. You are nothing to me but just another target. "
        "I will wipe you the fuck out with precision the likes of which has never been seen before on this Earth, mark my fucking words. "
        "You think you can get away with saying that shit to me over the Internet? Think again, fucker. "
        "As we speak I am contacting my secret network of spies across the USA and your IP is being traced right now so you better prepare for the storm, maggot. "
        "The storm that wipes out the pathetic little thing you call your life. You're fucking dead, kid. "
        "I can be anywhere, anytime, and I can kill you in over seven hundred ways, and that's just with my bare hands. "
        "Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the United States Marine Corps "
        "and I will use it to its full extent to wipe your miserable ass off the face of the continent, you little shit. "
        "If only you could have known what unholy retribution your little \"clever\" comment was about to bring down upon you, maybe you would have held your fucking tongue. "
        "But you couldn't, you didn't, and now you're paying the price, you goddamn idiot. "
        "I will shit fury all over you and you will drown in it. You're fucking dead, kiddo."
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("authtrumpism", "auth is just fascism, or as I like to call it, trumpism", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def authtrumpism(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "auth is just fascism, or as I like to call it, trumpism"
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("postingcontent", "Posting content again that was deemed rule-breaking...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def postingcontent(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "Posting content again that was deemed rule breaking by one of us is defacto considered rule breaking. "
        "If you have questions as to why it was removed. You can ask via modmail and we will answer there. "
        "Just doing what op did, and technically you have done, breaks the rules by this virtue. "
        "That said, the rule breaking content is barely visible so I will defer to other mods before doing anything on this.\n\n"
        "Before any of you snowflakes even try to go after my flair. I have been told this is operating procedure already when I joined as well as I wasn't the one to remove that post.\n\n"
        "Edit: Nice, reported for misinformation lmao. I don't do anything to my own reports but I was expecting this. "
        "Also, nice Reddit Cares whoever did it. I'm sure you're smugging real nicely right now. Personally, I don't care"
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("dekekcomment", "I just dekek'd your comment.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def dekekcomment(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "I just dekek'd your comment.\n\n# FAQ\n## What does this mean?\n"
        "The amount of keks (laughs) on your leaderboard entry and discord account has decreased by one.\n\n"
        "## Why did you do this?\nThere are several reasons I may deem a comment to be unworthy of positive or neutral keks. "
        "These include, but are not limited to:\n\n"
        "* Rudeness towards other Discorders.\n"
        "* Spreading incorrect information,\n"
        "* Sarcasm not correctly flagged with a /s.\n\n"
        "## Am I banned from the Discord?\nNo - not yet. But you should refrain from making comments like this in the future. "
        "Otherwise, I will be forced to issue an additional dekek, which may put your commenting and posting privileges in jeopardy.\n\n"
        "## I don't believe my comment deserved a dekek. Can you un-dekek it?\nSure, mistakes happen. But only in exceedingly rare "
        "circumstances will I undo a dekek. If you would like to issue an appeal, shoot me a private message explaining what I got wrong. "
        "I tend to respond to Discord PMs within several minutes. Do note, however, that over 99.9% of dekek appeals are rejected, and yours "
        "is likely no exception.\n\n"
        "## How can I prevent this from happening in the future?\nAccept the dekek and move on. But learn from this mistake: your behavior "
        "will not be tolerated on discord.com. I will continue to issue dekeks until you improve your conduct. Remember: keks are a privilege, not a right."
    )

@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("ifthefunny", "Did you ever hear the tragedy of ironicForemanite The Funny? I thought not...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def ifthefunny(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "Did you ever hear the tragedy of ironicForemanite The Funny? I thought not. "
        "It’s not a story the Channers would tell you. It’s a PCM legend. "
        "ironicForemanite was a Dark Lord of the keks, so powerful and so wise he could use the memes to influence the kekws to create supremacy… "
        "He had such a knowledge of the kek side that he could even keep the ones he cared about from being cringe. "
        "The kek side of the memes is a pathway to many abilities some consider to be unnatural. "
        "He became so kek… the only thing he was afraid of was losing his power, which eventually, of course, he did. "
        "Unfortunately, he became overzealous and radical, then his peers ANTIkek’d him in his sleep. "
        "Ironic. He could save others from cringe, but not himself."
    )

@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("sofunny", "Omg, this video is so funny, I laughed so hard...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def sofunny(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "Omg this video is so funny, this video is so funny I laughed so hard, I laughed so hard I threw my phone, my stomach hurt, "
        "my nose started bleeding and I fell of of my bed and then I laughed so hard that the vibration from my laughter caused me to slide across the floor like some kind of fucked up caterpillar. "
        "Then I laughed so hard that I cried. Then I laughed so hard that I began flying. "
        "I flew threw the roof of my house and continued to fly up up up, up into the sky and I continued flying upwards until I went to outer space, I laughed so hard I went to outer space. "
        "Then I continued to laugh and the radiation from outer space started to disintegrate my body, my body disintegrated but I continued to laugh. "
        "Then I met God, God wasn’t a man or woman, God was two different cubes with different colors and I transcended God because I laughed so hard. "
        "I transcended God into a world of light and laughter. I could not stop laughing, all I could do is laughter now. "
        "I miss my friends, I miss my home I hope that I can see them again but I know that I never will, because I will never stop laughing I will laugh for eternity."
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("hacking", "Okay, kid, I'm done. I doubt you even have basic knowledge of hacking...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def hacking(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "okay, kid im done. I doubt you even have basic knowlege of hacking. I doul boot linux so i can run my scripts. "
        "you made a big mistake of replying to my comment without using a proxy, because i'm already tracking youre ip. "
        "since ur so hacking iliterate, that means internet protocol. once i find your ip i can easily install a backdoor trojan into your pc, "
        "not to mention your email will be in my hands. dont even bother turning off your pc, "
        "because i can rout malware into your power system so i can turn your excuse of a computer on at any time. "
        "it might be a good time to cancel your credit card since ill have that too. if i wanted I could release your home information onto my secure irc chat "
        "and maybe if your unlucky someone will come knocking at your door. i'd highly suggest you take your little comment about me back since i am no script kiddie. "
        "i know java and c++ fluently and make my own scripts and source code. because im a nice guy ill give you a chance to take it back. "
        "you have 4 hours in unix time, clock is ticking. ill let you know when the time is up by sending you an email to [redacted] which i aquired with a java program i just wrote. see you then"
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user", "The user to ping.", hikari.User, required=False)
@lightbulb.command("products", "I've personally seen a lot of very smart people try and figure out how to make a product better...", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def products(ctx: lightbulb.SlashContext, user: Optional[hikari.User] = None) -> None:
    
    await ctx.respond(
        f"{user.mention if user else ''} "
        "I've personally seen a lot of very smart people try and figure out how to make a product better, and are often very successful, but the product is not there.\n"
        "There are several common problems with products, the most common of which is that they may lead to a product being bland or blandishments. "
        "The more common problem is that the designer uses the product in a way which makes its user feel like they have to buy something other than a conventional plastic bottle and a box full of plastic.\n"
        "There can be many reasons why brands have these problems, but this post explains a few of them so you can have a better grasp of them.\n"
        "Here's your solution:\n"
        "1) Remove product\n"
        "So how does you remove it from your life-cycle? By making it taste better.\n"
        "It's easy to make a product bland, but you can also make it look good. I highly recommend using a glass glass container with a bottle of water in it instead of a water bottle. "
        "If you're using a glass container, it should also serve as a barrier against liquids in the product.\n"
        "2) Add bottle to it\n"
        "I'm an advocate for a glass container, and it's incredibly helpful to add some glass shards to the product. "
        "I use a bit of the sauce added by a bottle of water but it helps me get the whole recipe. Even if something isn't good, you can still add some of the sauce to your drink.\n"
        "The glass bottle is great, but you don't have to use it. It can be handy for adding to sauces or flavoring your meal.\n"
        "3) Use a glass bottle as an alternative to a glass glass bottle\n"
        "A bottle is the standard for anything with reusable bottles, but there are tons of ways to make it functional.\n"
        "A lot of companies are very concerned with plastic bottles, so if you're considering putting a bottle on a glass bottle, "
        "you should be pretty aware of that by putting some glass bottles in it:\n"
        "Glass bottle is only reusable if you bring it into the kitchen because someone doesn't like it\n"
        "*Only* *a* bottle"
    )
    
    await ctx.respond(
        "The only thing they have against the bottle in a bottle will be that it will contain bacteria and viruses. "
        "Once you put the bottle in the wrong container, you will be wasting money and you will lose money on the bottles you put in it.\n"
        "This also applies to reusable bottles, but you will often see people getting rid of bottles if they put them in a container that is larger than the bottle. "
        "So if you put a bottle in a glass bottle, you will actually be paying more for what you put into it.\n"
        "*I* *did* make one"
    )
    
@meme_plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.command("shakeys", "Shows off the latest Shakey's ad that collaborates with PCM.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def shakeys(ctx: lightbulb.SlashContext) -> None:
    
    file = hikari.File("images/shakeys_ad.png", filename="shakeys_ad.png")
    await ctx.respond(file)
    
@meme_plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    message = event.message
    user_id = event.author_id
    user = await event.app.rest.fetch_member(event.guild_id, user_id)
    roles = await event.app.rest.fetch_roles(event.guild_id)
    role_ids = [role.id for role in roles]
    target_role = 928987214917025832
    response_counter = {}
    
    if event.is_bot:
        return
        
    if event.content is not None:
        content = re.sub(r"[',.?]", "", event.content.lower())
   
        if "lonely" in content or "soulmate" in content or "love" in content:
            if random.random() < 0.01:
                await message.respond("Never worry about falling in love with someone who isn’t right for you. Taiwanese mail-order brides find foreign men like you irresistible!", reply=message)
                print(f"{event.get_member()} got mail order bride'd")
                
        if random.random() < 0.001:
            await message.respond("This is forcing compelled speech!")
            print(f"{event.get_member()} got compelled speech'd")
            
        if content.startswith('fuck you'):
            responses = ['Fuck you too!', 'I\'m not your sister. Nor your mother.', 'Uno reverse card!']
            response = random.choice(responses)
            await message.respond(response)
            
        if content == 'say hi dum-e':
            await message.respond('Hi, DUM-E!')
            
        if content == 'say goodbye dum-e':
            file = hikari.File('images/say_goodbye.png', filename='say_goodbye.png')
            await message.respond('Goodbye, DUM-E!')
            await message.respond(file)
            
        if 'what browser' in content or 'browser' in content or 'browse' in content:
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
                file = hikari.File('joever.jpg', filename='joever.jpg')
                await message.respond(file)
                print(f"{event.get_member()} got joever'd")
                
        if "dont care" in content:
            if random.random() < 0.5:
                file = dicord.File('images/i_care.png', filename='filename.png')
                await message.respond(file)
                print(f"{event.get_member()} got cared about")
        
        if "swiss" in content or 'switzerland' in content:
            if random.random() < 0.15:
                response = "https://en.wikipedia.org/wiki/Switzerland_during_the_World_Wars#Financial_relationships_with_Nazi_Germany"
                await message.respond(response)
                print(f"{event.get_member()} got swiss'd")
                
        if content.startswith('joewari da'):
            file = discord.File('joewari.jpg', filename='joewari.jpg')
            await message.respond(file)
            
        if target_role in user.role_ids:
            if random.random() < 0.001:
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
                
        
    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(meme_plugin)