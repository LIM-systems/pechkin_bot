from db.models import Person
from utils import check_user_in_yandex


# проверка является ли пользователь авторизованным и сотрудников +
# удаление, если он авторизован, но уже не сотрудник
async def check_auth(user_id: int) -> bool:
    user = Person.select().where(Person.tg_id == user_id).first()
    if user:
        is_worker = await check_user_in_yandex(user.email)
        if not is_worker:
            user.delete_instance()
            return False
    return bool(user)


# проверка зареган ли уже такой email
async def check_email(email: str) -> bool:
    user = Person.select().where(Person.email == email).first()
    return bool(user)


# запись нового пользователя в бд
async def add_new_person(tg_id: int, email: str) -> None:
    Person.create(tg_id=tg_id, email=email)


# получить пользователя
async def get_user(tg_id: int) -> Person:
    user = Person.select().where(Person.tg_id == tg_id).first()
    return user
