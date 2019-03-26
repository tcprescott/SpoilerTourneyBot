# the thing that makes it all work
import asyncio

# bot libraries
from discord.ext import commands
import discord
import bottom

# logging libraries
import logging
import logging.handlers as handlers

# spoilerbot libraries
import spoilerbot.config as cfg
import spoilerbot.qualifier as qual
import spoilerbot.bracket as bracket
import spoilerbot.helpers as helpers
import spoilerbot.srl as srl
import spoilerbot.sg as sg

# our special asyncio version of pyz3r
import pyz3r_asyncio


config = cfg.get_config()

# discord bot using discord.py rewrite
discordbot = commands.Bot(
    command_prefix=config['cmd_prefix'],
)
discordbot.load_extension("spoilerbot.verifiers")
discordbot.load_extension("spoilerbot.eggs")
discordbot.load_extension("spoilerbot.admin")

# irc bot using bottom, an very, very low level async irc client
ircbot = bottom.Client(
    host='irc.speedrunslive.com',
    port=6667,
    ssl=False
)

#setup logging configuration
logger = logging.getLogger('spoilerbot')
logger.setLevel(logging.INFO)
handler = handlers.TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when='D', interval=1, backupCount=30)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#do some stuff when we connect to discord
@discordbot.event
async def on_ready():
    try:
        await discordbot.change_presence(activity=discord.Game(name='$help for available cmds'))
        logger.info('discord - {username} - {userid}'.format(
            username=discordbot.user.name,
            userid=discordbot.user.id
            ))

    except Exception as e:
        print(e)

@discordbot.event
async def on_message(message):
    if discordbot.user in message.mentions:
        await message.add_reaction(':sombreroguy:536296419699720222')
        
    await discordbot.process_commands(message)

#automatically adds/removes roles based on the voice channels that are entered/exited
#this should be its own function
@discordbot.event
async def on_voice_state_update(member, before, after):
    if not after.channel == None:
        if after.channel.name in config['voice_channel_role'][member.guild.id]:
            role = discord.utils.get(member.guild.roles, name=config['voice_channel_role'][member.guild.id][after.channel.name]['role_name'])
            await member.add_roles(role)
    if not before.channel == None:
        if before.channel.name in config['voice_channel_role'][member.guild.id]:
            role = discord.utils.get(member.guild.roles, name=config['voice_channel_role'][member.guild.id][before.channel.name]['role_name'])
            await member.remove_roles(role)
    return

#Allow admins to issue arbitrary IRC commands to the IRC bot (useful for fixing something that broke)
@discordbot.command()
@commands.has_any_role('admin')
async def srlcmd(ctx, op, channel=None, target=None, message=None):
    await ctx.message.add_reaction('⌚')
    ircbot.send(op, channel=channel, target=target, message=message)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)
    await ctx.message.add_reaction('👍')

#the bracketrace command!
@discordbot.command(
    help='Begin a race to be restreamed.  Should be ran by a restreamer or broadcast operator.\n\nsg_race_id should be the ID of the race on the SG schedule\nsrl_channel should be the full channel name of the SRL race (e.g. #srl-abc12)',
    brief='Begin a restreamed race'
)
@commands.has_any_role('admin','moderator','bracket','sg-crew')
@helpers.has_any_channel('brackets','speedgaming','restreamer','bot-testing')
async def bracketrace(ctx, sg_race_id=None, srl_channel=None):
    await ctx.message.add_reaction('⌚')
    await bracket.bracketrace(ctx=ctx, arg1=sg_race_id, arg2=srl_channel, loop=loop, ircbot=ircbot)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

# This will only be available to admins/moderators as needed (SRL and/or IRC bot is broken for some reason and we need to manually operate the race).
@discordbot.command(
    help='Begin a race to be restreamed, without SRL functionality.  Should only be ran if SRL or IRC Bot is broken.\n\nsg_race_id should be the ID of the race on the SG schedule',
    brief='Begin a restreamed race',
)
@commands.has_any_role('admin','moderator')
async def nosrlrace(ctx, sg_race_id=None):
    await ctx.message.add_reaction('⌚')
    await bracket.bracketrace(ctx=ctx, arg1=sg_race_id, loop=loop, ircbot=ircbot, nosrl=True)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

# practice skirmishes, basically sets everything up like normal except don't use the SG schedule
@discordbot.command(
    help='Begin a practice skirmish.\n\ntitle should title of the match in quotes\nsrl_channel should be the full channel name of the SRL race (e.g. #srl-abc12)',
    brief='Begin a practice skirmish',
)
@helpers.has_any_channel('practice_racing','speedgaming','bot-console','bot-testing')
async def skirmish(ctx, title=None, srl_channel=None):
    await ctx.message.add_reaction('⌚')
    await bracket.bracketrace(ctx=ctx, arg1=title, arg2=srl_channel, loop=loop, ircbot=ircbot, skirmish=True)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

# generate practice seeds with tournament spoiler logs
@discordbot.command(
    help='Generates a seed and sends the requestor a DM w/ the spoiler log, permalink, and code.  Intended for practice.',
    brief='Generate a practice seed.'
)
async def practice(ctx):
    await ctx.message.add_reaction('⌚')
    await bracket.practice(ctx=ctx, loop=loop)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

# lets commentators, trackers, sg-crew, restreamers, or players get sent a copy of the seed and code (not spoiler log)
@discordbot.command(
    help='Sends you a DM with bracket information',
    brief='Re-request details for a race.'
)
@commands.has_any_role('admin','commentator','tracker','sg-crew','restreamer','qualifier','bracket')
async def resend(ctx, channel=None):
    await ctx.message.add_reaction('⌚')
    await bracket.resend(ctx, loop, ircbot, channel)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

#qualifier command, this has been condensed and relocated to the spoilerbot/qualifier.py
#we also make sure that only admins, mods, and qualifier players can run this command, and that it is run in the qualifier channel
@discordbot.command(
    help='Request a verification key to begin a qualifier run.\n\n*seednum* is the number of the seed you wish to play.',
    brief='Request a qualifier verification key'
)
@commands.has_any_role('admin','moderator')
@helpers.has_any_channel('bot-testing')
async def qualifier(ctx, seednum=''):
    await ctx.message.add_reaction('⌚')
    await qual.qualifier_cmd(
        ctx=ctx,
        arg1=seednum,
        loop=loop,
        logger=logger
    )
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

#genqualifier
#allow an admin to generate a qualifier seed and store it in the database
@discordbot.command(
    help='Generate a qualifier seeed for others to request.  Only admins should run this.',
    brief='Generate a qualifier seeed for others to request.'
)
@commands.has_any_role('admin')
async def genqualifier(ctx, seednum=''):
    await ctx.message.add_reaction('⌚')
    await qual.gen_qualifier_seed(
        ctx=ctx,
        seednum=seednum,
        loop=loop
    )
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

import spoilerbot.database as db
from datetime import datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta

@discordbot.command(
    help='Get current deadline.\n'
        'Timezone is the timezone name found in the TZ database.\n'
        'See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones',
    brief='Get current deadline.'
)
async def deadline(ctx, timezone='America/New_York'):
    await ctx.message.add_reaction('⌚')

    sbdb = db.SpoilerBotDatabase(loop)
    await sbdb.connect()
    deadline = await sbdb.get_current_deadline()

    if deadline == None:
        await ctx.send('No deadline current exists.')

        await ctx.message.add_reaction('👎')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)

    now = datetime.utcnow().replace(tzinfo=tz.tzutc())
    end = deadline['end'].replace(tzinfo=tz.tzutc())
    diff = relativedelta(end, now)

    await ctx.send(deadline['message'].format(
        time=end.astimezone(tz.gettz(timezone)).strftime('%b %d %Y at %I:%M:%S %p %Z'),
        remain='{days} days, {hours} hours, {minutes} minutes, and {seconds} seconds to go'.format(
            days=diff.days,
            hours=diff.hours,
            minutes=diff.minutes,
            seconds=diff.seconds,
        ),
    ))

    await ctx.message.add_reaction('👍')
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

#handle errors, using a common handler
#also handles CheckFailures, in this case it'll react with a prohibitory symbol
@discordbot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.message.add_reaction('🚫')
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(error)
        await ctx.message.add_reaction('👎')
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.errors.CommandOnCooldown):
        pass
    else:
        await helpers.error_handle(ctx, error, logger)
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

#Bot should only respond to DMs for the practice command.  Other commands should be ignored.
@discordbot.check
async def globally_block_dms(ctx):
    if ctx.guild is None and not ctx.invoked_with in ['practice']:
        return False
    else:
        return True

# Connects the IRC Bot!
@ircbot.on('CLIENT_CONNECT')
async def connect(**kwargs):
    await srl.connect(ircbot, config, loop)

# respond to IRC PINGs, so we can stay connected to SRL
# this is a pretty low level library, so yea
@ircbot.on('PING')
def keepalive(message, **kwargs):
    ircbot.send('PONG', message=message)


# log messages, respond to .spoilerstart and .spoilerseed commands
@ircbot.on('PRIVMSG')
async def message(nick, target, message, **kwargs):
    try:
        await srl.write_chat_log(
            channel=target,
            author=nick,
            message=message
        )
    except:
        pass
    if message == '.spoilerstart':
        await srl.spoilerstart(
            channel=target,
            author=nick,
            ircbot=ircbot,
            discordbot=discordbot,
            loop=loop,
            immediate=True
        )
    elif message == '.spoilerseed':
        await srl.spoilerseed(
            channel=target,
            author=nick,
            ircbot=ircbot,
            loop=loop
        )
    elif message == '.multitwitch':
        await srl.post_multitwitch(
            channel=target,
            author=nick,
            ircbot=ircbot
        )

# log when NICKSERV accepts our auth request, mostly for troubleshooting failed starts of the SRL bot
@ircbot.on('NOTICE')
def notice(message, **kwargs):
    if message=='Password accepted - you are now recognized.':
        logger.info('irc - successfully auth\'d with nickserv')

#create the main loop and all of tha that fun stuff
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(discordbot.start(config['discord_token']))
    loop.create_task(ircbot.connect())
    loop.run_forever()
