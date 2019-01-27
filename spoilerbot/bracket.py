import re
import spoilerbot.srl as srl

async def restreamrace(ctx, arg1=None, arg2=None):
    if arg1==None or arg2==None:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, you need both the race id and srl room specified.'.format(
            author=ctx.author.mention
        ))
        return
    if re.search('^#srl-[a-z0-9]{5}$',arg2):
        raceid = arg2.partition('-')[-1]
        channel = arg2
        race = await srl.get_race(raceid)
    else:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that doesn\'t look like an SRL race room.'.format(
            author=ctx.author.mention
        ))
        return
    # if not await srl.is_race_open(race):
    #     await ctx.message.add_reaction('👎')
    #     await ctx.send('{author}, that race does not exist or is not in an "Entry Open" state.'.format(
    #         author=ctx.author.mention
    #     ))
    #     return

    # participants = await sg.get_participants(arg1)
    participants = ['Synack#1337']
    if participants == False:
        await ctx.message.add_reaction('👎')
        await ctx.send('{author}, that episode doesn\'t appear to exist.'.format(
            author=ctx.author.mention
        ))
        return
    
    for user in participants:
        u = ctx.guild.get_member_named(user)
        if u == None:
            #log this at sometime, for now just skip
            pass
        else:
            dm = u.dm_channel
            if dm == None:
                dm = await u.create_dm()
            await dm.send(
                'test',
            )
    
    await ctx.message.add_reaction('👍')
    # call SRL gatekeeper coroutine
    # await srl.gatekeeper(
    #     ircbot=ircbot,
    #     channel=channel,
    #     spoilerlogurl=''
    # )
