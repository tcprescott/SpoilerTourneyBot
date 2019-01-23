import asyncio
import sys
from discord.ext import commands

import gspread
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
    command_prefix='$',

)

tz = timezone('EST')

@bot.event
async def on_ready():
    try:
        print(bot.user.name)
        print(bot.user.id)

    except Exception as e:
        print(e)


@bot.command()
async def qualifier(ctx, arg1):
    try:
        seednum=int(arg1)
    except ValueError:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that is not a number.'.format(
            author=ctx.author.mention
        ))
        return

    scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json', scope)
    gc = gspread.authorize(credentials)
    wb = gc.open_by_key(config['gsheet_id'])
    wks = wb.get_worksheet(0)
    wks2 = wb.get_worksheet(1)

    if wks2.cell(seednum, 1).value == '':
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that seed does not exist.'.format(
            author=ctx.author.mention
        ))
        return

    verificationkey = ''.join(random.choices(string.ascii_uppercase, k=4))
    permalink = wks2.cell(seednum, 2).value
    fscode = wks2.cell(seednum, 3).value

    dm = ctx.author.dm_channel
    if dm == None:
        dm = await ctx.author.create_dm()

    await dm.send('This is the verification key that is required to be in the filename of your run:\n`{verificationkey}`\n\nSeed number: {seednum}\nFile select code: [{fscode}]\nPermalink: {permalink}\n\nYou have 15 minutes from the receipt of this DM to start you run! Good luck <:mudora:536293302689857567>'.format(
        verificationkey=verificationkey,
        seednum=seednum,
        fscode=fscode,
        permalink=permalink
    ))

    wks.append_row(
        [
            str(datetime.now(tz)),
            str(ctx.author),
            seednum,
            verificationkey
        ]
    )

    await ctx.message.add_reaction('👍')



bot.run(config['discord_token'])