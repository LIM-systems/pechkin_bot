from aiogram import types
from loader import dp, bot
from config import CHAT_ID
from typing import List
from db.commands import *
from state import User, Dialogue
from aiogram.dispatcher import FSMContext
from utils import check_user_in_yandex, send_code, show_main_menu
from typing import Union


# /start
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    is_auth = await check_auth(msg.chat.id)
    if msg.chat.id != CHAT_ID and not is_auth:
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(
                'Авторизоваться', callback_data='auth_button')
        )
        await msg.answer('''Здравствуйте! Я почтальон Печкин. 
Через меня Вы можете внести предложение, задать вопрос или оставить жалобу. 
Давайте знакомиться.''', reply_markup=keyboard)
    elif msg.chat.id != CHAT_ID:
        await show_main_menu(msg)


# кнопка авторизации
@dp.callback_query_handler(lambda call: call.data == 'auth_button')
@dp.callback_query_handler(lambda call: call.data == 'back_to_email_step_button', state=User.code)
async def start_auth(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer('Введите свой рабочий e-mail')
    await User.email.set()


# сообщение при отправке кода
async def send_code_message(msg: types.Message, text: str) -> None:
    keyboard = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton(
            'Отправить код ещё раз', callback_data='auth_code_repeat_button'),
        types.InlineKeyboardButton(
            'Назад', callback_data='back_to_email_step_button')
    )
    await msg.answer(text, reply_markup=keyboard)


# проверка email и отправка кода авторизации
@dp.message_handler(state=User.email, content_types=['text'])
async def check_email_handler(msg: types.Message, state: FSMContext):
    email = msg.text
    if email.split('@')[1] != 'printgrad.ru':
        await msg.answer('Этот email не подходит')
        return
    is_email_exist = await check_email(email)
    if is_email_exist:
        await msg.answer('Этот email уже зарегистрирован')
        return
    is_worker = await check_user_in_yandex(email)
    if not is_worker:
        await msg.answer('Этот email не найден среди действующих сотрудников')
        return
    del_msg = await bot.send_message(chat_id=msg.chat.id, text='Подождите. Генерирую проверочный код.')
    code = await send_code(email)
    await state.update_data(email=email)
    await state.update_data(code=code)
    await bot.delete_message(chat_id=msg.chat.id, message_id=del_msg.message_id)
    await send_code_message(msg, 'Введите код авторизации, отправленный на указанную почту.')
    await User.code.set()


# повторная отправка кода
@dp.callback_query_handler(lambda call: call.data == 'auth_code_repeat_button', state=User.code)
async def repeat_code(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    state_data = state.get_data()
    email = state_data.get('email')
    del_msg = await bot.send_message(chat_id=call.message.chat.id, text='Подождите. Генерирую проверочный код.')
    code = await send_code(email)
    await state.update_data(code=code)
    await bot.delete_message(chat_id=call.message.chat.id, message_id=del_msg.message_id)
    await send_code_message(call.message, 'Код отправлен повторно.')
    await User.code.set()


# проверка кода и запись в бд
@dp.message_handler(state=User.code, content_types=['text'])
async def check_code_handler(msg: types.Message, state: FSMContext):
    state_data = await state.get_data()
    code = int(msg.text)
    if code != state_data.get('code'):
        await msg.answer('Неверный код')
        return
    email = state_data.get('email')
    tg_id = int(msg.chat.id)
    await add_new_person(tg_id, email)
    await msg.answer('Вы успешно авторизованы!')
    await show_main_menu(msg)
    await state.finish()


# обработка кнопок главного меню
@dp.callback_query_handler(lambda call: call.data.endswith('_button_main_menu'))
async def main_buttons_handler(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    is_worker = await check_auth(call.message.chat.id)
    if not is_worker:
        await call.message.answer('Доступ закрыт. Используйте команду /start .')
        await state.finish()
        return
    text_offer = 'Пожалуйста, внесите свое предложение '
    text_question = 'Пожалуйста, задайте свой вопрос '
    text_complaint = 'Пожалуйста, опишите свою проблему '
    text = 'в любом удобном формате: фото, видео, голосовое сообщение, документ или текстовое сообщение.'
    message_type = call.data.split('_')[0]
    await state.update_data(message_type=message_type)
    match call.data.split('_')[0]:
        case 'offer':
            text = text_offer + text
        case 'question':
            text = text_question + text
        case 'complaint':
            text = text_complaint + text
    keyboard = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(
            'Отмена', callback_data='cancel_button_main_menu')
    )
    await call.message.answer(text, reply_markup=keyboard)
    await Dialogue.message.set()


# отмена отправки сообщения
@dp.callback_query_handler(lambda call: call.data == 'cancel_button_main_menu', state=Dialogue.message)
async def cancel_message(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.finish()
    await show_main_menu(call.message)


# отправка или отмена
async def send_or_cancel(msg: types.Message) -> None:
    keyboard = types.InlineKeyboardMarkup()\
        .add(
        types.InlineKeyboardButton(
            'Отправить', callback_data='send_message_button')
    )\
        .add(
            types.InlineKeyboardButton(
                'Отмена', callback_data='cancel_button_main_menu')
    )
    await msg.answer('Отправить сообщение или желаете что-то добавить?', reply_markup=keyboard)


# получить и записать сообщение
# обработка одинарных сообщений без альбомов
@dp.message_handler(is_media_group=False,
                    content_types=['text', 'audio', 'document', 'sticker',
                                   'photo', 'video', 'voice', 'contact', 'location'],
                    state=Dialogue.message)
async def dialog_handler(msg: types.Message, state: FSMContext):
    is_worker = await check_auth(msg.chat.id)
    if not is_worker:
        await msg.answer('Доступ закрыт. Используйте команду /start .')
        await state.finish()
        return
    state_data = await state.get_data()
    state_message = state_data.get('message')
    caption = msg.caption if msg.caption else None
    message_for_save = {
        'album': False,
        'type': msg.content_type,
        'caption': caption,
    }
    match msg.content_type:
        case 'text':
            message_for_save['content'] = msg.text
        case 'audio':
            message_for_save['content'] = msg.audio.file_id
        case 'document':
            message_for_save['content'] = msg.document.file_id
        case'sticker':
            message_for_save['content'] = msg.sticker.file_id
        case 'photo':
            message_for_save['content'] = msg.photo[-1].file_id
        case 'video':
            message_for_save['content'] = msg.video.file_id
        case 'voice':
            message_for_save['content'] = msg.voice.file_id
        case 'contact':
            message_for_save['content'] = {
                'number': msg.contact.phone_number,
                'name': msg.contact.first_name
            }
        case 'location':
            message_for_save['content'] = str(msg.location.latitude) + \
                ',' + str(msg.location.longitude)

    if state_message:
        state_message.append(message_for_save)
    else:
        state_message = [message_for_save]

    await state.update_data(message=state_message)
    await send_or_cancel(msg)


# обработка сообщений с альбомами
@dp.message_handler(is_media_group=True, content_types=['audio', 'document', 'photo', 'video'],
                    state=Dialogue.message)
async def dialog_handler_media(msg: types.Message, album: List[types.Message], state: FSMContext):
    is_worker = await check_auth(msg.chat.id)
    if not is_worker:
        await msg.answer('Доступ закрыт. Используйте команду /start .')
        await state.finish()
        return
    state_data = await state.get_data()
    state_message = state_data.get('message')
    message_for_save = {
        'album': True,
        'type': msg.content_type,
        'content': []
    }
    for item in album:
        caption = item.caption if item.caption else None
        if msg.content_type == 'photo' or msg.content_type == 'video':
            content = {
                'file': item.photo[-1].file_id if item.photo else item.video.file_id,
                'caption': caption
            }
            message_for_save['content'].append(content)
        else:
            message_for_save['content'].append(item[msg.content_type].file_id)

    if state_message:
        state_message.append(message_for_save)
    else:
        state_message = [message_for_save]

    await state.update_data(message=state_message)
    await send_or_cancel(msg)


# вопрос включить анонимность или нет
@dp.callback_query_handler(lambda call: call.data == 'send_message_button', state=Dialogue.message)
async def is_anonim_handler(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    is_worker = await check_auth(call.message.chat.id)
    if not is_worker:
        await call.message.answer('Доступ закрыт. Используйте команду /start .')
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()\
        .add(types.InlineKeyboardButton('Да', callback_data='anonim_yes_button'))\
        .add(types.InlineKeyboardButton('Нет', callback_data='anonim_no_button'))\
        .add(types.InlineKeyboardButton('Отмена', callback_data='cancel_button_main_menu'))
    await call.message.answer('Желаете ли Вы отправить сообщение анонимно?', reply_markup=keyboard)


# получение имени пользователя
async def get_username(msg: Union[types.Message, types.CallbackQuery]) -> str:
    if not msg.from_user.first_name:
        name = msg.from_user.last_name
    elif not msg.from_user.last_name:
        name = msg.from_user.first_name
    else:
        name = msg.from_user.first_name + " " + msg.from_user.last_name
    return name


# отправка сообщения в чат
@dp.callback_query_handler(lambda call: call.data.startswith('anonim'), state=Dialogue.message)
async def send_message_handler(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    is_worker = await check_auth(call.message.chat.id)
    if not is_worker:
        await call.message.answer('Доступ закрыт. Используйте команду /start .')
        await state.finish()
        return
    del_msg = await bot.send_message(chat_id=call.message.chat.id, text='Подождите. Отправляю.')
    is_anonim = 'Да' if call.data.split('_')[1] == 'yes' else 'Нет'
    username = await get_username(call)
    user_data = await get_user(int(call.message.chat.id))
    state_data = await state.get_data()
    state_message = state_data.get('message')
    message_type = state_data.get('message_type')
    match message_type:
        case 'offer':
            message_type = 'Предложение'
        case 'question':
            message_type = 'Вопрос'
        case 'complaint':
            message_type = 'Жалоба'
    await bot.send_message(chat_id=CHAT_ID, text=f'''Сообщение от {username}
Email: {user_data.email}
Тип сообщения: {message_type}
Анонимность: {is_anonim}
========================''')
    for message in state_message:
        if not message.get('album'):
            content = message.get('content')
            caption = message.get('caption')
            match message.get('type'):
                case 'text':
                    await bot.send_message(chat_id=CHAT_ID, text=content)
                case 'audio':
                    if caption:
                        await bot.send_audio(chat_id=CHAT_ID, audio=content, caption=caption)
                    else:
                        await bot.send_audio(chat_id=CHAT_ID, audio=content)
                case 'document':
                    if caption:
                        await bot.send_document(chat_id=CHAT_ID, document=content, caption=caption)
                    else:
                        await bot.send_document(chat_id=CHAT_ID, document=content)
                case'sticker':
                    await bot.send_sticker(chat_id=CHAT_ID, sticker=content)
                case 'photo':
                    if caption:
                        await bot.send_photo(chat_id=CHAT_ID, photo=content, caption=caption)
                    else:
                        await bot.send_photo(chat_id=CHAT_ID, photo=content)
                case 'video':
                    if caption:
                        await bot.send_video(chat_id=CHAT_ID, video=content, caption=caption)
                    else:
                        await bot.send_video(chat_id=CHAT_ID, video=content)
                case 'voice':
                    await bot.send_voice(chat_id=CHAT_ID, voice=content)
                case 'contact':
                    await bot.send_contact(chat_id=CHAT_ID, first_name=content.get('name'),
                                           phone_number=content.get('number'))
                case 'location':
                    location = content.split(',')
                    await bot.send_location(chat_id=CHAT_ID, latitude=float(location[0]),
                                            longitude=float(location[1]))
        else:
            media_group = types.MediaGroup()
            if message.get('type') == 'photo' or message.get('type') == 'video':
                for item in message.get('content'):
                    if item.get('caption'):
                        media_group.attach({"media": item.get('file'),
                                            "type": message.get('type'),
                                            "caption": item.get('caption')})
                    else:
                        media_group.attach(
                            {"media": item.get('file'), "type": message.get('type')})
            await bot.send_media_group(chat_id=CHAT_ID, media=media_group)

    await bot.send_message(chat_id=CHAT_ID, text='===Конец сообщения===')
    await state.finish()
    await bot.delete_message(chat_id=call.message.chat.id, message_id=del_msg.message_id)
    await call.message.answer('''Спасибо за уделенное время!
Благодаря Вам мы становимся лучше. Для повторного обращения вызовите команду /start .''')
