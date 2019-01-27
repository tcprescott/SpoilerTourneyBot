import asyncio
import aiohttp
import json

import spoilerbot.config as cfg

config = cfg.get_config()

async def get_sg_episode(episodeid):
    async with aiohttp.ClientSession() as session:
        async with session.get(config['sg_api_endpoint'] + '/episode/?id=' + str(episodeid)) as response:
            raw = await response.text()
            return json.loads(raw)

async def get_participants(episodeid):
    episode = await get_sg_episode(episodeid)
    if 'error' in episode:
        return False
    particpants = []
    for commentator in episode['commentators']:
        if commentator['approved'] == True:
            particpants.append(commentator['discordTag'])
    for tracker in episode['trackers']:
        if tracker['approved'] == True:
            particpants.append(tracker['discordTag'])
    for broadcaster in episode['broadcasters']:
        if broadcaster['approved'] == True:
            particpants.append(tracker['discordTag'])
    if not episode['match1'] == None:
        for player in episode['match1']['players']:
            particpants.append(player['discordTag'])
    if not episode['match2'] == None:
        for player in episode['match2']['players']:
            particpants.append(player['discordTag'])
    return particpants