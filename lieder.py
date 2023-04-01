import asyncio
from datetime import datetime

import settings
from http_commands import send_comment, get, post
from terminal import Terminal

terminal: Terminal
lieder_existed_position_tickets = []
positions_for_none_reopen = []
event_loop = asyncio.Event()  # init async event
# init_data = {}
init_data = {'login': 66587203,
             'password': '3hksvtko',
             'server': 'MetaQuotes-Demo',
             'path': r'C:\Program Files\MetaTrader 5\terminal64.exe'
             }
host_setting = ''
host_positions = ''
host_trade_state = ''


async def get_settings():
    global init_data
    url = host_setting
    init_data = await get(url)


def is_init_data_valid(data):
    return data['login'] and data['password'] and data['server'] and data['path']


async def send_position(position):
    url = host_positions
    data = {'ticket': position.ticket,
            'time': position.time,
            'time_update': position.time_update,
            'type': position.type,
            'magic': position.magic,
            'volume': position.volume,
            'price_open': position.price_open,
            'tp': position.tp,
            'sl': position.sl,
            'price_current': position.price_current,
            'symbol': position.symbol,
            'comment': position.comment,
            'price_close': position.price_close,
            'time_close': position.time_close,
            }
    await post(url=url, data=data)


async def send_trade_state(balance, equity):
    url = host_trade_state
    data = {'balance': balance,
            'equity': equity,
            }
    await post(url=url, data=data)


async def update_lieder_info(sleep=settings.sleep_lieder_update):
    global lieder_existed_position_tickets, positions_for_none_reopen
    while True:
        lieder_balance = terminal.get_balance()
        lieder_equity = terminal.get_equity()
        await send_trade_state(lieder_balance, lieder_equity)

        input_positions = Terminal.get_positions(only_own=False)

        if len(lieder_existed_position_tickets) == 0:
            for _ in input_positions:
                lieder_existed_position_tickets.append(_.ticket)

        # lieder_positions = []
        # if source['investors'][0]['reconnected'] == 'Не переоткрывать':
        #     for _ in input_positions:
        #         if _.ticket not in lieder_existed_position_tickets:
        #             lieder_positions.append(_)
        # else:
        #     if len(lieder_existed_position_tickets) > 0:
        #         lieder_existed_position_tickets = []
        lieder_positions = input_positions

        # POST positions
        for position in lieder_positions:
            await send_position(position)

        print(
            f'\nLIEDER {terminal.login} [{Terminal.get_account_currency()}] - {len(lieder_positions)} positions :',
            datetime.now().replace(microsecond=0),
            ' [EURUSD', settings.EURUSD, ': USDRUB', settings.USDRUB, ': EURRUB', str(round(settings.EURRUB, 3)) + ']')
        await asyncio.sleep(sleep)


if __name__ == '__main__':
    get_settings()
    if not is_init_data_valid(init_data):
        await send_comment('Неверные данные инициализации')
        exit()
    terminal = Terminal(login=init_data['login'],
                        password=init_data['password'],
                        server=init_data['server'],
                        path=init_data['path'])
    if not terminal.init_mt():
        await send_comment('Ошибка инициализации лидера')
        exit()

    event_loop = asyncio.new_event_loop()
    event_loop.create_task(update_lieder_info())
    event_loop.run_forever()
