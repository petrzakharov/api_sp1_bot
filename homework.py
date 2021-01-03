import logging
import os
import time

import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or '12345:abcdef'
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PRAKTIKUM_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
PRAKTIKUM_OAUTH = {'Authorization': 'OAuth ' + PRAKTIKUM_TOKEN}
telegram_bot = Bot(token=TELEGRAM_TOKEN)

STATUS_MESSAGES = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'approved': (
        'Ревьюеру всё понравилось, можно приступать к следующему уроку.'
    )
}

SUCCESS_MESSAGE = 'У вас проверили работу "{name}"!\n\n{status}'
ERROR_MESSAGE = ('Запрос к апи вернулся с ошибкой. {description} '
                 'URL="{PRAKTIKUM_URL}", params="{params}"')
LOGGING_SEND_MESSAGE = ('Попытка отправить сообщение: "{message}", ' 
                        'chat_id "{chat_id}"')


def parse_homework_status(homework):
    name = homework['homework_name']
    status = homework['status']
    if status not in STATUS_MESSAGES:
        raise KeyError(f'Работа имеет неизвестный статус, {status}')
    verdict = STATUS_MESSAGES[status]
    return SUCCESS_MESSAGE.format(name=name, status=verdict)


def get_homework_statuses(current_timestamp):
    params = {'from_date': current_timestamp}
    logging.info(f'Запрос данных апи практикум')
    try:
        response = requests.get(PRAKTIKUM_URL,
                                params=params,
                                headers=PRAKTIKUM_OAUTH)
    except requests.exceptions.RequestException as exception:
        # нормально ли делать except, а после raise ошибки,
        # но уже с кастомным соообщением?
        raise Exception(f'Ошибка запроса к апи, {exception}')
    else:
        data = response.json()
        if 'code' in data or 'error' in data:
            description = data.get('message', 'Сообщение отсутствует.')
            raise Exception(ERROR_MESSAGE.format(description=description,
                                                 PRAKTIKUM_URL=PRAKTIKUM_URL,
                                                 params=params))
        if 'homeworks' not in data:
            raise KeyError('В ответе апи нет данных о работе.')
    return data


def send_message(message, bot_client=telegram_bot):
    logging.info(LOGGING_SEND_MESSAGE.format(message=message, chat_id=CHAT_ID))
    return bot_client.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())  # начальное значение timestamp
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
            logging.info(f'Новая итерация проверки ответа апи.')
            time.sleep(300)
        except Exception as e:
            logging.error(e)
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=__file__ + '.log',
        format='%(asctime)s:%(levelname)s:%(funcName)s %(message)s',
        filemode='w'
    )
    main()
