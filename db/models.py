from peewee import *

db = SqliteDatabase('../sqlite.db')


class Person(Model):
    tg_id = IntegerField()
    email = CharField()

    class Meta:
        database = db


Person.create_table()
