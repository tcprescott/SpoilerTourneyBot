import asyncio
import aiomysql

import spoilerbot.config as cfg
config = cfg.get_config()

class SpoilerBotDatabase():
    def __init__(self, loop):
        self.loop = loop

    async def connect(self):
        conn = await aiomysql.connect(
            user=config['spoilerbot_db']['username'],
            db=config['spoilerbot_db']['database'],
            host=config['spoilerbot_db']['hostname'],
            password=config['spoilerbot_db']['password'],
            loop=self.loop
        )
        self.conn = conn

    async def close(self):
        conn = self.conn.close()

    async def get_qualifier_seed(self, id):
        cursor = await self.conn.cursor()
        sql = 'SELECT hash FROM qualifier_seeds where id=%s'
        result = await cursor.execute(sql, (id))
        return await cursor.fetchone()

    # async def record_qualifier_request(self, id, date, discord_tag, seed, retry, verification_key):
    #     cursor = await self.conn.cursor()
    #     sql = "INSERT INTO test (sg_episode_id) VALUES (%s)"
    #     await cursor.execute(sql, (episodeid))
    #     await self.conn.commit()

    async def record_bracket_race(self, sg_episode_id, srl_race_id, hash, player1, player2, permalink, spoiler_url, initiated_by):
        cursor = await self.conn.cursor()
        sql = 'INSERT INTO bracket_races (sg_episode_id, srl_race_id, hash, player1, player2, permalink, spoiler_url, initiated_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        await cursor.execute(sql, (sg_episode_id, srl_race_id, hash, player1, player2, permalink, spoiler_url, initiated_by))
        await self.conn.commit()

class RandomizerDatabase():
    def __init__(self,loop):
        self.loop = loop

    async def connect(self):
        conn = await aiomysql.connect(
            user=config['randomizer_db']['username'],
            db=config['randomizer_db']['database'],
            host=config['randomizer_db']['hostname'],
            password=config['randomizer_db']['password'],
            loop=self.loop
        )
        self.conn = conn

    async def close(self):
        conn = self.conn.close()

    async def get_seed_spoiler(self, hashid):
        cursor = await self.conn.cursor()
        sql = 'SELECT spoiler FROM seeds where hash=%s'
        result = await cursor.execute(sql, (hashid))
        return await cursor.fetchone()