import asyncio
import aiohttp
import json

import dateutil.parser

import spoilerbot.config as cfg
config = cfg.get_config()

async def async_req_general(url, method='get', reqparams=None, data=None, header={}):
    async with aiohttp.ClientSession() as session:
        async with session.request(method.upper(), url, params=reqparams, data=data, headers=header) as resp:
            if 200 <= resp.status < 300:
                data = await resp.text()
                # have to either add dud variable or everything becomes an array and more lines to edit
                return resp, data
            else:
                # print(resp.text)
                return resp, "error"

async def get_twitch_video_published(id):
    resp, data = await async_req_general(
        url='https://api.twitch.tv/helix/videos',
        reqparams={
            'id': id,
        },
        header={
            'Client-ID': config['twitch_creds']['clientid'],
        }
    )
    if data == "error":
        return None
    video = json.loads(data)
    published_at = dateutil.parser.parse(video['data'][0]['created_at'])
    return published_at

async def get_youtube_stream_published(id):
    resp, data = await async_req_general(
        url='https://www.googleapis.com/youtube/v3/videos',
        reqparams={
            'id': id,
            'key': config['youtube_credcs']['apikey'],
            'part': 'liveStreamingDetails'
        }
    )
    try:
        streamed_at = dateutil.parser.parse(json.loads(data)['items'][0]['liveStreamingDetails']['actualStartTime'])
    except KeyError:
        return None
    except IndexError:
        return None

    return streamed_at