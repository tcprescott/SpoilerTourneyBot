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

import urllib.parse

import spoilerbot.config as cfg
config = cfg.get_config()

async def qualifier_cmd(ctx, arg1, logger, loop):
    tz = timezone('US/Eastern')
    logger.info('Qualifier Requested - {servername} - {channelname} - {player} - {seednum}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = arg1,
    ))
    # if helpers.check_cmd_filter(ctx.guild.id,ctx.channel.name,'qualifier',config):
    #     return

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
        hash=qualifier_seed['hash']
    )

    spoilerlog = qualifier_seed['spoilerlog']
    verificationkey = await generate_verification_key(loop)


    permalink = await seed.url()
    fscode = ' | '.join(await seed.code())
    timestamp = str(datetime.now(tz).replace(microsecond=0))

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
        'This is the verification key that is required to be in the first four characters of the filename of your run:\n`{verificationkey}`\n\n' \
        'Seed number: {seednum}\n' \
        'Timestamp: {timestamp}\n' \
        'Permalink: {permalink}\n' \
        'File select code: [{fscode}]\n' \
        'Spoiler log: {spoilerlog}\n\n' \
        'Submit your run here once completed: <{submiturl}>\n\n' \
        'You have 15 minutes from the receipt of this message to start your run!\n' \
        '**Please DM an admin immediately if this was requested in error**, otherwise it may be counted as a forfeit (slowest time of all runners of the seed plus 30 minutes).\n\n' \
        'Good luck <:mudora:536293302689857567>'.format(
            verificationkey=verificationkey,
            seednum=seednum,
            timestamp=timestamp,
            fscode=fscode,
            permalink=permalink,
            spoilerlog=spoilerlog,
            submiturl=config['qualifier_form_prefill'].format(
                discordtag=urllib.parse.quote_plus(ctx.author.name + '#' + ctx.author.discriminator),
                verificationkey=verificationkey,
                seednum=seednum
            )
        )
    )

    modlogchannel = ctx.guild.get_channel(config['log_channel'][ctx.guild.id])
    msg = 'Qualifier request for {player}:\n\n' \
    'Verification Key: {verificationkey}\n' \
    'Seed Number: {seednum}\n' \
    'Timestamp: {timestamp}'.format(
        player = ctx.author.name + '#' + ctx.author.discriminator,
        verificationkey=verificationkey,
        seednum=seednum,
        timestamp=timestamp,
    )
    await modlogchannel.send(msg)

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
            verificationkey,
            "=INDEX('Submitted Runs'!E:G,MATCH(INDIRECT(\"R[0]C[-1]\", false),'Submitted Runs'!C:C,0), 1)*3600+INDEX('Submitted Runs'!E:G,MATCH(INDIRECT(\"R[0]C[-1]\", false),'Submitted Runs'!C:C,0), 2)*60+INDEX('Submitted Runs'!E:G,MATCH(INDIRECT(\"R[0]C[-1]\", false),'Submitted Runs'!C:C,0), 3)",
            "=INDEX('Submitted Runs'!H:H,MATCH(INDIRECT(\"R[0]C[-2]\", false),'Submitted Runs'!C:C,0), 1)",
            "=INDEX('Submitted Runs'!I:I,MATCH(INDIRECT(\"R[0]C[-3]\", false),'Submitted Runs'!C:C,0), 1)",
            "=INDEX('Submitted Runs'!J:J,MATCH(INDIRECT(\"R[0]C[-4]\", false),'Submitted Runs'!C:C,0), 1)"
        ],
        value_input_option='USER_ENTERED'
    )

    logger.info('Qualifier Recorded in Gsheet - {servername} - {channelname} - {player} - {seednum} - {verificationkey}'.format(
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        seednum = seednum,
        verificationkey = verificationkey
    ))

    await ctx.message.add_reaction('👍')

async def generate_verification_key(loop):
    for a in range(10):
        key = ''.join(random.choices(string.ascii_uppercase, k=4))
        sbdb = db.SpoilerBotDatabase(loop)
        await sbdb.connect()
        flattened=[]
        if await sbdb.get_verification_key(key) == None:
            await sbdb.record_verification_key(key)
            await sbdb.close()
            return key
    sbdb.close()
    raise RuntimeError('Verification key generation failed.')

async def gen_qualifier_seed(ctx, loop, seednum=None):
    try:
        seednum=int(seednum)
    except ValueError:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that is not a number.'.format(
            author=ctx.author.mention
        ))
        return

    spdb = db.SpoilerBotDatabase(loop)
    await spdb.connect()
    qualifier_seed = await spdb.get_qualifier_seed(seednum)

    if not qualifier_seed == None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that seed already exists.  It would need to be manually purged from the database first.'.format(
            author=ctx.author.mention
        ))
        await spdb.close()
        return
    
    seed = await pyz3r_asyncio.create_seed(
        randomizer='item', # optional, defaults to item
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        settings={
            "difficulty": "normal",
            "enemizer": False,
            "logic": "NoGlitches",
            "mode": "open",
            "tournament": True,
            "variation": "none",
            "weapons": "randomized",
            "lang": "en"
        }
    )

    rdb = db.RandomizerDatabase(loop)
    await rdb.connect()
    spoiler_log = await rdb.get_seed_spoiler(seed.hash)
    await rdb.close()

    spoiler_log_url = await helpers.write_json_to_disk(spoiler_log['spoiler'], seed)

    await spdb.insert_qualifier_seed(
        id=seednum,
        hash=seed.hash,
        spoilerlog=spoiler_log_url,
    )

    modlogchannel = ctx.guild.get_channel(config['log_channel'][ctx.guild.id])
    msg = '-----------------------------------------\n' \
    'Qualifier Seed #{seednum}:\n\n' \
    'Permalink: {permalink}\n' \
    'Code: [{code}]\n' \
    'Spoiler log: {spoilerlog}'.format(
        seednum=seednum,
        permalink=await seed.url(),
        spoilerlog=spoiler_log_url,
        code=' | '.join(await seed.code())
    )
    await modlogchannel.send(msg)
    await ctx.send(msg)

    await spdb.close()

    await ctx.message.add_reaction('👍')