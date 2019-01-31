import re
import spoilerbot.srl as srl
import spoilerbot.sg as sg
import spoilerbot.database as db

import random, string

import pyz3r_asyncio

import json

import aiofiles

import spoilerbot.config as cfg
config = cfg.get_config()

async def restreamrace(ctx, loop, ircbot, arg1=None, arg2=None):
    if arg1==None or arg2==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, you need both the race id and srl room specified.'.format(
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

    sge = await sg.find_episode(arg1)
    participants = await sge.get_participants_discord()
    players = await sge.get_player_names()
    # participants = []
    participants.append(ctx.author.name + '#' + ctx.author.discriminator)

    #filter out duplicates
    participants = list(set(participants))

    if participants == False:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that episode doesn\'t appear to exist.'.format(
            author=ctx.author.mention
        ))
        return
    
    seed = await pyz3r_asyncio.create_seed(
        randomizer='item', # optional, defaults to item
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        append_json_extension=False,
        settings={
            "difficulty": "normal",
            "enemizer": False,
            "logic": "NoGlitches",
            "mode": "open",
            "tournament": False,
            "variation": "none",
            "weapons": "randomized",
            "lang": "en"
        }
    )

    rdb = db.RandomizerDatabase(loop)
    await rdb.connect()
    spoiler_log = await rdb.get_seed_spoiler(seed.hash)
    await rdb.close()

    spoiler_log_url = await write_json_to_disk(spoiler_log[0], seed.hash)
    print(spoiler_log_url)

    spdb = db.SpoilerBotDatabase(loop)
    await spdb.connect()
    await spdb.record_bracket_race(
        sg_episode_id=arg1,
        srl_race_id=raceid,
        hash=seed.hash,
        player1=players[0],
        player2=players[1],
        permalink=await seed.url(),
        spoiler_url=spoiler_log_url,
        initiated_by=ctx.author.name + '#' + ctx.author.discriminator,
    )
    await spdb.close()

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
    
    await ctx.message.add_reaction('👍')
    # call SRL gatekeeper coroutine
    await srl.gatekeeper(
        ircbot=ircbot,
        discordctx=ctx,
        sg_episode_id=arg1,
        channel=channel,
        spoilerlogurl=spoiler_log_url,
        players=players,
        seed=seed,
        raceid=raceid,
        loop=loop
    )

async def generate_bracket_dm(seed, players, channel):
    msg = 'Details for race {player1} vs {player2}:\n\n' \
    'SRL Channel: {srlchannel}\n' \
    'Permalink: {permalink}\n' \
    'Code: [{fscode}]\n\n' \
    'The bot will provide the spoiler log in SRL chat once all joined players have readied up.\n' \
    'At that point a link to the spoiler log and a 15 minute countdown timer will commence.\n\n' \
    'Good luck <:mudora:536293302689857567>'.format(
        player1=players[0],
        player2=players[1],
        srlchannel=channel,
        permalink=await seed.url(),
        fscode=' | '.join(await seed.code()))
    return msg

async def generate_bracket_spoiler_dm(participants, players, spoilerurl):
    msg = 'Spoiler log for {player1} vs {player2}:\n\n' \
        '{spoilerurl}'.format(
            player1=players[0],
            player2=players[1],
            spoilerurl=spoilerurl,
        )
    return msg

async def write_json_to_disk(spoiler, hash):
    filename = 'spoilertourneylog__' + hash + '__' + ''.join(random.choices(string.ascii_letters + string.digits, k=6)) + '.txt'

    # magic happens here to make it pretty-printed and tournament-compliant
    s = json.loads(spoiler)
    del s['meta']['_meta']
    del s['playthrough']

    async with aiofiles.open(config['spoiler_log_local'] + '/' + filename, "w") as out:
        await out.write(json.dumps(s, indent=4, sort_keys=True))
        await out.flush()

    return config['spoiler_log_url_base'] + '/' + filename