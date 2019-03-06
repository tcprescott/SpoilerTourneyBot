from discord.ext import commands

class Eggs:
    def __init__(self, bot):
        self.bot = bot

    # bunch of fluff because I like fluff
    @commands.command(hidden=True)
    async def pizza(self, ctx):
        await ctx.send('🍕')

    @commands.command(hidden=True)
    async def beer(self, ctx):
        await ctx.send('🍺')

    @commands.command(hidden=True)
    async def dead(self, ctx):
        await ctx.send('⚰️')

    @commands.command(hidden=True)
    async def mudora(self, ctx):
        await ctx.send('<:mudora:536293302689857567>')

    @commands.command(hidden=True)
    async def linkface(self, ctx):
        await ctx.send('<:LinkFace:545809659651686400>')

    @commands.command(hidden=True)
    @commands.has_any_role('admin')
    async def throwerror(self, ctx):
        raise Exception

def setup(bot):
    bot.add_cog(Eggs(bot))