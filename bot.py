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

import re

config = cfg.get_config()

# discord bot using discord.py rewrite
discordbot = commands.Bot(
    command_prefix=config['cmd_prefix'],
)

# irc bot using bottom, an very low level async irc client
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

@discordbot.command()
async def test(ctx, arg1=None):
    pass

# make sure that admins can only do this in the public version of the bot!
@discordbot.command()
async def srl_chat(ctx, arg1, arg2):
    ircbot.send('JOIN', channel=arg1)
    ircbot.send('PRIVMSG', target=arg1, message=arg2)
    ircbot.send('PART', channel=arg1)

async def is_open(race):
    try:
        if race['state'] == 1:
            return True
        else:
            return False
    except KeyError:
        return False

#restreamrace command
@discordbot.command()
async def restreamrace(ctx, arg1=None, arg2=None):
    if arg1==None or arg2==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, you need both the race id and srl room specified.'.format(
            author=ctx.author.mention
        ))
        return
    if re.search('^#srl-[a-z0-9]{5}$',arg2):
        raceid = arg2.partition('-')[-1]
        channel = arg2
        race = await srl.get_race(raceid)
    else:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that doesn\'t look like an SRL race.'.format(
            author=ctx.author.mention
        ))
        return
    print(await is_open(race))
    # call SRL gatekeeper coroutine
    # await srl.gatekeeper(
    #     ircbot=ircbot,
    #     channel=channel,
    #     spoilerlogurl=''
    # )


#qualifier command, this has been condensed and relocated to the spoilerbot/qualifier.py
@discordbot.command()
async def qualifier(ctx, arg1=''):
    await qual.qualifier_cmd(
        ctx=ctx,
        arg1=arg1,
        config=config,
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


# for testing, this ircbot will actually only be sending messages
# @ircbot.on('PRIVMSG')
# def message(nick, target, message, **kwargs):
#     """ Echo all messages """

#     # Don't echo ourselves
#     if nick == NICK:
#         return
#     # Respond directly to direct messages
#     if target == NICK:
#         print(message)
#     # Channel message
#     else:
#         print(message)

@ircbot.on('NOTICE')
def notice(message, **kwargs):
    if message=='Password accepted - you are now recognized.':
        logger.info('irc - successfully auth\'d with nickserv')

#create the main loop and all of tha that fun stuff
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(discordbot.start(config['discord_token']))
    # loop.create_task(ircbot.connect())
    loop.run_forever()
