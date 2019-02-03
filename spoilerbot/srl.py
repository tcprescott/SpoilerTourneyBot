import asyncio
import re
import aiohttp
import json
import aiofiles

import ircmessage
import datetime

import math

import pyz3r_asyncio

import spoilerbot.sg as sg
import spoilerbot.database as db

import spoilerbot.config as cfg
config = cfg.get_config()

async def connect(ircbot, config, loop):
    ircbot.send('NICK', nick=config['srl_irc_nickname'])
    ircbot.send('USER', user=config['srl_irc_nickname'],
             realname=config['srl_irc_nickname'])

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

async def spoilerstart(channel, author, ircbot, discordbot, loop):
    if channel == '#speedrunslive':
        return
    # ignore private messages
    if channel == config['srl_irc_nickname']:
        return

    if re.search('^#srl-[a-z0-9]{5}$',channel):
        raceid = channel.partition('-')[-1]
    else:
        return

    if not await is_race_open(raceid):
        ircbot.send('NOTICE', target=channel, author=author, message='This race is not currently open for entry.')
        return

    if not await get_single_player(raceid, player=config['srl_irc_nickname'].lower()) == None:
        ircbot.send('PRIVMSG', target=channel, message='Bot is already entered into this race.')
        return

    sbdb = db.SpoilerBotDatabase(loop)
    await sbdb.connect()
    racedata = await sbdb.get_bracket_race(raceid)
    await sbdb.close()
    if racedata == None:
        ircbot.send('PRIVMSG', target=channel, message='This race is not yet registered with SpoilerTourneyBot.  Please run $bracketrace command in discord.')
        return

    sg_episode_id = racedata[0]
    srl_race_id = racedata[1]
    hash = racedata[2]
    title = racedata[3]
    spoiler_url = racedata[4]
    initiated_by = racedata[5]

    seed = await pyz3r_asyncio.create_seed(
        randomizer='item',
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        append_json_extension=False,
        hash=hash
    )

    await gatekeeper(
        ircbot=ircbot,
        discordbot=discordbot,
        initiated_by_discordtag=initiated_by,
        sg_episode_id=sg_episode_id,
        channel=channel,
        spoilerlogurl=spoiler_url,
        title=title,
        seed=seed,
        raceid=raceid,
        loop=loop
    )


async def spoilerseed(channel, author, ircbot, loop):
    if channel == '#speedrunslive':
        return
    # ignore private messages
    if channel == config['srl_irc_nickname']:
        return

    if re.search('^#srl-[a-z0-9]{5}$',channel):
        raceid = channel.partition('-')[-1]
    else:
        return

    sbdb = db.SpoilerBotDatabase(loop)
    await sbdb.connect()
    racedata = await sbdb.get_bracket_race(raceid)
    await sbdb.close()

    if racedata == None:
        ircbot.send('PRIVMSG', target=channel, message='This race is not yet registered with SpoilerTourneyBot.  Please run $bracketrace command in discord.')
        return

    hash = racedata[2]

    seed = await pyz3r_asyncio.create_seed(
        randomizer='item',
        baseurl=config['alttpr_website']['baseurl'],
        seed_baseurl=config['alttpr_website']['baseurl_seed'],
        append_json_extension=False,
        hash=hash
    )

    ircbot.send('PRIVMSG', target=channel, message='Seed: {permalink} - {code}'.format(
        permalink=await seed.url(),
        code=' | '.join(await seed.code())
    ))

async def gatekeeper(ircbot, discordbot, initiated_by_discordtag, sg_episode_id, channel, spoilerlogurl, title, seed, raceid, loop):
    # ircbot.send('JOIN', channel=channel)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {title} - {permalink} - [{code}]'.format(
        title=title,
        permalink=await seed.url(),
        code=' | '.join(await seed.code())
    ))
    ircbot.send('PRIVMSG', target=channel, message='.join')
    await wait_for_ready_up(raceid)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {title} - Log Study In Progress'.format(
        title=title,
    ))
    await asyncio.sleep(1)
    ready_players = await get_race_players(raceid)
    ircbot.send('PRIVMSG', target=channel, message='Sending spoiler log to readied players.')
    for player in ready_players['Ready']:
        ircbot.send('NOTICE', channel=channel, target=player, message='---------------')
        ircbot.send('NOTICE', channel=channel, target=player, message='This race\'s spoiler log: {spoilerurl}'.format(
            spoilerurl=spoilerlogurl
        ))
        ircbot.send('NOTICE', channel=channel, target=player, message='---------------')
    await send_discord_dms(
        sg_episode_id=sg_episode_id,
        discordbot=discordbot,
        title=title,
        spoilerlogurl=spoilerlogurl,
        initiated_by_discordtag=initiated_by_discordtag,
    )

    await countdown_timer(
        duration_in_seconds=61,
        srl_channel=channel,
        loop=loop,
        ircbot=ircbot,
    )
    ircbot.send('PRIVMSG', target=channel, message='GLHF! :mudora:')
    ircbot.send('PRIVMSG', target=channel, message='.quit')
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {title}'.format(
        title=title,
    ))

async def get_race(raceid):
    async with aiohttp.ClientSession() as session:
        async with session.get('http://api.speedrunslive.com/races/' + raceid) as response:
            raw = await response.text()
        await session.close()
    return json.loads(raw)

async def are_ready(raceid):
    players = await get_race_players(raceid)

    try:
        ready = len(players['Ready'])
    except KeyError:
        ready = 0
    try:
        entered = len(players['Entered'])
    except KeyError:
        entered = 0

    if ready >= 1 and entered == 0:
        return True
    else:
        return False


async def wait_for_ready_up(raceid):
    readycount = 0
    while True:
        if await are_ready(raceid):
            readycount=readycount+1
            await asyncio.sleep(2)
        else:
            readycount=0
            await asyncio.sleep(10)

        if readycount>=2:
            return

async def get_race_players(raceid):
    #get current race
    race = await get_race(raceid)

    #filter out bots like JOPEBUSTER and the SpoilerTourneyBot
    try:
        del race['entrants']['JOPEBUSTER']
    except KeyError:
        pass
    try:
        del race['entrants'][config['srl_irc_nickname'].lower()]
    except KeyError:
        pass

    #build a simpliified dictionary separated by state
    players = {}
    for entrant in race['entrants']:
        players.setdefault(race['entrants'][entrant]['statetext'], []).append(entrant)
    return players

async def get_single_player(raceid, player):
    #get current race
    race = await get_race(raceid)

    #build a simpliified dictionary separated by state
    players = {}
    for entrant in race['entrants']:
        if entrant == player:
            return entrant
    return None

async def is_race_open(raceid):
    race = await get_race(raceid)
    try:
        if race['state'] == 1:
            return True
        else:
            return False
    except KeyError:
        return False
        
async def write_chat_log(channel, author, message):
    if channel == '#speedrunslive':
        return
    # ignore private messages
    if channel == config['srl_irc_nickname']:
        return
    filename = channel + ".log"
    async with aiofiles.open(config['srl_log_local'] + '/' + filename, "a") as out:
        await out.write("\"{timestamp}\" - \"{channel}\" - \"{author}\" - \"{message}\"\n".format(
            timestamp=datetime.datetime.utcnow(),
            channel=channel,
            author=author,
            message=ircmessage.unstyle(message)
        ))
        await out.close()


async def countdown_timer(duration_in_seconds, srl_channel, loop, ircbot):
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
            if minutes == 0 and seconds > 10:
                msg = '{seconds} second(s) remain!'.format(
                    seconds=seconds
                )
            elif minutes == 0 and seconds <= 10:
                msg = '{seconds} second(s) remain!'.format(
                    seconds=seconds,
                )
                msg = ircmessage.style(msg, fg='green', bold=True)
            else:
                msg = '{minutes} minute(s), {seconds} seconds remain!'.format(
                    minutes=minutes,
                    seconds=seconds
                )
            ircbot.send('PRIVMSG', target=srl_channel, message=msg)
            reminders.remove(timeleft)
        if (loop.time() + 1) >= end_time:
            break
        await asyncio.sleep(.5)

async def send_discord_dms(sg_episode_id, discordbot, title, spoilerlogurl, initiated_by_discordtag):
    if sg_episode_id=='0':
        return
    sge = await sg.find_episode(sg_episode_id)
    participants = await sge.get_participants_discord()
    participants.append(initiated_by_discordtag)
    #filter out duplicates
    participants = list(set(participants))

    msg = 'Spoiler log for {title}:\n\n' \
        '{spoilerurl}'.format(
            title=title,
            spoilerurl=spoilerlogurl,
        )

    guild = discordbot.get_guild(config['dm_discord_guild'])

    for user in participants:
        u = guild.get_member_named(user)
        if u == None:
            #log this at sometime, for now just skip
            pass
        else:
            dm = u.dm_channel
            if dm == None:
                dm = await u.create_dm()
            await dm.send(msg)