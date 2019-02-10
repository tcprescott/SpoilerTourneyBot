import re
import spoilerbot.srl as srl
import spoilerbot.sg as sg
import spoilerbot.database as db
import spoilerbot.helpers as helpers

import random, string

import pyz3r_asyncio

import json

import aiofiles

import spoilerbot.config as cfg
config = cfg.get_config()

async def practice(ctx, loop):
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

    spoiler_log_url = await helpers.write_json_to_disk(spoiler_log[0], seed.hash)

    permalink = await seed.url()
    fscode = ' | '.join(await seed.code())

    dm = ctx.author.dm_channel
    if dm == None:
        dm = await ctx.author.create_dm()

    await dm.send(
        'Requested practice seed:\n\n'
        'Permalink: {permalink}\n' \
        'File select code: [{fscode}]\n' \
        'Spoiler log: {spoiler}\n\n' \
        'Good luck <:mudora:536293302689857567>'.format(
            fscode=fscode,
            permalink=permalink,
            spoiler=spoiler_log_url,
        )
    )

    await ctx.message.add_reaction('👍')

async def resend(ctx, loop, ircbot, channel):
    if channel==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, you need to specify a channel.'.format(
            author=ctx.author.mention
        ))
        return
    if re.search('^#srl-[a-z0-9]{5}$',channel):
        raceid = channel.partition('-')[-1]
    else:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that doesn\'t look like an SRL race room.'.format(
            author=ctx.author.mention
        ))
        return

    # figure out if this game has already been generated
    sbdb = db.SpoilerBotDatabase(loop)
    await sbdb.connect()
    racedata = await sbdb.get_bracket_race(raceid)
    await sbdb.close()
    
    if racedata == None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, `$bracketrace` has not yet been ran for this race.'.format(
            author=ctx.author.mention
        ))
        return

    ircbot.send('JOIN', channel=channel)

    hash = racedata[2]
    player1 = racedata[3]
    player2 = racedata[4]

    seed = await pyz3r_asyncio.create_seed(
        randomizer='item',
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        hash=hash
    )

    msg = await generate_bracket_dm(
        seed=seed,
        players=[player1, player2],
        channel=channel,
        )

    dm = ctx.author.dm_channel
    if dm == None:
        dm = await ctx.author.create_dm()
    await dm.send(msg)

    await ctx.message.add_reaction('👍')

async def bracketrace(ctx, loop, ircbot, arg1=None, arg2=None, nosrl=False, skirmish=False):
    if nosrl==False:
        if arg1==None:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, you need the SG episode id.'.format(
                author=ctx.author.mention
            ))
            return
        if arg2==None:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, you need the srl room specified.'.format(
                author=ctx.author.mention
            ))
            return
        if re.search('^#srl-[a-z0-9]{5}$',arg2):
            raceid = arg2.partition('-')[-1]
            channel = arg2
        else:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, that doesn\'t look like an SRL race room.'.format(
                author=ctx.author.mention
            ))
            return
        if not await srl.is_race_open(raceid):
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, that race does not exist or is not in an "Entry Open" state.'.format(
                author=ctx.author.mention
            ))
            return

        # figure out if this game has already been generated
        sbdb = db.SpoilerBotDatabase(loop)
        await sbdb.connect()
        racedata = await sbdb.get_bracket_race(raceid)
        await sbdb.close()
        
        if not racedata == None:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, game data was already generated for that SRL room, try using `$resend #srl-12345` where `#srl-12345` is the SRL channel name to resend seed information and have the bot join the room.'.format(
                author=ctx.author.mention
            ))
            return
    else:
        if arg1==None:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, you the race id.'.format(
                author=ctx.author.mention
            ))
            return
        raceid = 'nosrl' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        channel = ''

    if skirmish==False:
        sg_episode_id = arg1
        sge = await sg.find_episode(sg_episode_id)
        participants = await sge.get_participants_discord()
        players = await sge.get_player_names()
        participants.append(ctx.author.name + '#' + ctx.author.discriminator)

        #filter out duplicates
        participants = list(set(participants))

        if participants == False:
            await ctx.message.add_reaction('👎')
            await ctx.send('{author}, that episode doesn\'t appear to exist.'.format(
                author=ctx.author.mention
            ))
            return

        title = ' v. '.join(players)
        
    else:
        title = arg1
        sg_episode_id = 0


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

    spoiler_log_url = await helpers.write_json_to_disk(spoiler_log[0], seed.hash)

    modlogchannel = ctx.guild.get_channel(config['log_channel'][ctx.guild.id])
    msg = 'Race {title}:\n\n' \
    'SRL Channel: {srlchannel}\n' \
    'Permalink: {permalink}\n' \
    'Spoiler log: {spoilerlog}'.format(
        title=title,
        srlchannel=channel,
        permalink=await seed.url(),
        spoilerlog=spoiler_log_url
    )
    await modlogchannel.send(msg)

    spdb = db.SpoilerBotDatabase(loop)
    await spdb.connect()
    await spdb.record_bracket_race(
        sg_episode_id=sg_episode_id,
        srl_race_id=raceid,
        hash=seed.hash,
        title=title,
        permalink=await seed.url(),
        spoiler_url=spoiler_log_url,
        initiated_by=ctx.author.name + '#' + ctx.author.discriminator,
    )
    await spdb.close()

    if skirmish==True:
        msg = await generate_skirmish_msg(
            seed=seed,
            title=title,
            channel=channel,
        )
        await ctx.send(msg)
    else:
        msg = await generate_bracket_dm(
            seed=seed,
            players=players,
            channel=channel,
            )
        for user in participants:
            u = ctx.guild.get_member_named(user)
            if u == None:
                #log this at sometime, for now just skip
                pass
            else:
                dm = u.dm_channel
                if dm == None:
                    dm = await u.create_dm()
                await dm.send(msg)
    
    if nosrl==False:
        ircbot.send('JOIN', channel=channel)

    await ctx.message.add_reaction('👍')

async def generate_bracket_dm(seed, players, channel):
    msg = 'Details for race {player1} vs {player2}:\n\n' \
    'SRL Channel: {srlchannel}\n' \
    'Permalink: {permalink}\n' \
    'Code: [{fscode}]\n\n' \
    'In the SRL room, issue the command `.spoilerstart` to have the bot begin gatekeeping.\n' \
    'The bot will wait for all joined players to be readied up, and any human gatekeepers to leave (such as the restreamer).\n' \
    'At that point a link to the spoiler log and a 15 minute countdown timer will commence.  If you do not get the spoiler log in SRL, DM an admin immediately!\n\n' \
    'Good luck <:mudora:536293302689857567>'.format(
        player1=players[0],
        player2=players[1],
        srlchannel=channel,
        permalink=await seed.url(),
        fscode=' | '.join(await seed.code()))
    return msg

async def generate_skirmish_msg(seed, title, channel):
    msg = 'Skirmish title: {title}\n\n' \
    'SRL Channel: {srlchannel}\n' \
    'Permalink: {permalink}\n' \
    'Code: [{fscode}]\n\n' \
    'In the SRL room, issue the command `.spoilerstart` to have the bot begin gatekeeping.\n' \
    'The bot will wait for all joined players to be readied up, and any human gatekeepers to leave.\n' \
    'At that point a link to the spoiler log and a 15 minute countdown timer will commence.  If you do not get the spoiler log in SRL, DM an admin immediately!\n\n' \
    'Good luck <:mudora:536293302689857567>'.format(
        title=title,
        srlchannel=channel,
        permalink=await seed.url(),
        fscode='|'.join(await seed.code()))
    return msg


async def generate_bracket_spoiler_dm(participants, players, spoilerurl):
    msg = 'Spoiler log for {player1} vs {player2}:\n\n' \
        '{spoilerurl}'.format(
            player1=players[0],
            player2=players[1],
            spoilerurl=spoilerurl,
        )
    return msg