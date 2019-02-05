from oauth2client.service_account import ServiceAccountCredentials
import math
import asyncio

import spoilerbot.config as cfg
config = cfg.get_config()

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json',
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

def check_cmd_filter(guildid, channelname, cmd):
    if not channelname in config['cmd_filters'][cmd][guildid]:
        return True
    else:
        return False

async def error_handle(ctx,error,logger,cmd):
    await ctx.message.add_reaction('👎')
    await ctx.send('{author}, there was a problem with your request.  Ping an admin if this condition persists.'.format(
        author=ctx.author.mention
    ))
    logger.error('{cmd} error - {servername} - {channelname} - {player} - {error}'.format(
        cmd = cmd,
        servername = ctx.guild.name,
        channelname = ctx.channel.name,
        player = ctx.author,
        error = error,
    ))

    modlogchannel = ctx.guild.get_channel(config['log_channel'][ctx.guild.id])
    msg = 'Error in {cmd}:\n\n' \
    'Error: {error}\n' \
    'Channel: {channel}\n'.format(
        cmd = cmd,
        error=error,
        channel=ctx.channel.name,
    )
    await modlogchannel.send(msg)