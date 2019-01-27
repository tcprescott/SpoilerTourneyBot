import asyncio
import sys
from discord.ext import commands
import discord

import bottom

import logging
import logging.handlers as handlers

import math

import gspread_asyncio
import string
import random
from datetime import datetime
from pytz import timezone
from oauth2client.service_account import ServiceAccountCredentials

import yaml

try:
    with open("cfg/config.yaml") as configfile:
        try:
            config = yaml.load(configfile)
        except yaml.YAMLError as e:
            print(e)
            sys.exit(1)
except FileNotFoundError:
    print('cfg/config.yaml does not exist!')
    sys.exit(1)

discordbot = commands.Bot(
    command_prefix=config['cmd_prefix'],
)

ircbot = bottom.Client(host='irc.speedrunslive.com', port=6667, ssl=False)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = handlers.TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when='D', interval=1, backupCount=30)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

tz = timezone('EST')

@discordbot.event
async def on_ready():
    try:
        print(discordbot.user.name)
        print(discordbot.user.id)

    except Exception as e:
        print(e)

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
    await asyncio.sleep(30)
    ircbot.send('PRIVMSG', target=arg2, message='This race\'s spoiler log: https://example.com/spoiler/something.txt')
    await countdown_timer(900, arg2)
    ircbot.send('PRIVMSG', target=arg2, message='.quit')


@discordbot.command()
async def qualifier(ctx, arg1=''):
    # is this a channel we want to be using?
    logger.info('Qualifier Requested - {servername} - {channelname} - {player} - {seednum}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = arg1,
    ))
    if check_cmd_filter(ctx.guild.id,ctx.channel.name,'qualifier'):
        return

    try:
        seednum=int(arg1)
    except ValueError:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that is not a number.'.format(
            author=ctx.author.mention
        ))
        return

    logger.info('Qualifier gsheet init - {servername} - {channelname} - {player} - {seednum}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
    ))
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(config['gsheet_id'])
    wks = await wb.get_worksheet(0)
    wks2 = await wb.get_worksheet(1)

    logger.info('Qualifier gsheet init finished - {servername} - {channelname} - {player} - {seednum}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
    ))

    # does seed exist?  If not :thumbsdown: the message and let the user know.
    seed = await wks2.row_values(seednum)
    if seed[0] == '' or arg1==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that seed does not exist.'.format(
            author=ctx.author.mention
        ))
        return

    verificationkey = ''.join(random.choices(string.ascii_uppercase, k=4))
    permalink = seed[1]
    fscode = seed[2]
    timestamp = str(datetime.now(tz))

    logger.info('Qualifier Generated - {servername} - {channelname} - {player} - {seednum} - {verificationkey}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
        verificationkey = verificationkey
    ))

    dm = ctx.author.dm_channel
    if dm == None:
        dm = await ctx.author.create_dm()

    await dm.send(
        'This is the verification key that is required to be in the filename of your run:\n`{verificationkey}`\n\n' \
        'Seed number: {seednum}\n' \
        'Timestamp: {timestamp}\n' \
        'File select code: [{fscode}]\n' \
        'Permalink: {permalink}\n\n' \
        'You have 15 minutes from the receipt of this message to start your run!\n' \
        '**Please DM an admin immediately if this was requested in error**, otherwise it may be counted as a DNF (slowest time plus 30 minutes).\n\n' \
        'Good luck <:mudora:536293302689857567>'.format(
            verificationkey=verificationkey,
            seednum=seednum,
            timestamp=timestamp,
            fscode=fscode,
            permalink=permalink
        )
    )

    logger.info('Qualifier DM Sent - {servername} - {channelname} - {player} - {seednum} - {verificationkey}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
        verificationkey = verificationkey
    ))

    await wks.append_row(
        [
            timestamp,
            str(ctx.author),
            seednum,
            verificationkey
        ]
    )

    logger.info('Qualifier Recorded in Gsheet - {servername} - {channelname} - {player} - {seednum} - {verificationkey}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
        verificationkey = verificationkey
    ))

    await ctx.message.add_reaction('👍')

@qualifier.error
async def qualifier_error(ctx, error):
    await ctx.message.add_reaction('👎')
    await ctx.send('{author}, there was a problem with your request.  Ping an admin if this condition persists.'.format(
        author=ctx.author.mention
    ))
    logger.error('Qualifier Error - {servername} - {channelname} - {player} - {error}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        error = error,
    ))

def check_cmd_filter(guildid, channelname, cmd):
    if not channelname in config['cmd_filters'][cmd][guildid]:
        return True
    else:
        return False

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json',
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

async def countdown_timer(duration_in_seconds, srl_channel):
    reminders = [900,600,300,120,60,30,10,9,8,7,6,5,4,3,2,1]
    start_time = loop.time()
    end_time = loop.time() + duration_in_seconds
    while True:
        # print(datetime.datetime.now())
        timeleft = math.ceil(start_time - loop.time() + duration_in_seconds)
        # print(timeleft)
        if timeleft in reminders:
            minutes = math.floor(timeleft/60)
            seconds = math.ceil(timeleft % 60)
            if minutes == 0:
                msg = '{seconds} second(s) are remaining!'.format(
                    seconds=seconds
                )
            else:
                msg = '{minutes} minute(s), {seconds} second(s) are remaining!'.format(
                    minutes=minutes,
                    seconds=seconds
                )
            ircbot.send('PRIVMSG', target=srl_channel, message=msg)
            reminders.remove(timeleft)
        if (loop.time() + 1) >= end_time:
            break
        await asyncio.sleep(.5)


@ircbot.on('CLIENT_CONNECT')
async def connect(**kwargs):
    ircbot.send('NICK', nick=config['srl_irc_nickname'])
    ircbot.send('USER', user=config['srl_irc_nickname'],
             realname='https://github.com/numberoverzero/bottom')

    # Don't try to join channels until the server has
    # sent the MOTD, or signaled that there's no MOTD.
    done, pending = await asyncio.wait(
        [ircbot.wait("RPL_ENDOFMOTD"),
         ircbot.wait("ERR_NOMOTD")],
        loop=loop,
        return_when=asyncio.FIRST_COMPLETED
    )

    #raw command because I can't seem to get this to work with send()
    ircbot.send('PRIVMSG', target='NICKSERV', message='identify ' + config['srl_irc_password'])

    # Cancel whichever waiter's event didn't come in.
    for future in pending:
        future.cancel()

    ircbot.send('JOIN', channel='#speedrunslive')

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
    print(message)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(discordbot.start(config['discord_token']))
    loop.create_task(ircbot.connect())
    # loop.create_task(countdown_timer(900))
    loop.run_forever()
