from discord.ext import commands

class Eggs:
    # bunch of fluff because I like fluff
    @commands.command(hidden=True)
    async def pizza(ctx):
        await ctx.send('🍕')

    @commands.command(hidden=True)
    async def beer(ctx):
        await ctx.send('🍺')

    @commands.command(hidden=True)
    async def dead(ctx):
        await ctx.send('⚰️')

    @commands.command(hidden=True)
    async def mudora(ctx):
        await ctx.send('<:mudora:536293302689857567>')

    @commands.command(hidden=True)
    async def linkface(ctx):
        await ctx.send('<:LinkFace:545809659651686400>')

    @commands.command(hidden=True)
    @commands.has_any_role('admin')
    async def throwerror(ctx):
        raise Exception

def setup(bot):
    bot.add_cog(Eggs(bot))