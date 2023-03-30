"""Functions collection for HTTP requests"""
import aiohttp

import settings


async def get(url):
    response = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as get_response:
                response = await get_response.json()
    except Exception as e:
        print('Exception in get():', e)
    return response


async def patch(url, data):
    response = []
    status = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, data=data) as get_response:
                response = await get_response.json()
                status = get_response.status
    except Exception as e:
        print('Exception in patch():', e)
    return response, status


async def post(url, data):
    response = []
    status = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, data=data) as get_response:
                response = await get_response.json()
                status = get_response.status
    except Exception as e:
        print('Exception in post():', e)
    return response, status


async def get_current_db_record_id():
    url = settings.host + 'last'
    rsp = await get(url)
    if not len(rsp):
        return None
    response = rsp[0]
    return response['id']


async def send_comment(comment):
    if not comment or comment == 'None':
        return
    idx = await get_current_db_record_id()
    if not idx:
        return
    url = settings.host + f'patch/{idx}/'
    await patch(url=url, data={"comment": comment})
