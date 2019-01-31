import asyncio
import re
import aiohttp
import json
import aiofiles

import ircmessage
import datetime

import math

import spoilerbot.sg as sg

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

async def gatekeeper(ircbot, discordctx, sg_episode_id, channel, spoilerlogurl, players, seed, raceid, loop):
    ircbot.send('JOIN', channel=channel)
    await asyncio.sleep(1)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2} - {permalink} - [{code}]'.format(
        player1=players[0],
        player2=players[1],
        permalink=await seed.url(),
        code=' | '.join(await seed.code())
    ))
    ircbot.send('PRIVMSG', target=channel, message='.join')
    await wait_for_ready_up(raceid)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2} - Log Study In Progress'.format(
        player1=players[0],
        player2=players[1],
    ))
    await asyncio.sleep(1)
    ready_players = await get_race_players(raceid)
    for player in ready_players['Ready']:
        ircbot.send('NOTICE', channel=channel, target=player, message='---------------')
        ircbot.send('NOTICE', channel=channel, target=player, message='This race\'s spoiler log: {spoilerurl}'.format(
            spoilerurl=spoilerlogurl
        ))
        ircbot.send('NOTICE', channel=channel, target=player, message='---------------')
        ircbot.send('NOTICE', channel=channel, target=player, message='Permalink: {permalink}'.format(
            permalink=await seed.url()
        ))
        ircbot.send('NOTICE', channel=channel, target=player, message='Code: [{code}]'.format(
            code=' | '.join(await seed.code())
        ))
        ircbot.send('NOTICE', channel=channel, target=player, message='---------------')

    sge = await sg.find_episode(sg_episode_id)
    participants = await sge.get_participants_discord()
    participants.append(discordctx.author.name + '#' + discordctx.author.discriminator)
    #filter out duplicates
    participants = list(set(participants))

    msg = await generate_bracket_spoiler_dm(participants, players, spoilerlogurl)
    for user in participants:
        u = discordctx.guild.get_member_named(user)
        if u == None:
            #log this at sometime, for now just skip
            pass
        else:
            dm = u.dm_channel
            if dm == None:
                dm = await u.create_dm()
            await dm.send(msg)

    await countdown_timer(
        duration_in_seconds=61,
        srl_channel=channel,
        loop=loop,
        ircbot=ircbot,
        discordctx=discordctx,
    )
    ircbot.send('PRIVMSG', target=channel, message='GLHF! :mudora:')
    ircbot.send('PRIVMSG', target=channel, message='.quit')
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2}'.format(
        player1=players[0],
        player2=players[1],
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
    # if channel == '#speedrunslive':
    #     return
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


async def countdown_timer(duration_in_seconds, srl_channel, loop, ircbot, discordctx):
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


async def generate_bracket_spoiler_dm(participants, players, spoilerlogurl):
    msg = 'Spoiler log for {player1} vs {player2}:\n\n' \
        '{spoilerurl}'.format(
            player1=players[0],
            player2=players[1],
            spoilerurl=spoilerlogurl,
        )
    return msg