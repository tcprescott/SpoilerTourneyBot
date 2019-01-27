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
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = handlers.TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when='D', interval=1, backupCount=30)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#do some stuff when we connect to discord
@discordbot.event
async def on_ready():
    try:
        print(discordbot.user.name)
        print(discordbot.user.id)

    except Exception as e:
        print(e)

#restreamrace command
@discordbot.command()
async def restreamrace(ctx, arg1=None, arg2=None):
    if arg1==None or arg2==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, you need both the race id and srl room specified.'.format(
            author=ctx.author.mention
        ))
        return
    # ircbot.join(arg2)
    await asyncio.sleep(10)
    ircbot.send('PRIVMSG', target=arg2, message='.setgoal BOT TESTING - Please do not join!')
    ircbot.send('PRIVMSG', target=arg2, message='.join')
    await asyncio.sleep(10) #placeholder for coroutine that will check for ready state
    ircbot.send('PRIVMSG', target=arg2, message='This race\'s spoiler log: https://example.com/spoiler/something.txt')
    await helpers.countdown_timer(900, arg2, loop=loop, ircbot=ircbot)
    ircbot.send('PRIVMSG', target=arg2, message='.quit')


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
    loop.create_task(ircbot.connect())
    # loop.create_task(countdown_timer(900))
    loop.run_forever()
