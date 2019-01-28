import asyncio
import re
import aiohttp
import json

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

async def gatekeeper(ircbot, channel, raceid, spoilerlogurl, players, permalink, loop):
    ircbot.send('JOIN', channel=channel)
    await asyncio.sleep(2)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2} - {permalink}'.format(
        player1=players[0],
        player2=players[1],
        permalink=permalink,
    ))
    ircbot.send('PRIVMSG', target=channel, message='.join')
    await wait_for_ready_up(raceid)
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2} - {permalink} - Log Study In Progress'.format(
        player1=players[0],
        player2=players[1],
        permalink=permalink,
    ))
    await asyncio.sleep(5)
    ircbot.send('PRIVMSG', target=channel, message='---------------')
    ircbot.send('PRIVMSG', target=channel, message='This race\'s spoiler log: {spoilerurl}'.format(
        spoilerurl=spoilerlogurl
    ))
    ircbot.send('PRIVMSG', target=channel, message='---------------')
    await helpers.countdown_timer(
        duration_in_seconds=61,
        srl_channel=channel,
        loop=loop,
        ircbot=ircbot
    )
    ircbot.send('PRIVMSG', target=channel, message='GLHF! :mudora:')
    ircbot.send('PRIVMSG', target=channel, message='.quit')
    ircbot.send('PRIVMSG', target=channel, message='.setgoal ALTTPR Spoiler Tournament - {player1} vs. {player2} - {permalink}'.format(
        player1=players[0],
        player2=players[1],
        permalink=permalink,
    ))
    ircbot.send('PART', channel=channel)

async def get_race(raceid):
    async with aiohttp.ClientSession() as session:
        async with session.get('http://api.speedrunslive.com/races/' + raceid) as response:
            raw = await response.text()
            return json.loads(raw)

async def are_ready(raceid, config):
    race = await get_race(raceid)
    readycount=0
    entrants = race['entrants']
    try:
        del entrants[config['srl_irc_nickname'].lower()]
    except KeyError:
        pass
    try:
        del entrants['JOPEBUSTER']
    except KeyError:
        pass
    for entrant in entrants:
        if race['entrants'][entrant]['statetext'] == 'Ready':
            readycount=readycount+1
    if readycount==len(entrants) and len(entrants) >= 2:
        return True
    else:
        return False

async def wait_for_ready_up(raceid, config):
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

async def is_race_open(race):
    try:
        if race['state'] == 1:
            return True
        else:
            return False
    except KeyError:
        return False