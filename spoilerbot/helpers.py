from oauth2client.service_account import ServiceAccountCredentials
import math
import asyncio

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_name('cfg/spoilertourneybot_googlecreds.json',
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

def check_cmd_filter(guildid, channelname, cmd, config):
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

async def countdown_timer(duration_in_seconds, srl_channel, loop, ircbot):
    reminders = [900,600,300,120,60,30,10,9,8,7,6,5,4,3,2,1]
    start_time = loop.time()
    end_time = loop.time() + duration_in_seconds
    while True:
        # print(datetime.datetime.now())
        timeleft = math.ceil(start_time - loop.time() + duration_in_seconds)
        # print(timeleft)
        if timeleft in reminders:
            minutes = math.floor(timeleft/60)
            seconds = math.ceil(timeleft % 60)
            if minutes == 0:
                msg = '{seconds} second(s) remain!'.format(
                    seconds=seconds
                )
            else:
                msg = '{minutes} minute(s), {seconds} remain!'.format(
                    minutes=minutes,
                    seconds=seconds
                )
            ircbot.send('PRIVMSG', target=srl_channel, message=msg)
            reminders.remove(timeleft)
        if (loop.time() + 1) >= end_time:
            break
        await asyncio.sleep(.5)