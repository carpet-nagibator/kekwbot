import json
import random
from datetime import datetime
from Settings import TOKEN, WEBHOOK
from flask import Flask, request, Response
from sqlalchemy import create_engine, ForeignKey, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.viber_requests import ViberMessageRequest, ViberConversationStartedRequest
from viberbot.api.messages import (
    TextMessage
)

#engine = create_engine('sqlite:///mydb.db', echo=True)
engine = create_engine('postgres://lczzteaucanfvc:994b06b0eb663196de10011cdc9f3f087130adeba87ebb6fddb482fe371ce3cc@ec2-52-200-119-0.compute-1.amazonaws.com:5432/dcqbg6ek6hjaiq', echo=True)
Base = declarative_base()
Session = sessionmaker(engine)


class Users(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    viber_id = Column(String, nullable=False, unique=True)
    all_answers = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    question = Column(String)
    dt_last_answer = Column(DateTime)
    words = relationship('Learning', back_populates='users')


class Learning(Base):
    __tablename__ = 'learning'
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True, nullable=False)
    word = Column(String, primary_key=True, nullable=False)
    right_answer = Column(Integer, nullable=False, default=0)
    dt_last_answer = Column(DateTime)
    users = relationship('Users', back_populates='words')


def add_user(viber_id):
    session = Session()
    try:
        session.add(Users(viber_id=viber_id, all_answers=0, correct_answers=0))
        session.commit()
        session.close()
    except:
        session.rollback()
        session.close()


def send_question(viber_id):
    session = Session()
    select_query = session.query(Users.all_answers, Users.correct_answers, Users.user_id,
                                 Users.dt_last_answer).filter(Users.viber_id == viber_id).one()
    session.close()
    if select_query[0] >= 10:
        temp_correct_answers = select_query[1]
        session = Session()
        update_query = session.query(Users).filter(Users.viber_id == viber_id).one()
        update_query.all_answers = 0
        update_query.correct_answers = 0
        session.commit()
        session.close()

        session = Session()
        select_query2 = session.query(Learning.word).filter(Learning.user_id == select_query[2]).filter(
            Learning.right_answer >= 5).count()
        session.close()
        return TextMessage(text=f'У вас {temp_correct_answers} верных из 10. '
                                f'Вы уже выучили {select_query2} слов. '
                                f'Осталось выучить {50 - select_query2} слов. '
                                f'Последний опрос пройден {str(select_query[3])[:16]}. '
                                f'Хотите ещё раз сыграть?',
                           keyboard=KEYBOARD1, tracking_data='tracking_data')
    else:
        temp_answers = []
        temp_correct_answer = 100
        question = {}
        while temp_correct_answer >= 5:
            question = random.choice(data)
            try:
                session = Session()
                session.add(Learning(user_id=select_query[2], word=question['word']))
                session.commit()
                session.close()
            except:
                session.rollback()
                session.close()

            session = Session()
            select_query2 = session.query(Learning.right_answer).filter(Learning.user_id == select_query[2]).filter(
                Learning.word == question['word']).one()
            session.close()
            temp_correct_answer = select_query2[0]

        session = Session()
        update_query = session.query(Users).filter(Users.viber_id == viber_id).one()
        update_query.question = str(question)
        session.commit()
        session.close()

        temp_answers.append(question['translation'])

        for i in range(3):
            temp_answers.append(random.choice(data)['translation'])
        random.shuffle(temp_answers)
        for i in range(4):
            temp_question = {'question_number': f'{select_query[0]}',
                             'answer': f"{temp_answers[i]}"}
            KEYBOARD2['Buttons'][i]['Text'] = f'{temp_answers[i]}'
            KEYBOARD2['Buttons'][i]['ActionBody'] = f'{temp_question}'
        return TextMessage(text=f'{select_query[0] + 1}.Как переводится слово {question["word"]}',
                           keyboard=KEYBOARD2, tracking_data='tracking_data')


def check_answer(viber_id, user_answer):
    check = 'Неверно'
    session = Session()
    select_query = session.query(Users.question, Users.user_id, Users.all_answers).filter(Users.viber_id == viber_id).one()
    session.close()
    question = eval(select_query[0])

    session = Session()
    update_query = session.query(Users).filter(Users.viber_id == viber_id).one()
    update_query.all_answers += 1
    update_query.dt_last_answer = datetime.utcnow()
    session.commit()
    session.close()

    if user_answer == question['translation']:
        session = Session()
        update_query1 = session.query(Users).filter(Users.viber_id == viber_id).one()
        update_query1.correct_answers += 1
        session.commit()
        session.close()

        session = Session()
        update_query2 = session.query(Learning).filter(Learning.word == question['word']).filter(
            Learning.user_id == select_query[1]).one()
        update_query2.right_answer += 1
        update_query2.dt_last_answer = datetime.utcnow()
        session.commit()
        session.close()

        session = Session()
        select_query2 = session.query(Learning.right_answer).filter(Learning.word == question['word']).filter(
            Learning.user_id == select_query[1]).one()
        session.close()
        check = f'Верно. Количество правильных ответов: {select_query2[0]}'
    return TextMessage(text=check, keyboard=KEYBOARD2, tracking_data='tracking_data')


def send_example(viber_id):
    session = Session()
    select_query = session.query(Users.question).filter(Users.viber_id == viber_id).one()
    session.close()
    question = eval(select_query[0])
    return TextMessage(text=f'{random.choice(question["examples"])}',
                       keyboard=KEYBOARD2, tracking_data='tracking_data')


def update_time(viber_id):
    session = Session()
    update_query = session.query(Users).filter(Users.viber_id == viber_id).one()
    update_query.dt_last_answer = datetime.utcnow()
    session.commit()
    session.close()
    return TextMessage(text='Прохождение теста отложено на полчаса KEKW')


def get_question_number(viber_id):
    session = Session()
    select_query = session.query(Users.all_answers).filter(Users.viber_id == viber_id).one()
    session.close()
    return select_query[0]


app = Flask(__name__)
count = 0

bot_configuration = BotConfiguration(
    name='olddrunkenwolf',
    avatar='http://viber.com/avatar.jpg',
    auth_token=TOKEN
)

viber = Api(bot_configuration)


@app.route('/')
def hello():
    global count
    count += 1
    return f'Hello world {count}'


with open("english_words.json", "r", encoding='utf-8') as f:
    data = json.load(f)

KEYBOARD1 = {
"Type": "keyboard",
"Buttons": [
        {
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "ActionBody": "Давай начнём!",
            "Text": "Давай начнём!"
        }
    ]
}

KEYBOARD2 = {
"Type": "keyboard",
"Buttons": [
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "ActionBody": "Показать пример",
            "Text": "Показать пример"
        }
    ]
}


@app.route('/incoming', methods=['POST'])
def incoming():
    #Base.metadata.create_all(engine)
    viber_request = viber.parse_request(request.get_data())
    print(viber_request)
    if isinstance(viber_request, ViberConversationStartedRequest):
        # идентификация/добавление нового пользователя
        new_current_id = viber_request.user.id
        add_user(new_current_id)
        viber.send_messages(viber_request.user.id, [
            TextMessage(text='Бот предназначен для заучивания английских слов, для начала нажмите кнопку снизу.',
                        keyboard=KEYBOARD1, tracking_data='tracking_data')
        ])
    if isinstance(viber_request, ViberMessageRequest):
        current_id = viber_request.sender.id
        message = viber_request.message
        if isinstance(message, TextMessage):
            text = message.text
            print(text)
            # чтение введёного текста
            if text == "Давай начнём!":
                bot_response = send_question(current_id)
                viber.send_messages(current_id, bot_response)
            elif text == "Показать пример":
                bot_response = send_example(current_id)
                viber.send_messages(current_id, bot_response)
            elif text == "Отложить":
                bot_response = update_time(current_id)
                viber.send_messages(current_id, bot_response)
            else:
                answer = eval(text)
                question_number = get_question_number(current_id)
                if int(question_number) == int(answer['question_number']):
                    bot_response_1 = check_answer(current_id, answer['answer'])
                    bot_response_2 = send_question(current_id)
                    viber.send_messages(current_id, [bot_response_1, bot_response_2])
    return Response(status=200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=80)
