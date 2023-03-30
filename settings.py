import asyncio
from datetime import datetime


TIMEOUT_INIT = 60_000  # время ожидания при инициализации терминала (рекомендуемое 60_000 millisecond)
MAGIC = 9876543210  # идентификатор эксперта
DEVIATION = 20  # допустимое отклонение цены в пунктах при совершении сделки
# lieder_balance = 0  # default var
# lieder_equity = 0  # default var
# lieder_positions = []  # default var
lieder_existed_position_tickets = []  # default var
# UTC_OFFSET = datetime.now() - datetime.utcnow()
# SERVER_DELTA_TIME = timedelta(hours=4)
SERVER_TIME_OFFSET_HOURS = 4  # timedelta(hours=4)
old_investors_balance = {}
start_date = datetime.now().replace(microsecond=0)
# trading_event = asyncio.Event()  # init async event

EURUSD = USDRUB = EURRUB = -1
# send_messages = True  # отправлять сообщения в базу
sleep_lieder_update = 1  # пауза для обновления лидера

host = 'https://my.atimex.io:8000/api/demo_mt5/'

source = {
    # 'lieder': {},
    # 'investors': [{}, {}],
    # 'settings': {}
}
