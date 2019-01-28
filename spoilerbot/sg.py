import asyncio
import aiohttp
import json

import spoilerbot.config as cfg

config = cfg.get_config()

async def find_episode(episodeid):
    episode = SpeedGamingEpisode(episodeid)
    await episode._init()
    return episode

class SpeedGamingEpisode():
    def __init__(self, episodeid):
        self.episodeid=episodeid

    async def _init(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(config['sg_api_endpoint'] + '/episode/?id=' + str(self.episodeid)) as response:
                raw = await response.text()
                self.episode = json.loads(raw)

    async def get_participants_discord(self):
        if 'error' in self.episode:
            return False
        particpants = []
        for commentator in self.episode['commentators']:
            if commentator['approved'] == True:
                particpants.append(commentator['discordTag'])
        for tracker in self.episode['trackers']:
            if tracker['approved'] == True:
                particpants.append(tracker['discordTag'])
        for broadcaster in self.episode['broadcasters']:
            if broadcaster['approved'] == True:
                particpants.append(tracker['discordTag'])
        if not self.episode['match1'] == None:
            for player in self.episode['match1']['players']:
                particpants.append(player['discordTag'])
        if not self.episode['match2'] == None:
            for player in self.episode['match2']['players']:
                particpants.append(player['discordTag'])
        return particpants

    async def get_player_names(self):
        players = []
        if not self.episode['match1'] == None:
            for player in self.episode['match1']['players']:
                players.append(player['displayName'])
        if not self.episode['match2'] == None:
            for player in self.episode['match2']['players']:
                players.append(player['displayName'])
        return players