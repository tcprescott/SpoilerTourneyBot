from oauth2client.service_account import ServiceAccountCredentials
import math
import asyncio
import bisect

import random, string
import json
import aiofiles

from discord.ext import commands

import spoilerbot.config as cfg
config = cfg.get_config()

# this grabs our google service account's credentials
# (spoilertournamentbot@spoilertourneybot.iam.gserviceaccount.com)
def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json',
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

# a custom command check that lets us filter commands by originating channel
def has_any_channel(*channels):
    async def predicate(ctx):
        return ctx.channel and ctx.channel.name in channels
    return commands.check(predicate)

# our global error handler
async def error_handle(ctx,error,logger):
    await ctx.message.add_reaction('👎')
    await ctx.send('{author}, there was a problem with your request.  Ping an admin if this condition persists.'.format(
        author=ctx.author.mention
    ))
    logger.error('{cmd} error - {servername} - {channelname} - {player} - {error}'.format(
        cmd = ctx.invoked_with,
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        error = error,
    ))

    # send the error to the bot-log channel so we can troubleshoot it all later
    modlogchannel = ctx.guild.get_channel(config['log_channel'][ctx.guild.id])
    msg = 'Error in {cmd}:\n\n' \
    'Error: {error}\n' \
    'Channel: {channel}\n'.format(
        cmd = ctx.invoked_with,
        error=error,
        channel=ctx.channel.name,
    )
    await modlogchannel.send(msg)

async def write_json_to_disk(spoiler, seed):
    code = await seed.code()
    filename = 'spoilertourneylog__' + seed.hash + '__' + '-'.join(code).replace(' ', '') + '__' + ''.join(random.choices(string.ascii_letters + string.digits, k=4)) + '.txt'

    # magic happens here to make it pretty-printed and tournament-compliant
    s = json.loads(spoiler)
    del s['meta']['_meta']
    del s['playthrough']
    del s['Shops'] #QOL this information is useless for this tournament
    del s['Bosses'] #QOL this information is useful only for enemizer

    sorteddict = {}

    prizemap = [
        ['Eastern Palace', 'Eastern Palace - Prize'],
        ['Desert Palace', 'Desert Palace - Prize'],
        ['Tower Of Hera', 'Tower of Hera - Prize'],
        ['Dark Palace', 'Palace of Darkness - Prize'],
        ['Swamp Palace', 'Swamp Palace - Prize'],
        ['Skull Woods', 'Skull Woods - Prize'],
        ['Thieves Town', 'Thieves\' Town - Prize'],
        ['Ice Palace', 'Ice Palace - Prize'],
        ['Misery Mire', 'Misery Mire - Prize'],
        ['Turtle Rock', 'Turtle Rock - Prize'],
    ]
    sorteddict['Prizes'] = {}
    for dungeon, prize in prizemap:
        sorteddict['Prizes'][dungeon] = s[dungeon][prize]
    sorteddict['Special']        = s['Special']
    sorteddict['Hyrule Castle']  = sort_dict(s['Hyrule Castle'])
    sorteddict['Eastern Palace'] = sort_dict(s['Eastern Palace'])
    sorteddict['Desert Palace']  = sort_dict(s['Desert Palace'])
    sorteddict['Tower Of Hera']  = sort_dict(s['Tower Of Hera'])
    sorteddict['Castle Tower']   = sort_dict(s['Castle Tower'])
    sorteddict['Dark Palace']    = sort_dict(s['Dark Palace'])
    sorteddict['Swamp Palace']   = sort_dict(s['Swamp Palace'])
    sorteddict['Skull Woods']    = sort_dict(s['Skull Woods'])
    sorteddict['Thieves Town']   = sort_dict(s['Thieves Town'])
    sorteddict['Ice Palace']     = sort_dict(s['Ice Palace'])
    sorteddict['Misery Mire']    = sort_dict(s['Misery Mire'])
    sorteddict['Turtle Rock']    = sort_dict(s['Turtle Rock'])
    sorteddict['Ganons Tower']   = sort_dict(s['Ganons Tower'])
    sorteddict['Light World']    = sort_dict(s['Light World'])
    sorteddict['Death Mountain'] = sort_dict(s['Death Mountain'])
    sorteddict['Dark World']     = sort_dict(s['Dark World'])

    drops = get_seed_prizepacks(seed.patchdata)
    sorteddict['Drops']          = {}
    sorteddict['Drops']['PullTree'] = drops['PullTree']
    sorteddict['Drops']['RupeeCrab'] = {}
    sorteddict['Drops']['RupeeCrab']['Main'] = drops['RupeeCrab']['Main']
    sorteddict['Drops']['RupeeCrab']['Final'] = drops['RupeeCrab']['Final']
    sorteddict['Drops']['Stun'] = drops['Stun']
    sorteddict['Drops']['FishSave'] = drops['FishSave']

    sorteddict['Special']['DiggingGameDigs'] = seek_patch_data(seed.patchdata['patch'], 982421, 1)[0]

    sorteddict['meta']           = s['meta']
    sorteddict['meta']['hash']   = seed.hash
    sorteddict['meta']['permalink'] = await seed.url()

    for dungeon, prize in prizemap:
        del sorteddict[dungeon][prize]

    async with aiofiles.open(config['spoiler_log_local'] + '/' + filename, "w", newline='\r\n') as out:
        await out.write(json.dumps(sorteddict, indent=4))
        await out.flush()

    return config['spoiler_log_url_base'] + '/' + filename

def sort_dict(dict):
    sorteddict = {}
    for key in sorted(dict):
        sorteddict[key] = dict[key]
    return sorteddict

def get_sprite_droppable(i):
    spritemap = {
        121: "Bee", 178: "BeeGood", 216: "Heart",
        217: "RupeeGreen", 218: "RupeeBlue", 219: "RupeeRed",
        220: "BombRefill1", 221: "BombRefill4", 222: "BombRefill8",
        223: "MagicRefillSmall", 224: "MagicRefillFull",
        225: "ArrowRefill5", 226: "ArrowRefill10",
        227: "Fairy",
    }
    try: return spritemap[i]
    except KeyError: return 'ERR: UNKNOWN'

def get_seed_prizepacks(data):
    d = {}
    d['PullTree'] = {}
    d['RupeeCrab'] = {}

    stun_offset = '227731'
    pulltree_offset = '981972'
    rupeecrap_main_offset = '207304'
    rupeecrab_final_offset = '207300'
    fishsave_offset = '950988'

    for patch in data['patch']:
        if stun_offset in patch:
            d['Stun'] = get_sprite_droppable(patch[stun_offset][0])
        if pulltree_offset in patch:
            d['PullTree']['Tier1'] = get_sprite_droppable(patch[pulltree_offset][0])
            d['PullTree']['Tier2'] = get_sprite_droppable(patch[pulltree_offset][1])
            d['PullTree']['Tier3'] = get_sprite_droppable(patch[pulltree_offset][2])
        if rupeecrap_main_offset in patch:
            d['RupeeCrab']['Main'] = get_sprite_droppable(patch[rupeecrap_main_offset][0])
        if rupeecrab_final_offset in patch:
            d['RupeeCrab']['Final'] = get_sprite_droppable(patch[rupeecrab_final_offset][0])
        if fishsave_offset in patch:
            d['FishSave'] = get_sprite_droppable(patch[fishsave_offset][0])
    
    return d

def seek_patch_data(patches, offset, bytes):
    """[summary]
    
    Arguments:
        patches {list} -- a list of dictionaries depicting raw patch data
        offset {int} -- a decimal integer of the offset to look for
        bytes {int} -- the number of bytes to retrieve
    
    Raises:
        ValueError -- raised if the offset could not be found
    
    Returns:
        list -- a list of bytes of the requested offset
    """

    offsetlist = []
    for patch in patches:
        for key, value in patch.items():
            offsetlist.append(int(key))
    offsetlist_sorted = sorted(offsetlist)
    i = bisect.bisect_left(offsetlist_sorted, offset)
    if i:
        if offsetlist_sorted[i] == offset:
            seek = str(offset)
            for patch in patches:
                if seek in patch:
                    return patch[seek][:bytes]
        else:
            left_slice = offset - offsetlist_sorted[i-1]
            for patch in patches:
                seek = str(offsetlist_sorted[i-1])
                if seek in patch:
                    return patch[seek][left_slice:left_slice + bytes]
    raise ValueError