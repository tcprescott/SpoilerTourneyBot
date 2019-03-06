from discord.ext import commands
import spoilerbot.helpers as helpers

from datetime import datetime
from dateutil import tz
import spoilerbot.checkstream as cs
import re

class Verifiers:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role("admin","qual-validator")
    @helpers.has_any_channel('admin-chat','qual-validators','bot-testing')
    async def timediff(self, ctx, start, end):
        tdelta = datetime.strptime(end, get_fmt(end)) - datetime.strptime(start, get_fmt(start))
        await ctx.send('Time diff is {diff}'.format(
            diff=str(tdelta)
        ))
    
    @commands.command(
        help='Get a stream start timestamp.\n\n'
            'service = youtube or twitch.\n'
            'id = the video id in the URL',
        brief='Get a stream start timestamp.'
    )
    @commands.has_any_role('admin','qual-validator')
    @helpers.has_any_channel('admin-chat','qual-validators','bot-testing')
    async def checkstream(self, ctx, service, id):
        await ctx.message.add_reaction('⌚')

        if service=='twitch':
            date=await cs.get_twitch_video_published(id)
        elif service=='youtube':
            date=await cs.get_youtube_stream_published(id)
        else:
            await ctx.send('Must specify twitch or youtube for service!')
            await ctx.message.add_reaction('👎')
            await ctx.message.remove_reaction('⌚',ctx.bot.user)
            return

        if date == None:
            await ctx.send('Specified id not present or is not a livestream.')
            await ctx.message.add_reaction('👎')
            await ctx.message.remove_reaction('⌚',ctx.bot.user)
            return

        await ctx.send('{mention}, the stream was started `{date}`'.format(
            mention=ctx.author.mention,
            date=date.astimezone(tz.gettz('America/New_York'))
        ))

        await ctx.message.add_reaction('👍')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)

def get_fmt(time):
    if re.search('^([0-9]|[0-5][0-9]):([0-9]|[0-5][0-9])$', time):
        return '%M:%S'

    elif re.search('^([0-9]|[0-9][0-9]):([0-9]|[0-5][0-9]):([0-9]|[0-5][0-9])$', time):
        return '%H:%M:%S'

    elif re.search('^[0-9]|[0-5][0-9]$', time):
        return '%S'

    else:
        return None

def setup(bot):
    bot.add_cog(Verifiers(bot))