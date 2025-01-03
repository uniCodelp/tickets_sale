import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler, CallbackContext
import colorlog

# Логирование
logger = logging.getLogger()
logHandler = colorlog.StreamHandler()
logFormatter = colorlog.ColoredFormatter('%(log_color)s[%(levelname)s] %(message)s')
logHandler.setFormatter(logFormatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Настройка базы данных SQLite
def init_db():
    conn = sqlite3.connect('ticket_sales.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, phone TEXT, city TEXT, payment_method TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, event_type TEXT, price REAL, city TEXT, status TEXT)''')
    conn.commit()
    conn.close()

# Команды бота
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(f'Привет, {user.first_name}! Этот бот поможет тебе продавать и покупать билеты на мероприятия.\n\n'
                              'Используй меню ниже для навигации:',
                              reply_markup=main_menu())

def main_menu():
    keyboard = [['Продать билет', 'Торговая площадка'],
                ['Настройки', 'Политика соглашения']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Обработчик кнопки "Настройки"
def settings(update: Update, context: CallbackContext):
    keyboard = [['Номер телефона', 'Город'],
                ['Способ получения оплаты', 'Связь с тех. поддержкой']]
    update.message.reply_text("В разделе настроек ты можешь изменить свои данные.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# Обработчик кнопки "Продать билет"
def sell_ticket(update: Update, context: CallbackContext):
    update.message.reply_text("Выбери тип мероприятия, на которое ты хочешь продать билет: \n"
                              "1. Концерт \n"
                              "2. Спортивное событие \n"
                              "3. Театральное представление", 
                              reply_markup=ReplyKeyboardMarkup([['Концерт', 'Спортивное событие', 'Театральное представление']], resize_keyboard=True))

    return "SELL_TICKET_TYPE"

def ticket_type(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data['event_type'] = update.message.text
    update.message.reply_text("Теперь отправь мне файл с билетом.")
    
    return "SELL_TICKET_FILE"

def ticket_file(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data['ticket_file'] = update.message.document.file_id  # Сохраняем файл билета
    update.message.reply_text("Укажи цену, за которую ты хочешь продать билет.")

    return "SELL_TICKET_PRICE"

def ticket_price(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data['price'] = update.message.text
    update.message.reply_text("Теперь, если ты согласен с условиями, нажми 'Я согласен', чтобы разместить билет на площадке.")

    return "SELL_TICKET_CONFIRM"

def ticket_confirm(update: Update, context: CallbackContext):
    user_data = context.user_data
    ticket_info = {
        'event_type': user_data['event_type'],
        'price': user_data['price'],
        'ticket_file': user_data['ticket_file'],
        'user_id': update.message.from_user.id
    }
    
    # Добавляем билет в базу данных
    conn = sqlite3.connect('ticket_sales.db')
    c = conn.cursor()
    c.execute("INSERT INTO tickets (user_id, event_type, price, city, status) VALUES (?, ?, ?, ?, ?)",
              (ticket_info['user_id'], ticket_info['event_type'], ticket_info['price'], 'default', 'available'))
    conn.commit()
    conn.close()
    
    update.message.reply_text(f"Ваш билет на мероприятие '{user_data['event_type']}' был размещен на торговой площадке!")
    return ConversationHandler.END

# Основной обработчик сообщений
def handle_text(update: Update, context: CallbackContext):
    update.message.reply_text("Неизвестная команда. Пожалуйста, используйте меню.")

# Основная функция для запуска бота
def main():
    init_db()
    
    updater = Updater("8018543300:AAFgcrM7-n7d1kkiO35M96PHp-UCHtVagrU", use_context=True)
    
    dp = updater.dispatcher
    
    # ConversationHandler для обработки шагов продажи билета
    sell_ticket_handler = ConversationHandler(
        entry_points=[CommandHandler('sell_ticket', sell_ticket)],
        states={
            "SELL_TICKET_TYPE": [MessageHandler(Filters.text, ticket_type)],
            "SELL_TICKET_FILE": [MessageHandler(Filters.document, ticket_file)],
            "SELL_TICKET_PRICE": [MessageHandler(Filters.text & ~Filters.command, ticket_price)],
            "SELL_TICKET_CONFIRM": [MessageHandler(Filters.text & ~Filters.command, ticket_confirm)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: update.message.reply_text("Отмена продажи билета"))]
    )
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("settings", settings))
    dp.add_handler(sell_ticket_handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
