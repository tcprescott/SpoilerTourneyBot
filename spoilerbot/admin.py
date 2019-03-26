from discord.ext import commands
from .helpers import has_any_channel

import re 

class Admin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role("admin")
    @has_any_channel('twitch-clips')
    async def purgeclips(self, ctx):
        await ctx.channel.purge(limit=500, check=is_twitch_url)

def setup(bot):
    bot.add_cog(Admin(bot))

def is_twitch_url(m):
    return not re.findall('http[s]?:\/\/clips\.twitch\.tv\/[A-Za-z0-9]*', m.content)