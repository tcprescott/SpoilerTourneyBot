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
        sql = 'SELECT hash, spoilerlog FROM qualifier_seeds where id=%s'
        result = await cursor.execute(sql, (id))
        return await cursor.fetchone()

    async def insert_qualifier_seed(self, id, hash, spoilerlog):
        cursor = await self.conn.cursor()
        sql = "INSERT INTO qualifier_seeds (id, hash, spoilerlog) VALUES (%s, %s, %s)"
        await cursor.execute(sql, (id, hash, spoilerlog))
        await self.conn.commit()

    async def record_verification_key(self, verification_key):
        cursor = await self.conn.cursor()
        sql = "INSERT INTO qualifier_requests (verification_key) VALUES (%s)"
        await cursor.execute(sql, (verification_key))
        await self.conn.commit()

    async def record_bracket_race(self, sg_episode_id, srl_race_id, hash, title, permalink, spoiler_url, initiated_by):
        cursor = await self.conn.cursor()
        sql = 'INSERT INTO bracket_races (sg_episode_id, srl_race_id, hash, title, permalink, spoiler_url, initiated_by) VALUES (%s, %s, %s, %s, %s, %s, %s)'
        await cursor.execute(sql, (sg_episode_id, srl_race_id, hash, title, permalink, spoiler_url, initiated_by))
        await self.conn.commit()

    async def get_verification_key(self, verification_key):
        cursor = await self.conn.cursor()
        sql = 'SELECT verification_key FROM qualifier_requests WHERE verification_key = %s'
        result = await cursor.execute(sql, verification_key)
        return await cursor.fetchone()

    async def get_bracket_race(self, srl_race_id):
        cursor = await self.conn.cursor()
        sql = 'SELECT sg_episode_id, srl_race_id, hash, title, spoiler_url, initiated_by FROM bracket_races WHERE srl_race_id=%s'
        await cursor.execute(sql, (srl_race_id))
        return await cursor.fetchone()

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