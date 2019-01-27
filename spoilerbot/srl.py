import asyncio

async def connect(ircbot, config, loop):
    ircbot.send('NICK', nick=config['srl_irc_nickname'])
    ircbot.send('USER', user=config['srl_irc_nickname'],
             realname='https://github.com/numberoverzero/bottom')

    # Don't try to join channels until the server has
    # sent the MOTD, or signaled that there's no MOTD.
    done, pending = await asyncio.wait(
        [ircbot.wait("RPL_ENDOFMOTD"),
         ircbot.wait("ERR_NOMOTD")],
        loop=loop,
        return_when=asyncio.FIRST_COMPLETED
    )

    #raw command because I can't seem to get this to work with send()
    ircbot.send('PRIVMSG', target='NICKSERV', message='identify ' + config['srl_irc_password'])

    # Cancel whichever waiter's event didn't come in.
    for future in pending:
        future.cancel()

    ircbot.send('JOIN', channel='#speedrunslive')