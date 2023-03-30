import asyncio
from datetime import datetime
from math import fabs

import aiohttp
import requests

import deal_comment
from deal_comment import DealComment
import settings
from http_commands import send_comment
from linked_positions import LinkedPositions
from terminal import Terminal

terminal: Terminal


async def disable_dcs(investor):
    async with aiohttp.ClientSession() as session:
        investor_id = -1
        # for _ in source['investors']:
        #     if _['login'] == investor['login']:
        #         investor_id = source['investors'].index(_)
        #         break
        # if investor_id < 0:
        #     return
        id_shift = '_' + str(investor_id + 1)
        url = settings.host + 'last'
        response = requests.get(url).json()[0]
        numb = response['id']
        url = settings.host + f'patch/{numb}/'
        name = "access" + id_shift
        async with session.patch(url=url, data={name: False}) as resp:
            await resp.json()


async def check_connection_exchange(investor):
    close_reason = None
    try:
        if investor['api_key_expired'] == "Да":
            close_reason = '04'
            # force_close_all_positions(investor=investor, reason=close_reason)
        elif investor['no_exchange_connection'] == 'Да':
            close_reason = '05'
            # force_close_all_positions(investor=investor, reason=close_reason)
        if close_reason:
            await send_comment(comment=deal_comment.reasons_code[close_reason])
    except Exception as e:
        print("Exception in patching_connection_exchange:", e)
    return True if close_reason else False


async def check_notification(investor):
    if investor['notification'] == 'Да':
        await send_comment('Вы должны оплатить вознаграждение')
        return True
    return False


async def execute_conditions(investor):
    if investor['disconnect'] == 'Да':
        await send_comment('Инициатор отключения: ' + investor['shutdown_initiator'])

        if Terminal.get_investors_positions_count(investor=investor, only_own=True) == 0:  # если нет открытых сделок
            await disable_dcs(investor)

        if investor['open_trades_disconnect'] == 'Закрыть':  # если сделки закрыть
            Terminal.force_close_all_positions(investor)
            await disable_dcs(investor)

        elif investor['accompany_transactions'] == 'Нет':  # если сделки оставить и не сопровождать
            await disable_dcs(investor)


async def check_stop_limits(investor):
    """Проверка стоп-лимита по проценту либо абсолютному показателю"""
    start_balance = investor['investment_size']
    if start_balance <= 0:
        start_balance = 1
    limit_size = investor['stop_value']
    calc_limit_in_percent = True if investor['stop_loss'] == 'Процент' else False
    history_profit = Terminal.get_history_profit()
    current_profit = Terminal.get_positions_profit()
    # SUMM TOTAL PROFIT
    if history_profit is None or current_profit is None:
        return
    close_positions = False
    total_profit = history_profit + current_profit
    print(f' - {investor["login"]} [{investor["currency"]}] - {len(Terminal.get_positions())} positions. Access:',
          investor['dcs_access'], end='')
    print('\t', 'Прибыль' if total_profit >= 0 else 'Убыток', 'торговли c', settings.start_date,
          ':', round(total_profit, 2), investor['currency'],
          '{curr.', round(current_profit, 2), ': hst. ' + str(round(history_profit, 2)) + '}')
    # CHECK LOST SIZE FOR CLOSE ALL
    if total_profit < 0:
        if calc_limit_in_percent:
            current_percent = fabs(total_profit / start_balance) * 100
            if current_percent >= limit_size:
                close_positions = True
        elif fabs(total_profit) >= limit_size:
            close_positions = True
        # CLOSE ALL POSITIONS
        active_positions = Terminal.get_positions()
        if close_positions and len(active_positions) > 0:
            print('     Закрытие всех позиций по условию стоп-лосс')
            await send_comment('Закрытие всех позиций по условию стоп-лосс. Убыток торговли c' + str(
                settings.start_date.replace(microsecond=0)) + ':' + str(round(total_profit, 2)))
            for act_pos in active_positions:
                if act_pos.magic == terminal.MAGIC:
                    Terminal.close_position(investor)
            if investor['open_trades'] == 'Закрыть и отключить':
                await disable_dcs(investor)


def synchronize_positions_volume(investor):
    try:
        investors_balance = investor['investment_size']
        global old_investors_balance
        login = investor.get("login")
        if login not in old_investors_balance:
            old_investors_balance[login] = investors_balance
        if "Корректировать объем" in (investor["recovery_model"], investor["buy_hold_model"]):
            if investors_balance != old_investors_balance[login]:
                volume_change_coefficient = investors_balance / old_investors_balance[login]
                if volume_change_coefficient != 1.0:
                    investors_positions_table = LinkedPositions.get_linked_positions_table()
                    for _ in investors_positions_table:
                        decimals = Terminal.get_volume_decimals(_.symbol)
                        volume = _.volume
                        new_volume = round(volume_change_coefficient * volume, decimals)
                        if volume != new_volume:
                            _.modify_volume(new_volume)
                old_investors_balance[login] = investors_balance
    except Exception as e:
        print("Exception in synchronize_positions_volume():", e)


def synchronize_positions_limits(lieder_positions):
    """Изменение уровней ТП и СЛ указанной позиции"""
    for l_pos in lieder_positions:
        l_tp = Terminal.get_pos_pips_tp(l_pos)
        l_sl = Terminal.get_pos_pips_sl(l_pos)
        if l_tp > 0 or l_sl > 0:
            for i_pos in Terminal.get_positions():
                request = []
                new_comment_str = comment = ''
                if DealComment.is_valid_string(i_pos.comment):
                    comment = DealComment().set_from_string(i_pos.comment)
                    comment.reason = '09'
                    new_comment_str = comment.string()
                if comment.lieder_ticket == l_pos.ticket:
                    i_tp = Terminal.get_pos_pips_tp(i_pos)
                    i_sl = Terminal.get_pos_pips_sl(i_pos)
                    sl_lvl = tp_lvl = 0.0
                    decimals = Terminal.get_symbol_decimals(i_pos.symbol)
                    if i_pos.type == Terminal.position_type_buy():
                        sl_lvl = i_pos.price_open - l_sl * decimals
                        tp_lvl = i_pos.price_open + l_tp * decimals
                    elif i_pos.type == Terminal.position_type_sell():
                        sl_lvl = i_pos.price_open + l_sl * decimals
                        tp_lvl = i_pos.price_open - l_tp * decimals
                    if i_tp != l_tp or i_sl != l_sl:
                        request = {
                            "action": Terminal.trade_action_sltp(),
                            "position": i_pos.ticket,
                            "symbol": i_pos.symbol,
                            "sl": sl_lvl,
                            "tp": tp_lvl,
                            "magic": Terminal.MAGIC,
                            "comment": new_comment_str
                        }
                if request:
                    result = Terminal.send_order(request)
                    print('Лимит изменен:', result)


def check_transaction(investor, lieder_position):
    """Проверка открытия позиции"""
    price_refund = True if investor['price_refund'] == 'Да' else False
    if not price_refund:  # если не возврат цены
        timeout = investor['waiting_time'] * 60
        deal_time = int(lieder_position.time_update - datetime.utcnow().timestamp())  # get_time_offset(investor))
        curr_time = int(datetime.timestamp(datetime.utcnow().replace(microsecond=0)))
        delta_time = curr_time - deal_time
        if delta_time > timeout:  # если время больше заданного
            # print('Время истекло')
            return False

    transaction_type = 0
    if investor['ask_an_investor'] == 'Плюс':
        transaction_type = 1
    elif investor['ask_an_investor'] == 'Минус':
        transaction_type = -1
    deal_profit = lieder_position.profit
    if transaction_type > 0 > deal_profit:  # если открывать только + и профит < 0
        return False
    if deal_profit > 0 > transaction_type:  # если открывать только - и профит > 0
        return False

    transaction_plus = investor['deal_in_plus']
    transaction_minus = investor['deal_in_minus']
    price_open = lieder_position.price_open
    price_current = lieder_position.price_current

    res = None
    if lieder_position.type == 0:  # Buy
        res = (price_current - price_open) / price_open * 100  # Расчет сделки покупки по формуле
    elif lieder_position.type == 1:  # Sell
        res = (price_open - price_current) / price_open * 100  # Расчет сделки продажи по формуле
    return True if res is not None and transaction_plus >= res >= transaction_minus else False  # Проверка на заданные отклонения


def multiply_deal_volume(investor, lieder_position, lieder_balance, lieder_equity):
    """Расчет множителя"""
    lieder_balance_value = lieder_balance if investor['multiplier'] == 'Баланс' else lieder_equity
    symbol = lieder_position.symbol
    lieder_volume = lieder_position.volume
    multiplier = investor['multiplier_value']
    investment_size = investor['investment_size']
    get_for_balance = True if investor['multiplier'] == 'Баланс' else False
    if get_for_balance:
        ext_k = (investment_size + Terminal.get_history_profit()) / lieder_balance_value
    else:
        ext_k = (
                        investment_size + Terminal.get_history_profit() + Terminal.get_positions_profit()) / lieder_balance_value
    try:
        decimals = Terminal.get_volume_decimals(symbol)
    except AttributeError:
        decimals = 2
    if investor['changing_multiplier'] == 'Нет':
        result = round(lieder_volume * ext_k, decimals)
    else:
        result = round(lieder_volume * multiplier * ext_k, decimals)
    return result


def get_currency_coefficient(investor):
    global EURUSD, EURRUB, USDRUB
    lid_currency = source['lieder']['currency']
    inv_currency = investor['currency']
    eurusd = usdrub = eurrub = -1

    usdrub = Terminal.get_price_bid('USDRUB')
    eurusd = Terminal.get_price_bid('EURUSD')
    eurrub = usdrub * eurusd

    if eurusd > 0:
        EURUSD = eurusd
    if usdrub > 0:
        USDRUB = usdrub
    if eurrub > 0:
        EURRUB = eurrub
    currency_coefficient = 1
    try:
        if lid_currency == inv_currency:
            currency_coefficient = 1
        elif lid_currency == 'USD':
            if inv_currency == 'EUR':
                currency_coefficient = 1 / eurusd
            elif inv_currency == 'RUB':
                currency_coefficient = usdrub
        elif lid_currency == 'EUR':
            if inv_currency == 'USD':
                currency_coefficient = eurusd
            elif inv_currency == 'RUB':
                currency_coefficient = eurrub
        elif lid_currency == 'RUB':
            if inv_currency == 'USD':
                currency_coefficient = 1 / usdrub
            elif inv_currency == 'EUR':
                currency_coefficient = 1 / eurrub
    except Exception as e:
        print('Except in get_currency_coefficient()', e)
        currency_coefficient = 1
    return currency_coefficient


# async def open_position(investor, symbol, deal_type, lot, sender_ticket: int, tp=0.0, sl=0.0):
#     """Открытие позиции"""
#     try:
#         point = Terminal.get_symbol_decimals(symbol=symbol)
#         price = tp_in = sl_in = 0.0
#         if deal_type == 0:  # BUY
#             deal_type = Terminal.order_type_buy()
#             price = Terminal.get_price_ask(symbol)
#         if tp != 0:
#             tp_in = price + tp * point
#         if sl != 0:
#             sl_in = price - sl * point
#         elif deal_type == 1:  # SELL
#             deal_type = Terminal.order_type_sell()
#             price = Terminal.get_price_bid(symbol)
#             if tp != 0:
#                 tp_in = price - tp * point
#             if sl != 0:
#                 sl_in = price + sl * point
#     except AttributeError:
#         return {'retcode': -200}
#     comment = DealComment()
#     comment.lieder_ticket = sender_ticket
#     comment.reason = '01'
#     request = {
#         "action": Terminal.trade_action_deal(),
#         "symbol": symbol,
#         "volume": lot,
#         "type": deal_type,
#         "price": price,
#         "sl": sl_in,
#         "tp": tp_in,
#         "deviation": Terminal.DEVIATION,
#         "magic": Terminal.MAGIC,
#         "comment": comment.string(),
#         "type_time": Terminal.order_tyme_gtc(),
#         "type_filling": Terminal.order_filling_fok(),
#     }
#     checked_request = await edit_volume_for_margin(investor, request)  # Проверка и расчет объема при недостатке маржи
#     if not checked_request:
#         return {'retcode': -100}
#     elif checked_request == -1:
#         # await set_comment('Уменьшите множитель или увеличите сумму инвестиции')
#         return {'retcode': -800}
#     elif checked_request != 'EMPTY_REQUEST' and checked_request != 'MORE_THAN_MAX_VOLUME':
#         result = Mt.order_send(checked_request)
#         return result


async def execute_investor(investor, lieder_positions, lieder_balance, lieder_equity):
    if investor['blacklist'] == 'Да':
        print(investor['login'], 'in blacklist')
        return
    if await check_notification(investor):
        print(investor['login'], 'not pay - notify')
        return
    if await check_connection_exchange(investor):
        print(investor['login'], 'API expired or Broker disconnected')
        return
    # synchronize = True if investor['deals_not_opened'] == 'Да' or investor['synchronize_deals'] == 'Да' else False
    # if investor['synchronize_deals'] == 'Да':  # если "синхронизировать"
    #     await disable_synchronize(synchronize)
    # if not synchronize:
    #     return

    # init_res = init_mt(init_data=investor)
    # if not init_res:
    #     await set_comment('Ошибка инициализации инвестора ' + str(investor['login']))
    #     return

    if investor['dcs_access']:
        await execute_conditions(investor=investor)  # проверка условий кейса закрытия
    if investor['dcs_access']:
        await check_stop_limits(investor=investor)  # проверка условий стоп-лосс
    if investor['dcs_access']:

        synchronize_positions_volume(investor)  # коррекция объемов позиций
        synchronize_positions_limits(investor)  # коррекция лимитов позиций

        for pos_lid in lieder_positions:
            inv_tp = Terminal.get_pos_pips_tp(pos_lid)
            inv_sl = Terminal.get_pos_pips_sl(pos_lid)
            if not Terminal.is_position_opened(pos_lid, investor):
                ret_code = None
                if check_transaction(investor=investor, lieder_position=pos_lid):
                    volume = multiply_deal_volume(investor, lieder_position=pos_lid, lieder_balance=lieder_balance,
                                                  lieder_equity=lieder_equity)

                    decimals = Terminal.get_volume_decimals(pos_lid.symbol)
                    volume = round(volume / get_currency_coefficient(investor), decimals)
                    response = await Terminal.open_position(investor=investor, symbol=pos_lid.symbol,
                                                            deal_type=pos_lid.type,
                                                            lot=volume, sender_ticket=pos_lid.ticket,
                                                            tp=inv_tp, sl=inv_sl)
                    if response:
                        try:
                            ret_code = response.retcode
                        except AttributeError:
                            ret_code = response['retcode']
                if ret_code:
                    msg = str(investor['login']) + ' ' + Terminal.send_retcodes[ret_code][1]  # + ' : ' + str(ret_code)
                    if ret_code != 10009:  # Заявка выполнена
                        await send_comment('\t' + msg)
                    print(msg)
        # else:
        #     set_comment('Не выполнено условие +/-')

    # закрытие позиций от лидера
    if (investor['dcs_access'] or  # если сопровождать сделки или доступ есть
            (not investor['dcs_access'] and investor['accompany_transactions'] == 'Да')):
        Terminal.close_positions_by_lieder(investor)

    # Mt.shutdown()


if __name__ == '__main__':
    terminal = Terminal(login=66587203, password='3hksvtko', server='MetaQuotes-Demo',
                        path=r'C:\Program Files\MetaTrader 5\terminal64.exe')
    if not terminal.init_mt():
        await send_comment('Ошибка инициализации лидера')
        exit()

    event_loop = asyncio.new_event_loop()
    event_loop.create_task(execute_investor())
    event_loop.run_forever()
