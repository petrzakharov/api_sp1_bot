import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or '12345:abcdef'
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PRAKTIKUM_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
PRAKTIKUM_OAUTH = {'Authorization': 'OAuth ' + PRAKTIKUM_TOKEN}
telegram_bot = Bot(token=TELEGRAM_TOKEN)

STATUS_MESSAGES = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'approved':
        'Ревьюеру всё понравилось, можно приступать к следующему уроку.'
}
SUCCESS_MESSAGE = 'У вас проверили работу "{name}"!\n\n{verdict}'
ERROR_MESSAGES = {
    'api_response':
        'Запрос к апи Яндекс Практикум вернулся с ошибкой. {message} '
        'value="{value}", URL="{url}", '
        'params="{params}", '
        'headers="{headers}"',
    'unknown_status': 'Работа имеет неизвестный статус, {status}',
    'connection':
        'Ошибка запроса к апи. '
        'URL="{url}", '
        'params="{params}", '
        'headers="{headers}"'
}
INFO_MESSAGES = {
    'try_send':
        'Попытка отправить сообщение: "{message}", chat_id "{chat_id}"',
    'praktikum_request': 'Запрос данных апи Яндекс Практикум.',
    'praktikum_response': 'Яндекс Практикум отдал ответ.',
    'success_send': 'Бот успешно отправил сообщение.',
    'new_iteration': 'Новая итерация проверки ответа Яндекс Практикум апи.'
}


def parse_homework_status(homework):
    status = homework.get('status')
    if status not in STATUS_MESSAGES:
        raise ValueError(
            ERROR_MESSAGES['unknown_status'].format(status=status)
        )
    return SUCCESS_MESSAGE.format(
        name=homework['homework_name'],
        verdict=STATUS_MESSAGES[status]
    )


def get_homework_statuses(current_timestamp):
    params = {'from_date': current_timestamp}
    params_request = dict(
        url=PRAKTIKUM_URL,
        params=params,
        headers=PRAKTIKUM_OAUTH
    )
    logging.info(INFO_MESSAGES['praktikum_request'])
    try:
        response = requests.get(**params_request)
    except requests.exceptions.RequestException as exception:
        raise ConnectionError(
            ERROR_MESSAGES['connection'].format(**params_request)
        ) from exception
    homework_data = response.json()
    for key_error in ['code', 'error']:
        if key_error in homework_data:
            message = homework_data.get('message')
            value = homework_data.get(key_error)
            raise RuntimeError(
                ERROR_MESSAGES['api_response'].format(
                    **params_request,
                    message=message,
                    value=value
                ))
    return homework_data


def send_message(message, bot_client=telegram_bot):
    logging.info(
        INFO_MESSAGES['try_send'].format(
            message=message,
            chat_id=CHAT_ID
        ))
    return bot_client.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())
    while True:
        try:
            new_homework = get_homework_statuses(
                current_timestamp)  # получает json
            logging.info(INFO_MESSAGES['praktikum_response'])
            if new_homework.get('homeworks'):
                send_message(
                    parse_homework_status(new_homework.get('homeworks')[0]))
                logging.info(INFO_MESSAGES['success_send'])
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            logging.info(INFO_MESSAGES['new_iteration'])
            time.sleep(300)
        except Exception as exception:
            logging.error(exception)
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=__file__ + '.log',
        format='%(asctime)s:%(levelname)s:%(funcName)s %(message)s',
        filemode='w'
    )
    main()
