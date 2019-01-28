import logging
import logging.handlers as handlers

import gspread_asyncio

import spoilerbot.helpers as helpers
import spoilerbot.database as db

import string
import random
from datetime import datetime
from pytz import timezone

import pyz3r_asyncio

import spoilerbot.config as cfg
config = cfg.get_config()

async def qualifier_cmd(ctx, arg1, logger, loop):
    tz = timezone('EST')
    logger.info('Qualifier Requested - {servername} - {channelname} - {player} - {seednum}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = arg1,
    ))
    if helpers.check_cmd_filter(ctx.guild.id,ctx.channel.name,'qualifier',config):
        return

    try:
        seednum=int(arg1)
    except ValueError:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that is not a number.'.format(
            author=ctx.author.mention
        ))
        return

    spdb = db.SpoilerBotDatabase(loop)
    await spdb.connect()
    qualifier_seed = await spdb.get_qualifier_seed(seednum)
    await spdb.close()

    if qualifier_seed == None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that seed does not exist.'.format(
            author=ctx.author.mention
        ))
        return

    seed = await pyz3r_asyncio.create_seed(
        randomizer='item',
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        append_json_extension=False,
        hash=qualifier_seed[0]
    )

    verificationkey = ''.join(random.choices(string.ascii_uppercase, k=4))
    permalink = await seed.url()
    fscode = ' | '.join(await seed.code())
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

    agcm = gspread_asyncio.AsyncioGspreadClientManager(helpers.get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(config['gsheet_id'])
    wks = await wb.get_worksheet(0)

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