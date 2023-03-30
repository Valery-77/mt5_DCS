import asyncio
from datetime import datetime

import settings
from http_commands import send_comment
from terminal import Terminal

terminal: Terminal
lieder_existed_position_tickets = []
positions_for_none_reopen = []
event_loop = asyncio.Event()  # init async event


async def update_lieder_info(sleep=settings.sleep_lieder_update):
    global lieder_existed_position_tickets, positions_for_none_reopen
    while True:
        lieder_balance = terminal.get_balance()
        lieder_equity = terminal.get_equity()
        input_positions = Terminal.get_positions(only_own=False)

        if len(lieder_existed_position_tickets) == 0:
            for _ in input_positions:
                lieder_existed_position_tickets.append(_.ticket)

        lieder_positions = []
        if source['investors'][0]['reconnected'] == 'Не переоткрывать':
            for _ in input_positions:
                if _.ticket not in lieder_existed_position_tickets:
                    lieder_positions.append(_)
        else:
            if len(lieder_existed_position_tickets) > 0:
                lieder_existed_position_tickets = []
            lieder_positions = input_positions

        # POST positions

        print(
            f'\nLIEDER {terminal.login} [{Terminal.get_account_currency()}] - {len(lieder_positions)} positions :',
            datetime.now().replace(microsecond=0),
            ' [EURUSD', settings.EURUSD, ': USDRUB', settings.USDRUB, ': EURRUB', str(round(settings.EURRUB, 3)) + ']')
        await asyncio.sleep(sleep)


if __name__ == '__main__':
    terminal = Terminal(login=66587203, password='3hksvtko', server='MetaQuotes-Demo',
                        path=r'C:\Program Files\MetaTrader 5\terminal64.exe')
    if not terminal.init_mt():
        await send_comment('Ошибка инициализации лидера')
        exit()

    event_loop = asyncio.new_event_loop()
    event_loop.create_task(update_lieder_info())
    event_loop.run_forever()
