from config_file import *
import redis
import json
import time


known_userids_by_tgid = {}

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DBNUM, password=REDIS_PWD)
try:
    x = r.keys()
except:
    print('Не смог подключиться к базе Redis, выхожу.')
    exit()


def get_user_id(tg_id):
    if tg_id in known_userids_by_tgid:
        timestamp = known_userids_by_tgid[tg_id][1]
        if time.time() - timestamp <= FIVE_MINUTES:
            return known_userids_by_tgid[tg_id][0]
    else:
        for user_id in r.hkeys('user_configs'):
            uconf = r.hget('user_configs', user_id)
            if uconf:
                try:
                    uconf = json.loads(uconf)
                except:
                    continue
                if uconf.get('tg_id') == str(tg_id) or uconf.get('tg_id') == tg_id:
                    known_userids_by_tgid[tg_id] = (user_id.decode('utf-8'), time.time())
                    return user_id.decode('utf-8')
    return None


def get_user_config(tg_id):
    try:
        user_id = get_user_id(tg_id)
        uconf = r.hget('user_configs', user_id)
        uconf = json.loads(uconf)
        return uconf
    except:
        uconf = None
    return uconf


def get_message(x):
    while True:
        try:
            with open('messages.json', 'r', encoding='utf-8') as f:
                messages = json.load(f) 
            return messages[x] 
        except:
            time.sleep(0.1)


def get_closable_strats(tg_id):
    user_id = get_user_id(tg_id)
    closable_strats = {}
    user_traders = r.hget('traders', user_id)
    if user_traders:
        user_traders = json.loads(user_traders)
        if 'active_strat' in user_traders:
            for strat_id, strat_dict in user_traders['active_strat'].items():
                closable_strats[strat_id] = strat_dict['symbol']
    return closable_strats


def get_openable_strats(tg_id):
    user_config = get_user_config(tg_id)
    unactive_strats = {}
    if user_config:
        current_trading_strats = get_closable_strats(tg_id)
        if 'strategies' in user_config.keys():
            for strat_id, strat_dict in user_config['strategies'].items():
                if strat_dict['enabled']:
                    if strat_id not in current_trading_strats:
                        unactive_strats[strat_id] = strat_dict['symbol']
    return unactive_strats


def pushing_deals(tg_id, dictionary_with_deal):
    user_id = get_user_id(tg_id)
    r.lpush(f'signals_{user_id}', json.dumps(dictionary_with_deal))


def pushing_closing_deals(tg_id, dictionary_with_closing_deals):
    user_id = get_user_id(tg_id)
    r.lpush(f'exit_signals_{user_id}', json.dumps(dictionary_with_closing_deals))
