from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, CallbackQueryHandler, filters
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import ReplyKeyboardRemove
from math import ceil
import json
import sqlite3
import requests

TOKEN = '6276213894:AAEUHFkdT-K5iYXiKCTpf4ZnFD9vgixug1k'
APIKEY = "40d1649f-0493-4b70-98ba-98533de7710b"
COMMON_KEYBOARD = ReplyKeyboardMarkup(
    [['/add_class', '/add_students'], ['/view_students', '/stop'], ['/view_class_list', '/match_students'],
     ['/show_matched', '/coordinates']],
    one_time_keyboard=False)

con = sqlite3.connect("stats.sqlite")
cur = con.cursor()


def write_file_to_db(user_id, file, first_name):
    res = cur.execute(f'''DELETE FROM classes WHERE user_id = ?''', (user_id,))
    res = cur.execute(f'''INSERT INTO classes(user_id, stat) VALUES(?,?)''', (user_id, file))
    res = cur.execute(f'''DELETE FROM names WHERE user_id = ?''', (user_id,))
    res = cur.execute(f'''INSERT INTO names(user_id, user_name) VALUES(?, ?)''', (user_id, first_name))
    con.commit()


def write_name_to_db(user_id, first_name):
    res = cur.execute(f'''UPDATE names
                          SET user_name = ?
                          WHERE user_id = ?''', (first_name, user_id))
    con.commit()


def read_name_from_db(user_id):
    res = cur.execute(f'''SELECT user_name FROM names
                          WHERE user_id = ?''', (user_id,)).fetchone()
    return res


def update_stat_in_db(user_id, file):
    res = cur.execute(f'''UPDATE classes
                          SET stat = ?
                          WHERE user_id = ?''', (file, user_id))
    con.commit()


def read_file_from_db(user_id):
    res = cur.execute(f'''SELECT stat FROM classes 
                        WHERE user_id = ?''', (user_id,)).fetchall()
    convert_to_common(res[0][0], 'stats.json')


def convert_to_binary(file):
    with open(file, 'rb') as file:
        res = file.read()
        return res


def convert_to_common(data, file):
    with open(file, 'wb') as file:
        file.write(data)


def generate_classes_keyboard(classes):
    plus = ceil(len(classes) / 3) * 3 - len(classes)
    [classes.append('') for i in range(plus)]
    res = classes
    res_ = []
    for i in range(0, len(res), 3):
        res_.append([res[i], res[i + 1], res[i + 2]])
    return ReplyKeyboardMarkup(res_, one_time_keyboard=True)


def generate_students_keyboard(students):
    keyboard = []
    for student in students:
        but = InlineKeyboardButton(student, callback_data=student)
        keyboard.append([but])
    final_but = InlineKeyboardButton('ГОТОВО', callback_data='DONE')
    keyboard.append([final_but])
    resboard = InlineKeyboardMarkup(keyboard)
    return resboard


async def simple_text_responser(update, context):
    await update.message.reply_text(
        f"Напиши /help, чтобы узнать больше о боте, {read_name_from_db(update.message.from_user.id)[0]}", )


async def start_responce(update, context):
    user = update.effective_user.first_name
    await update.message.reply_text(f"Привет, {user}. Как мне тебя называть?")
    with open('stats.json', 'w') as file:
        json.dump({}, file)
    write_file_to_db(update.message.from_user.id, convert_to_binary('stats.json'), user)

    return 1


async def naming(update, context):
    name = update.message.text
    write_name_to_db(update.message.from_user.id, name)
    keyboard = COMMON_KEYBOARD

    await update.message.reply_text(f"Привет, {read_name_from_db(update.message.from_user.id)[0]}",
                                    reply_markup=keyboard)

    return ConversationHandler.END


async def stop_naming(update, context):
    if read_name_from_db(update.message.from_user.id)[0] != update.effective_user.first_name:
        await update.message.reply_text('Ладно')
    else:
        await update.message.reply_text(
            f'Я Вас не запомнил. Вы просто {read_name_from_db(update.message.from_user.id)[0]}')

    return ConversationHandler.END


async def help_responce(update, context):
    await update.message.reply_text(
        "Вы можете использовать команды для добавления класса, учеников, отметки отсутсвующих")


async def answer_useless_stoping(update, context):
    await update.message.reply_text(f"Ни один процесс не запущен")


async def add_class(update, context):
    await update.message.reply_text(f"Введите название вашего класса")
    return 1


async def add_class_name(update, context):
    class_name = update.message.text
    read_file_from_db(update.message.from_user.id)
    with open('stats.json', 'r') as file:
        classes = json.load(file)
        if class_name in classes:
            await update.message.reply_text('Такой класс уже есть!')
        else:
            with open('stats.json', 'w') as wfile:
                classes[class_name] = {}
                json.dump(classes, wfile)
            update_stat_in_db(update.message.from_user.id, convert_to_binary('stats.json'))
            await update.message.reply_text(
                f"Класс {class_name} успешно добавлен. Используйте команду"
                f" /add_students, чтобы добавить учеников к класс.")
    return ConversationHandler.END


async def stop_class_adding(update, context):
    await update.message.reply_text(f"Класс не добавлен")
    return ConversationHandler.END


async def view_class_list(update, context):
    read_file_from_db(update.message.from_user.id)
    with open('stats.json') as file:
        classes = json.load(file)
    if classes:
        await update.message.reply_text(', '.join([i for i in classes]))
    else:
        await update.message.reply_text(
            f"Вы не добавили ни одного класса. Используйте /add_class, чтобы добавить штучку")


async def add_student(update, context):
    await update.message.reply_text(f"Введите название класса, в который мы добавим учеников")
    context.user_data['temp_students'] = []
    return 1


async def add_students_to_class(update, context):
    class_name = update.message.text
    read_file_from_db(update.message.from_user.id)
    with open('stats.json') as file:
        classes = json.load(file)
    if class_name in classes:
        context.user_data['temp_class'] = class_name
        keyboard = ReplyKeyboardMarkup([['/done']], one_time_keyboard=True)
        await update.message.reply_text(
            f"Введите имена учеников так, как Вы бы хотели видеть их в списке. Чтобы прервать ввод, введите /done",
            reply_markup=keyboard)
        return 2
    else:
        await update.message.reply_text(
            f"У нас нет такого класса. Попробуйте ввести название заново. Чтобы прервать ввод, введите /stop")
        return 1


async def add_new_student(update, context):
    student_name = update.message.text
    with open('stats.json') as file:
        classes = json.load(file)
        classes[context.user_data['temp_class']][student_name] = []
        with open('stats.json', 'w') as wfile:
            json.dump(classes, wfile)
    update_stat_in_db(update.message.from_user.id, convert_to_binary('stats.json'))
    context.user_data['temp_students'].append(student_name)
    return 2


async def finish_adding_students(update, context):
    if context.user_data['temp_students']:
        await update.message.reply_text(f"Вы успешно добавили учеников {', '.join(context.user_data['temp_students'])}",
                                        reply_markup=COMMON_KEYBOARD)
    else:
        await update.message.reply_text(f"Вы не добавили ни одного ученика")
    context.user_data['temp_class'] = ''
    context.user_data['temp_students'] = []

    return ConversationHandler.END


async def stop_adding_students(update, context):
    if context.user_data['temp_students']:
        await update.message.reply_text(f"Вы добавили некоторых учеников", reply_markup=COMMON_KEYBOARD)
    else:
        await update.message.reply_text(f"Ученеки не добавлены", reply_markup=COMMON_KEYBOARD)
    context.user_data['temp_class'] = ''
    context.user_data['temp_students'] = []
    return ConversationHandler.END


async def view_students_list(update, context):
    read_file_from_db(update.message.from_user.id)
    with open('stats.json') as file:
        classes = json.load(file).keys()
    await update.message.reply_text(
        f"Введите название класса, и мы покажем вам его учеников). Чтобы остановить ввод, введите /stop",
        reply_markup=generate_classes_keyboard(list(classes)))
    return 1


async def show_students_list(update, context):
    try:
        read_file_from_db(update.message.from_user.id)
        with open('stats.json') as file:
            classes = json.load(file)
        await update.message.reply_text(', '.join([i for i in classes[update.message.text]]),
                                        reply_markup=COMMON_KEYBOARD)
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            f"Мы не знаем такого класса(. Попроуйте ввести название заново. Используйте /add_class, чтобы добавить один")
        return 1

    except Exception as e:
        await update.message.reply_text(
            f"В вашем классе нет учеников", reply_markup=COMMON_KEYBOARD)
        return ConversationHandler.END


async def stop_showing_students(update, context):
    await update.message.reply_text(f"Вывод учеников остановлен", reply_markup=COMMON_KEYBOARD)
    return ConversationHandler.END


async def choose_date_to_match(update, context):
    await update.message.reply_text(f'Напишите дату, на которую мы отметим отсутсвующих')
    return 1


async def choose_class_to_match(update, context):
    context.user_data['temp_date'] = update.message.text
    context.user_data['temp_user'] = update.message.from_user.id
    await update.message.reply_text(f'Напишите название класса, в котором мы отметим отсутсвующих')
    return 2


async def match_students(update, context):
    context.user_data['class_name'] = update.message.text
    read_file_from_db(update.message.from_user.id)
    with open('stats.json') as file:
        classes = json.load(file)
        if context.user_data['class_name'] in classes:
            students = list(classes[context.user_data['class_name']])
            await update.message.reply_text(f'Выберете отсутсвующих учеников',
                                            reply_markup=generate_students_keyboard(students))
        else:
            await update.message.reply_text(f'Нет такого класса', reply_markup=COMMON_KEYBOARD)
            return 1


async def stop_matching_students(update, context):
    await update.message.reply_text(f'Отметка отсутсвующих прервана')
    return ConversationHandler.END


async def matching_done():
    pass


async def callback_responser(update, context):
    query = update.callback_query
    await query.answer()
    if query.data != "DONE":
        with open('stats.json', 'r') as file:
            classes = json.load(file)
            print(classes)
            classes[context.user_data['class_name']][query.data].append(context.user_data['temp_date'])
            with open('stats.json', 'w') as file_:
                print(classes)
                json.dump(classes, file_)
        update_stat_in_db(context.user_data['temp_user'], convert_to_binary('stats.json'))
    else:
        await query.edit_message_text(text='Вы отметили отсутсвующих')
        context.user_data['temp_date'] = ''
        context.user_data['temp_user'] = ''
        context.user_data['class_name'] = ''
        return ConversationHandler.END


async def choose_class_to_show_matched_students(update, context):
    await update.message.reply_text(f'Введите класс, отсутсвующих которого вы хотите посмотреть')
    return 1


async def choose_date_to_show_matched_students(update, context):
    context.user_data['temp_class_'] = update.message.text
    read_file_from_db(update.message.from_user.id)
    with open('stats.json') as file:
        classes = json.load(file)
        if context.user_data['temp_class_'] not in classes:
            await update.message.reply_text(
                f'Нет такого класса. Введите название заново или /stop, чтобы прервать вывод.')
            return 1
        elif not len(classes[context.user_data['temp_class_']]):
            await update.message.reply_text(f'В этом классе нет учениковб. Используйте /stop, чтобы остановить вывод. ')
            return 1
        else:
            await update.message.reply_text(f'Введите дату, в которую отсутсвовали ученики')
            return 2


async def show_matched_students(update, context):
    read_file_from_db(update.message.from_user.id)
    context.user_data['temp_date_'] = update.message.text
    with open('stats.json') as file:
        classes = json.load(file)
        print(context.user_data['temp_class_'])
        class_ = classes[context.user_data['temp_class_']]
        students = choose_students_by_date(class_, context.user_data['temp_date_'])
    if students:
        await update.message.reply_text(', '.join(students))
    else:
        await update.message.reply_text("В выбранную дату никто не отсутствовал!")
        context.user_data['temp_date_'] = ''
        context.user_data['temp_class_'] = ''
        return ConversationHandler.END
    context.user_data['temp_date_'] = ''
    context.user_data['temp_class_'] = ''
    return ConversationHandler.END


async def stop_showing_matched(update, context):
    await update.message.reply_text(f'Вывод отмеченных учеников остановлен')
    context.user_data['temp_date_'] = ''
    context.user_data['temp_class_'] = ''
    return ConversationHandler.END


def choose_students_by_date(class_, date):
    res = []
    for st in class_:
        if date in class_[st]:
            res.append(st)
    return res


def coordinating(name):
    serv = 'https://geocode-maps.yandex.ru/1.x/'
    params = {
        'apikey': APIKEY,
        'geocode': name,
        'format': 'json'
    }
    req = requests.get(serv, params=params).json()
    object_data = req['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']
    cords = object_data["Point"]["pos"]
    cords = ', '.join(cords.split()[::-1])
    return cords


async def learn_cords(update, context):
    await update.message.reply_text(f'Введите название объекта, координаты которого вы хотите узнать.')
    return 1


async def write_cords(update, context):
    await update.message.reply_text(coordinating(update.message.text))
    return ConversationHandler.END


async def stop_coordinating(update, context):
    await update.message.reply_text('Ладно')
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()

    meeting_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_responce)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, naming)]
        },
        fallbacks=[CommandHandler('stop', stop_naming)]
    )

    class_adding_handler = ConversationHandler(
        entry_points=[CommandHandler('add_class', add_class)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_class_name)]
        },
        fallbacks=[CommandHandler('stop', stop_class_adding)]
    )

    students_adding_handler = ConversationHandler(
        entry_points=[CommandHandler('add_students', add_student)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_students_to_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_student)]
        },
        fallbacks=[CommandHandler('stop', stop_adding_students), CommandHandler('done', finish_adding_students)]
    )

    students_showing_handler = ConversationHandler(
        entry_points=[CommandHandler('view_students', view_students_list)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_students_list)]
        },
        fallbacks=[CommandHandler('stop', stop_showing_students)]
    )

    students_matching_handler = ConversationHandler(
        entry_points=[CommandHandler('match_students', choose_date_to_match)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_class_to_match)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, match_students)],
        },
        fallbacks=[CommandHandler('stop', stop_matching_students)]
    )

    showing_students_matched_handler = ConversationHandler(
        entry_points=[CommandHandler('show_matched', choose_class_to_show_matched_students)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_date_to_show_matched_students)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_matched_students)]
        },
        fallbacks=[CommandHandler('stop', stop_showing_matched)]
    )

    coordinating_handler = ConversationHandler(
        entry_points=[CommandHandler('coordinates', learn_cords)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, write_cords)]
        },
        fallbacks=[CommandHandler('stop', stop_coordinating)]
    )

    app.add_handler(coordinating_handler)
    app.add_handler(showing_students_matched_handler)
    app.add_handler(students_matching_handler)
    app.add_handler(students_showing_handler)
    app.add_handler(students_adding_handler)
    app.add_handler(class_adding_handler)
    app.add_handler(CommandHandler('view_class_list', view_class_list))
    app.add_handler(CommandHandler('help', help_responce))
    app.add_handler(meeting_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, simple_text_responser))
    app.add_handler(CommandHandler('stop', answer_useless_stoping))
    app.add_handler(CallbackQueryHandler(callback_responser))
    app.run_polling()


if __name__ == '__main__':
    main()
