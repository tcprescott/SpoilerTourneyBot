import asyncio

from discord.ext import commands
import discord
import bottom

import logging
import logging.handlers as handlers

import spoilerbot.config as cfg
import spoilerbot.qualifier as qual
import spoilerbot.bracket as bracket
import spoilerbot.helpers as helpers
import spoilerbot.srl as srl
import spoilerbot.sg as sg

import pyz3r_asyncio

import re




config = cfg.get_config()

# discord bot using discord.py rewrite
discordbot = commands.Bot(
    command_prefix=config['cmd_prefix'],
)

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
        logger.info('discord - {username} - {userid}'.format(
            username=discordbot.user.name,
            userid=discordbot.user.id
            ))

    except Exception as e:
        print(e)

# make sure that admins can only do this in the public version of the bot!
@discordbot.command(hidden=True)
async def srlcmd(ctx, op, channel=None, target=None, message=None):
    ircbot.send(op, channel=channel, target=target, message=message)

#restreamrace command
@discordbot.command(
    help='Begin a race to be restreamed.  Should be ran by a restreamer or broadcast operator.\n\nsg_race_id should be the ID of the race on the SG schedule\nsrl_channel should be the full channel name of the SRL race (e.g. #srl-abc12)',
    brief='Begin a restreamed race'
)
async def bracketrace(ctx, sg_race_id=None, srl_channel=None):
    await bracket.bracketrace(ctx=ctx, arg1=sg_race_id, arg2=srl_channel, loop=loop, ircbot=ircbot)

@discordbot.command(
    help='Begin a race to be restreamed.  Should be ran by a restreamer or broadcast operator.\n\nsg_race_id should be the ID of the race on the SG schedule\nsrl_channel should be the full channel name of the SRL race (e.g. #srl-abc12)',
    brief='Begin a restreamed race',
    hidden=True
)
async def nosrlrace(ctx, sg_race_id=None):
    await bracket.bracketrace(ctx=ctx, arg1=sg_race_id, loop=loop, ircbot=ircbot, nosrl=True)

@discordbot.command(
    help='Begin a practice skirmish.\n\ntitle should title of the match in quotes\nsrl_channel should be the full channel name of the SRL race (e.g. #srl-abc12)',
    brief='Begin a practice skirmish',
)
async def skirmish(ctx, title=None, srl_channel=None):
    await bracket.bracketrace(ctx=ctx, arg1=title, arg2=srl_channel, loop=loop, ircbot=ircbot, skirmish=True)

@discordbot.command(
    help='Generates a seed and sends the requestor a DM w/ the spoiler log, permalink, and code.  Intended for practice.',
    brief='Generate a practice seed.'
)
async def practice(ctx):
    await bracket.practice(ctx=ctx, loop=loop)

@discordbot.command(
    help='Sends you a DM with bracket information',
    brief='Re-request details for a race.'
)
async def resend(ctx, channel=None):
    await bracket.resend(ctx, loop, ircbot, channel)

@discordbot.command(
    hidden=True
)
async def pizza(ctx):
    await ctx.send('🍕')

@discordbot.command(
    hidden=True
)
async def beer(ctx):
    await ctx.send('🍺')

@discordbot.command(
    hidden=True
)
async def mudora(ctx):
    await ctx.send('<:mudora:536293302689857567>')

#qualifier command, this has been condensed and relocated to the spoilerbot/qualifier.py
@discordbot.command(
    help='Request a verification key to begin a qualifier run.\n\n*seednum* is the number of the seed you wish to play.',
    brief='Request a qualifier verification key'
)
async def qualifier(ctx, seednum=''):
    await qual.qualifier_cmd(
        ctx=ctx,
        arg1=seednum,
        loop=loop,
        logger=logger
    )
    
#handle errors, use our standard error handler to simplify things
@qualifier.error
async def qualifier_error(ctx, error):
    await helpers.error_handle(ctx, error, logger, 'qualifier')


@ircbot.on('CLIENT_CONNECT')
async def connect(**kwargs):
    await srl.connect(ircbot, config, loop)

# this is a pretty low level library, so yea
@ircbot.on('PING')
def keepalive(message, **kwargs):
    ircbot.send('PONG', message=message)


# log messages, respond to .spoilerstart and .spoilerseed commands
@ircbot.on('PRIVMSG')
async def message(nick, target, message, **kwargs):
    await srl.write_chat_log(
        channel=target,
        author=nick,
        message=message
    )
    if message == '.spoilerstart':
        await srl.spoilerstart(
            channel=target,
            author=nick,
            ircbot=ircbot,
            discordbot=discordbot,
            loop=loop
        )
    elif message == '.spoilerseed':
        await srl.spoilerseed(
            channel=target,
            author=nick,
            ircbot=ircbot,
            loop=loop
        )

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
