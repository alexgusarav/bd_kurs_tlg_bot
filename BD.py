import configparser
import sqlalchemy
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Users(Base):
    __tablename__ = "users"

    id = sq.Column(sq.Integer, primary_key=True)
    cid = sq.Column(sq.BigInteger, unique=True)


class Words(Base):
    __tablename__ = "words"

    id = sq.Column(sq.Integer, primary_key=True)
    target_word = sq.Column(sq.String(length=20))
    translate_word = sq.Column(sq.String(length=20))


class Users_words(Base):
    __tablename__ = 'users_words'

    id = sq.Column(sq.Integer, primary_key=True)
    uid = sq.Column(sq.Integer, sq.ForeignKey("users.id"), nullable=False)
    wid = sq.Column(sq.Integer, sq.ForeignKey("words.id"), nullable=False)

    users = relationship(Users, backref="uid")
    words = relationship(Words, backref="wid")


def create_tables(engine):
    """
    функция предназначена удаления всех данных из базы данных и созданию таблиц при запуске программы
    """
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def add_base_word():
    """
    функция предназначена для наполнения базы данных первоначальным набором слов
    """
    w1 = Words(target_word='word', translate_word='слово')
    w2 = Words(target_word='car', translate_word='машина')
    w3 = Words(target_word='phone', translate_word='телефон')
    w4 = Words(target_word='red', translate_word='красный')
    w5 = Words(target_word='flower', translate_word='цветок')
    w6 = Words(target_word='clock', translate_word='часы')
    w7 = Words(target_word='peace', translate_word='мир')
    w8 = Words(target_word='white', translate_word='белый')
    w9 = Words(target_word='notebook', translate_word='блокнот')
    w10 = Words(target_word='door', translate_word='дверь')
    session.add_all([w1, w2, w3, w4, w5, w6, w7, w8, w9, w10])
    session.commit()


config = configparser.ConfigParser()
config.read('data.ini')
username_bd = config['bd_postgres']['user']
password_bd = config['bd_postgres']['password']
name_bd = config['bd_postgres']['namebd']

DSN = f"postgresql://{username_bd}:{password_bd}@localhost:5432/{name_bd}"

engine = sqlalchemy.create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()
