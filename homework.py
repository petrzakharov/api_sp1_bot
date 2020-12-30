import logging
import os
import time

import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')  # noqa
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or '12345:abcdef'
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PRAKTIKUM_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'  # noqa
PRAKTIKUM_OAUTH = {'Authorization': 'OAuth ' + PRAKTIKUM_TOKEN}  # noqa
TG_BOT = Bot(token=TELEGRAM_TOKEN)

MESSAGES = {'statuses': {'rejected': 'К сожалению в работе нашлись ошибки.',
                         'approved': ('Ревьюеру всё понравилось, '
                                      'можно приступать к следующему уроку.'),
                         'default_error': 'Невозможно получить информацию'},
            'success_message': 'У вас проверили работу "{name}"!\n\n{status}'
            }


def parse_homework_status(homework):
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = MESSAGES['statuses'][homework_status]
        logging.info(f'Статус работы {homework_status}, вердикт смапплен')
    except KeyError as e:
        logging.error(f'В апи практикум поменялся формат данных, {e}')
        return MESSAGES['statuses']['default_error']
    return MESSAGES['success_message'].format(name=homework_name,
                                              status=verdict)


def get_homework_statuses(current_timestamp):
    params = {'from_date': current_timestamp}
    logging.info(f'Запрос данных от практикум')
    try:
        homework_statuses = requests.get(PRAKTIKUM_URL,
                                         params=params,
                                         headers=PRAKTIKUM_OAUTH)
    except requests.exceptions.RequestException as e:
        logging.critical(f'Запрос вернулся с ошибкой {e}')
    return homework_statuses.json()


def send_message(message, bot_client=TG_BOT):
    logging.info(f'Попытка отправить сообщение: {message}, chat_id {CHAT_ID} ')
    return bot_client.send_message(CHAT_ID, message)


def main():
    current_timestamp = 0
    #current_timestamp = int(time.time())  # начальное значение timestamp
    while True:
        try:
            new_homework = get_homework_statuses(
                current_timestamp)  # получает json
            logging.info('Яндекс практикум отдал ответ')
            if new_homework.get('homeworks'):
                send_message(
                    parse_homework_status(new_homework.get('homeworks')[0]))
                logging.info('Бот успешно отправил сообщение')
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            logging.info(f'Смена времени отсчета. Новая итерация.')
            time.sleep(300)
        except Exception as e:
            print(f'Бот столкнулся с ошибкой: {e}')
            logging.critical(e)
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=__file__.split('.')[0] + '_log.log',
        format='%(asctime)s:%(levelname)s:%(funcName)s %(message)s',
        filemode='w'
    )
    main()
