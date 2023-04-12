import json
import math
from datetime import datetime

# from terminal import Terminal
import requests

import settings
from http_commands import patch, get, post
from terminal import Terminal


class DBInterface:
    init_data: dict
    options: dict
    account_id: int
    host: str
    leader_id: int
    leader_balance: float
    leader_equity: float
    leader_currency: str

    __slots__ = ['init_data', 'options', 'account_id', 'host', 'leader_id', 'leader_balance',
                 'leader_equity', 'leader_currency']

    def initialize(self, init_data, account_id, leader_id, host, leader_currency):
        self.init_data = init_data
        self.leader_id = leader_id
        self.account_id = account_id
        self.host = host
        self.leader_currency = leader_currency

    async def update_data(self):
        opt = await self.get_investor_options()
        self.options = opt[-1]
        await self.get_leader_data()

    async def send_history_position(self, position_ticket):
        # 'Slippage %'
        plus_minus_value = self.options['deal_in_plus'] if self.options['deal_in_plus'] \
            else self.options['deal_in_minus']
        #
        history_deals = Terminal.get_history_deals_for_ticket(int(position_ticket))
        deals_time = [deal.time for deal in history_deals]
        # datetime.fromtimestamp(deal.time).strftime('%m/%d/%Y %H:%M:%S')
        deal_duration = deals_time[-1] - deals_time[0]
        # print('---', deals_time)
        # print('duration:', deal_duration)
        deals_price = [deal.price for deal in history_deals]
        digits = Terminal.get_symbol_decimals(history_deals[-1].symbol)
        # print(history_deals[-1].symbol, digits)
        deal_price_change = round(math.fabs(deals_price[-1] - deals_price[0]), digits)
        # print('+++', deals_price)
        # print('delta_price:', deal_price_change)
        position = history_deals[0]
        # print(len(position), position)
        if not position:
            return
        data = {
            'Ticket': position.ticket,
            'Exchange': 'MT5',
            'API Key': self.init_data['login'],
            'Secret Key': self.init_data['password'],
            'Account': self.account_id,
            'Multiplicator': self.options['multiplier_value'],
            'Stop out': self.options['stop_value'],
            'Symbol': position.symbol,
            'Side': 'buy' if position.type == 0 else 'sell' if position.type == 1 else 'not buy or sell',
            'Slippage %': plus_minus_value,
            'Slippage time': self.options['waiting_time'],
            'Size': position.volume * Terminal.get_contract_size(position.symbol) * position.price_open,
            'Lots': position.volume,
            'Lever': '',
            'Balance %': '',
            'Volume %': '',
            'Open Time': position.time,
            'Open Price': position.price_open,
            'Stop loss': position.sl,
            'Take profit': position.tp,
            'Close time': 0,  # int(datetime.now().replace(microsecond=0).timestamp()),  # position.time_close,
            'Close Price': 0.0,
            # Terminal.get_price_bid(position.symbol) if position.type == 0 else
            # Terminal.get_price_ask(position.symbol) if position.type == 1 else 0.0,  # position.price_close,
            'Change_%': '',
            'Gross P&L': '',
            'Fee': '',
            'Swap': '',
            'Costs': '',
            'Net P&L': '',
            'Equity': '',
            'Float P&L': '',
            'Minimum': '',
            'Maximum': '',
            'Magic': position.magic,
            'Comment': position.comment,
        }
        # print(data)

    @staticmethod
    def get_init_data(host, account_idx, terminal_path):
        url = host + f'account/get/{account_idx}'
        init_data = requests.get(url=url).json()[-1]
        init_data['path'] = terminal_path
        return init_data

    async def get_investor_options(self):
        url = self.host + f'option/list/'
        return await get(url=url)
        # return requests.get(url=url).json()[-1]

    async def disable_dcs(self):
        url = self.host + f'account/patch/{self.account_id}/'
        data = {'access': False}
        await patch(url=url, data=json.dumps(data))

    async def get_db_positions(self, id_):
        url = self.host + f'position/list/active/{id_}'
        result = await get(url=url)
        # print(id_, url, result)
        return result

    async def get_leader_data(self):
        url = self.host + f'account/get/{self.leader_id}'
        response = await get(url=url)
        self.leader_balance = response[0]['balance']
        self.leader_equity = response[0]['equity']
        self.leader_currency = response[0]['currency']

    async def send_position(self, position):
        url = self.host + 'position/post'
        data = {
            "account_pk": self.account_id,
            "ticket": position.ticket,
            "time": position.time,
            "time_update": position.time_update,
            "type": position.type,
            "magic": settings.MAGIC,
            "volume": position.volume,
            "price_open": position.price_open,
            "tp": position.tp,
            "sl": position.sl,
            "price_current": position.price_current,
            "symbol": position.symbol,
            "comment": position.comment,
            "profit": position.profit,
            "price_close": 0,
            "time_close": 0,
            "active": True
        }
        print(f'\t-- add position {data["ticket"]}')
        await post(url=url, data=json.dumps(data))

    async def update_position(self, position):
        url = self.host + f'position/patch/{self.account_id}/{position.ticket}'
        data = {
            "time_update": position.time_update,
            "volume": position.volume,
            "tp": position.tp,
            "sl": position.sl,
            "profit": position.profit,
            "price_current": position.price_current,
            "comment": position.comment,
        }
        await patch(url=url, data=json.dumps(data))

    async def disable_position(self, position_ticket):
        url = self.host + f'position/patch/{self.account_id}/{position_ticket}'
        data = {
            # "price_close": 0,
            # "time_close": 0,
            "active": False
        }
        # print(self.account_id, url, data)
        print(f'\t-- disable position {position_ticket}')
        await patch(url=url, data=json.dumps(data))
