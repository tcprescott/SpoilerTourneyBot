from discord.ext import commands

class Eggs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # bunch of fluff because I like fluff
    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def pizza(self, ctx):
        await ctx.send('🍕')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def beer(self, ctx):
        await ctx.send('🍺')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def dead(self, ctx):
        await ctx.send('⚰️')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def mudora(self, ctx):
        await ctx.send('<:mudora:536293302689857567>')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def linkface(self, ctx):
        await ctx.send('<:LinkFace:545809659651686400>')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def validation(self, ctx):
        await ctx.send('<:validate:559467160469241857>')

    @commands.command(hidden=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def ThanksSolski(self, ctx):
        await ctx.send('yw')

    @commands.command(hidden=True)
    @commands.has_any_role('admin')
    async def throwerror(self, ctx):
        raise Exception

def setup(bot):
    bot.add_cog(Eggs(bot))