import configparser
import random

import requests
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from telebot import types, TeleBot, custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from BD import Users, Users_words, Words
from BD import create_tables, add_base_word


config = configparser.ConfigParser()
config.read('data.ini')
token_bot = config['tlg']['token']
username_bd = config['bd_postgres']['user']
password_bd = config['bd_postgres']['password']
name_bd = config['bd_postgres']['namebd']
token_ya = config['Ya']['token']


url = 'https://dictionary.yandex.net/api/v1/dicservice.json/lookup'
DSN = f"postgresql://{username_bd}:{password_bd}@localhost:5432/{name_bd}"

engine = sqlalchemy.create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()
create_tables(engine)
add_base_word()

print('Start telegram bot...')


state_storage = StateMemoryStorage()
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    """
    функция предназначена для вывода пары заданное слово - перевод
    """
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    """
    функция вывода карточек-слов, так же используется для приветствия новых пользователей,
    их внесения в базу данных Users, наполнения пользовательской базы данных слов базовыми
    значениями
    """
    cid = message.chat.id
    known_users_bd = session.query(Users.cid).filter(Users.cid == cid).all()
    if not known_users_bd:
        userStep[cid] = 0
        session.add(Users(cid=cid))
        session.commit()
        add_base_word_for_user(message)
        bot.send_message(cid, "Привет 👋 Давай попрактикуемся в английском языке. "\
                            'Тренировки можешь проходить в удобном для себя темпе.\n'\
                            'У тебя есть возможность использовать тренажёр, как конструктор,'\
                            ' и собирать свою собственную базу для обучения. '\
                            'Для этого воспрользуйся инструментами:\n'\
                            '\t - добавить слово ➕,\n\t - удалить слово 🔙.\nНу что, начнём ⬇️')
    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = []
    n = session.query(Users.id).filter(Users.cid == cid).all()[0][0]
    quer_word = session.query(Words.target_word).\
        join(Users_words, Users_words.wid == Words.id).\
        filter(Users_words.uid == n).all()
    target_word = random.sample(quer_word, k=1)[0][0]
    translate = session.query(Words.translate_word).\
        filter(Words.target_word == target_word).all()[0][0]
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    quer_word_random = session.query(Words.target_word).filter(Words.target_word != target_word).all()
    others = random.sample(quer_word_random, k=3)
    other_words_btns = [types.KeyboardButton(word[0]) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


def add_base_word_for_user(message):
    """
    вспомогательная функция предназначена для наполнения базы данных пользователя первоначальным набором слов
    """
    cid = message.chat.id
    n = session.query(Users.id).filter(Users.cid == cid).all()[0][0]
    user_words = [Users_words(uid=n, wid=i) for i in range(1, 11)]
    session.add_all(user_words)
    session.commit()


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    """
    функция предназначена для вызова новой карточки, при получении Command.NEXT
    """
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """
    функция предназначена для удаления слова из пользовалельской БД
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        cid = message.chat.id
        word = data['target_word']
        n = session.query(Users.id).filter(Users.cid == cid).all()[0][0]
        w = session.query(Words.id).filter(Words.target_word == word).all()[0][0]
        session.query(Users_words).filter(Users_words.wid == w and Users_words.uid == n).delete()
        session.commit()


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def step1(message):
    """
    функция предназначена для добавления в пользовательскую базу новых слов,
    принимает значение слова на английском языке и передает значение функции step2
    """
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, 'введите слово на английском языке')
    bot.register_next_step_handler(message, step2)


def step2(message):
    """
    функция предназначена для добавления в пользовательскую базу новых слов,
    принимает значение слова, переводит его с использоваием функции translate_word()
    и добавляет в базу при помощи функции add_word1()
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        cid = message.chat.id
        word1 = message.text.lower()
        translate_word1 = translate_word(word1)
        add_word1(word1, translate_word1, cid)
        data['target_word'] = word1
        data['translate_word'] = translate_word1
        bot.send_message(cid, show_hint('записана пара', show_target(data)))


def add_word1(word1, translate_word1, cid):
    """
    функция предназначена для добавления в пользовательскую базу новых слов,
    проверяет наличие слова в общей базе, если слова в общей базе нет,
    добавляет его в Words. Привязывает слово к пользователю
    """
    n = session.query(Users.id).filter(Users.cid == cid).all()[0][0]
    base_words = session.query(Words.target_word).all()
    if (word1,) not in base_words:
        session.add(Words(target_word=word1, translate_word=translate_word1))
        session.commit()
    w = session.query(Words.id).filter(Words.target_word == word1).all()[0][0]
    session.add(Users_words(uid=n, wid=w))
    session.commit()


def translate_word(word):
    """
    функция предназначена получения перевода нового слова при добавлении.
    Используется API Яндекс-переводчик
    """
    trans_word_json = requests.get(url+f'?key={token_ya}&lang=en-ru&text={word}').json()
    trans_word = trans_word_json['def'][0]['tr'][0]['text']
    return trans_word


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    """
    функция проверки правильности ответа, при правильном ответе - поздравляет,
    при неправильном - дает еще одну попытку
    """
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
