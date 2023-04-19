import asyncio
import json
from datetime import datetime

import requests

import settings
from db_interface import DBInterface
from http_commands import patch
from terminal import Terminal

terminal: Terminal
event_loop = asyncio.Event()  # init async event
init_data = {}
db = DBInterface()
account_id = -1
leader_id = 0
max_balance = 0
terminal_path = r'C:\Program Files\MetaTrader 5\terminal64.exe'
host = settings.host


async def send_trade_state(balance, equity):
    url = host + f'account/patch/{account_id}'
    data = {'balance': balance,
            'equity': equity,
            }
    await patch(url=url, data=json.dumps(data))


async def update_leader_info(sleep=settings.sleep_leader_update):
    global max_balance
    while True:
        leader_balance = terminal.get_balance()
        leader_equity = terminal.get_equity()
        await send_trade_state(leader_balance, leader_equity)
        if leader_balance > max_balance:
            max_balance = leader_balance
        active_db_positions = await db.get_db_positions(leader_id)
        active_db_tickets = [position['ticket'] for position in active_db_positions]
        terminal_positions = Terminal.get_positions(only_own=False)
        terminal_tickets = [position.ticket for position in terminal_positions]
        for position in active_db_positions:
            tick = Terminal.copy_rates_range(position['symbol'], position['time'],
                                             Terminal.symbol_info_tick(position['symbol']).time)
            print(tick)
            if position['ticket'] not in terminal_tickets:
                await db.disable_position(position['ticket'])
                await db.send_history_position(position['ticket'], max_balance, this_is_leader=True)
        for position in terminal_positions:
            if position.ticket not in active_db_tickets:
                await db.send_position(position)
            else:
                await db.update_position(position)

        print(
            f'{terminal.login} [{Terminal.get_account_currency()}] - {len(terminal_positions)} positions :',
            datetime.now().replace(), "- LEADER")
        await asyncio.sleep(sleep)


if __name__ == '__main__':
    account_id = db.get_account_id()
    init_data = db.get_init_data(host=host, account_idx=account_id, terminal_path=terminal_path)
    print(init_data)
    url_lid = host + f'leader_id/get/{account_id}'
    response = requests.get(url=url_lid)
    leader_id = response.json()

    if not Terminal.is_init_data_valid(init_data):
        exit()
    terminal = Terminal(login=int(init_data['login']),
                        password=init_data['password'],
                        server=init_data['server'],
                        path=init_data['path'],
                        start_date=datetime.now())
    if not terminal.init_mt():
        print('Ошибка инициализации лидера', init_data)
        exit()
    db.initialize(init_data=init_data, leader_id=leader_id, account_id=account_id, host=host,
                  leader_currency=Terminal.get_account_currency())

    db.send_currency()

    event_loop = asyncio.new_event_loop()
    event_loop.create_task(update_leader_info())
    event_loop.run_forever()
