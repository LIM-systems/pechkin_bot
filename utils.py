import requests
from config import *
from random import randint
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiogram import types


# проверка числиться ли эта почта среди сотрудников действующих
async def check_user_in_yandex(email):
    '''Получим список всех пользователей из YandexAPI '''
    params = {
        # Описание параметров запроса:
        # https://yandex.ru/dev/api360/doc/ref/UserService/UserService_List.html
        # срок жизни токена 1 год (истечет 01.09.2024)
        # обновить токен
        # https://oauth.yandex.ru/authorize?response_type=token&client_id=<идентификатор приложения>
        # 'fields': 'is_enabled,email',
        'perPage': 1000,
        'page': 1
    }
    headers = {
        'Authorization': 'OAuth ' + YA_TOKEN,
        'Accept': 'application/json'
    }
    response = requests.get(
        f'{YA_API_URL}/directory/v1/org/{YA_ORG_ID}/users?',
        params=params,
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    response_data = response.json()
    for user in response_data.get('users'):
        if user.get('email') == email:
            return True
    return False


# отправка проверочного кода на почту
async def send_code(email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = email
    msg['Subject'] = 'Печкин_bot. Проверочный код'
    code = randint(100000, 999999)
    message_text = f'Ваш проверочный код: {code}'
    message_text = MIMEText(message_text, 'html', 'utf-8')
    msg.attach(message_text)
    smtp_server = EMAIL_SERVER
    smtp_port = EMAIL_PORT

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        server.sendmail(EMAIL_USER, [email], msg.as_string().encode('utf-8'))

        server.quit()
        return code
    except Exception as e:
        print(e)


# главное меню
async def show_main_menu(msg):
    keyboard = types.InlineKeyboardMarkup()\
        .add(types.InlineKeyboardButton('Внести предложение', callback_data='offer_button_main_menu'))\
        .add(types.InlineKeyboardButton('Задать вопрос', callback_data='question_button_main_menu'))\
        .add(types.InlineKeyboardButton('Оставить жалобу', callback_data='complaint_button_main_menu'))
    await msg.answer('Какую заметку Вы хотите отправить?', reply_markup=keyboard)
