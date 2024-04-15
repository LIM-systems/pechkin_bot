from aiogram.dispatcher.filters.state import State, StatesGroup


class User(StatesGroup):
    email = State()
    code = State()


class Dialogue(StatesGroup):
    message = State()
    message_type = State()
