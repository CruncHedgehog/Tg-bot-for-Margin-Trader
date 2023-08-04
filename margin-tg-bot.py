from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


from config_file import TG_TOKEN
from redis_requests import *


import traceback


bot = Bot(token=TG_TOKEN)
dp = Dispatcher(bot)    


async def delete_call_message(call):
    try:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        print(f"Could NOT delete message with button: {traceback.format_exc()}")


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb1 = KeyboardButton('/open')
    kb2 = KeyboardButton('/close')
    kb.add(kb1).insert(kb2)
    txt = get_message('start').format(message.from_user.id)
    await bot.send_message(chat_id=message.chat.id, text=txt, reply_markup=kb)


@dp.message_handler(commands=['open'])
async def open_command(message: types.Message):
    us_id = get_user_config(message.from_user.id)
    unactive_strats = get_openable_strats(message.from_user.id)
    buttons = [
        InlineKeyboardButton(text=f'▶️ {text} – {data}', callback_data="open|"+data)
        for data, text in unactive_strats.items()
    ]
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    if us_id:
        if unactive_strats == {}:
            await bot.send_message(chat_id=message.chat.id, text=get_message('nothing_to_open'))
        else:   
            await bot.send_message(chat_id=message.chat.id, text=get_message('open'), reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=message.chat.id, text=get_message('user_unknown')) 


@dp.callback_query_handler(lambda x: x.data[:5] == 'open|')
async def open_strat_side(callback_query: types.CallbackQuery):
    print(f"callback: {callback_query.data}")
    strat_id = callback_query.data.split('|')[1]
    ikb = InlineKeyboardMarkup(row_width=2)
    ib1 = InlineKeyboardButton(text='⬆️ LONG', callback_data='open>long|'+strat_id)
    ib2 = InlineKeyboardButton(text='⬇️ SHORT', callback_data='open>short|'+strat_id)
    ikb.add(ib1, ib2)
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id, text=get_message('select_side'), reply_markup=ikb)


@dp.callback_query_handler(lambda x: x.data[:5] == 'open>')
async def open_strat_sure(callback_query: types.CallbackQuery):
    print(f"callback: {callback_query.data}")
    unactive_strats = get_openable_strats(callback_query.from_user.id)
    strat_id = callback_query.data.split('|')[1]
    side = callback_query.data.split('|')[0].split(">")[1]
    coin = unactive_strats[strat_id]
    ikb = InlineKeyboardMarkup(row_width=2)
    ib1 = InlineKeyboardButton(text='✅ Да', callback_data=f'deal>{side}>{strat_id}')
    ib2 = InlineKeyboardButton(text='❌ Нет', callback_data='no_deal')
    ikb.add(ib1, ib2)
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id,
                           text=get_message('sure_open').format(coin, side),
                           reply_markup=ikb)


@dp.callback_query_handler(lambda x: x.data[:7] == 'no_deal')
async def no_deal(callback_query: types.CallbackQuery):
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id, text='Ну и ладненько!')


@dp.callback_query_handler(lambda x: x.data[:5] == 'deal>')
async def deal(callback_query: types.CallbackQuery):
    print(f"callback: {callback_query.data}")
    unactive_strats = get_openable_strats(callback_query.from_user.id)
    strat_id = callback_query.data.split('>')[2]
    side = callback_query.data.split('>')[1]
    coin = unactive_strats[strat_id]
    dictionary_with_deals = {'user_id': callback_query.from_user.id,
                             'bot_id': strat_id,
                             'strategy_id': strat_id,
                             'side': side,
                             'source': 'Telegram'}

    pushing_deals(callback_query.from_user.id, dictionary_with_deals)
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id, text=get_message('saved_open').format(coin, side))
    

@dp.message_handler(commands=['close'])
async def close_command(message: types.Message):
    us_id = get_user_config(message.from_user.id)
    closable_strats = get_closable_strats(message.from_user.id)
    if closable_strats:
        buttons = [
            InlineKeyboardButton(text=f'❌ {text} - {data}', callback_data='close|'+data)
            for data, text in closable_strats.items() 
        ]
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
    if us_id:
        if not closable_strats:
            await bot.send_message(chat_id=message.chat.id, text=get_message('nothing_to_close'))
        else:
            await bot.send_message(chat_id=message.chat.id, text=get_message('close'), reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=message.chat.id, text=get_message('user_unknown'))


@dp.callback_query_handler(lambda x: x.data[:6] == 'close|')
async def close_strat(callback_query: types.CallbackQuery):
    print(f"callback: {callback_query.data}")

    closable_strats = get_closable_strats(callback_query.from_user.id)
    strat_id = callback_query.data.split('|')[1]
    coin = closable_strats[strat_id]
    ikb = InlineKeyboardMarkup(row_width=2)
    ib1 = InlineKeyboardButton(text='✅ Да', callback_data='close>'+strat_id)
    ib2 = InlineKeyboardButton(text='❌ Нет', callback_data='no_deal')
    ikb.add(ib1, ib2)
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id, text=get_message('sure_close').format(coin), reply_markup=ikb)


@dp.callback_query_handler(lambda x: x.data[:6] == 'close>')
async def closing_the_deal(callback_query: types.CallbackQuery):
    print(f"callback: {callback_query.data}")

    closable_strats = get_closable_strats(callback_query.from_user.id)
    strat_id = callback_query.data.split('>')[1]
    coin = closable_strats[strat_id]
    dictionary_with_closing_deals = {'user_id': callback_query.from_user.id,
                                     'bot_id': strat_id,
                                     'strat_id': strat_id,
                                     'source': 'Telegram'}
    pushing_closing_deals(callback_query.from_user.id, dictionary_with_closing_deals)
    await delete_call_message(callback_query)
    await bot.send_message(callback_query.from_user.id, text=get_message('saved_close').format(coin))


if __name__ == '__main__':
    print('Bot has successfully started!')
    executor.start_polling(dp)
