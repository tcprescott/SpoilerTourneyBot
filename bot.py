import asyncio
import sys
from discord.ext import commands
import discord

import logging
import logging.handlers as handlers

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

bot = commands.Bot(
    command_prefix=config['cmd_prefix'],
)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = handlers.TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when='D', interval=1, backupCount=30)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

tz = timezone('EST')

@bot.event
async def on_ready():
    try:
        print(bot.user.name)
        print(bot.user.id)

    except Exception as e:
        print(e)

@bot.command()
async def qualifier(ctx, arg1=''):
    # is this a channel we want to be using?
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

    agc = await agcm.authorize()
    wb = await agc.open_by_key(config['gsheet_id'])
    wks = await wb.get_worksheet(0)
    wks2 = await wb.get_worksheet(1)

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
        'File select code: [{fscode}]\n' \
        'Permalink: {permalink}\n\n' \
        'You have 15 minutes from the receipt of this DM to start you run!\n' \
        '**Please DM an admin immediately if this was requested in error**, otherwise it may be counted as a DNF (slowest time plus 30 minutes).\n\n' \
        'Good luck <:mudora:536293302689857567>'.format(
            verificationkey=verificationkey,
            seednum=seednum,
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
            str(datetime.now(tz)),
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

# @qualifier.error
# async def info_error(ctx, error):
#     await ctx.message.add_reaction('👎')
#     await ctx.send('{author}, there was a problem with your request.  Ping an admin if this condition persists.'.format(
#         author=ctx.author.mention
#     ))
#     logger.error('Qualifier Error - {servername} - {channelname} - {player} - {error}'.format(
#         servername = ctx.guild.name,
#         channelname = ctx.channel.name,
#         player = ctx.author,
#         error = error,
#     ))

def check_cmd_filter(guildid, channelname, cmd):
    if not channelname in config['cmd_filters']['qualifier'][guildid]:
        return True
    else:
        return False  

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json',
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

bot.run(config['discord_token'])