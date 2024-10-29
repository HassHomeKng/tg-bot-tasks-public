import logging
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Включите логирование ошибок
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = 'YOUR_BOT_TOKEN'

# Список сотрудников и их идентификаторы Telegram
employees = {
    "Иван Иванов": 123456789,
    "Петр Петров": 987654321,
}

# Словарь для хранения задач по пользователям
tasks = {}

def start(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение при команде /start."""
    update.message.reply_text('Привет! Я помогу вам управлять задачами.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Отвечает на команду /help."""
    text = (
        "Доступные команды:\n"
        "/add_task <описание> - добавить задачу\n"
        "/my_tasks - посмотреть свои текущие задачи\n"
        "/accept_task <номер_задачи> - принять задачу\n"
        "/complete_task <номер_задачи> - завершить задачу\n"
        "/transfer_task <номер_задачи> <имя_сотрудника> - передать задачу другому сотруднику\n"
        )
    update.message.reply_text(text)

def add_employee(update: Update, context: CallbackContext) -> None:
    """
    Добавление нового сотрудника.
    Команда: /add_employee <имя> <телеграм_id>
    """
    if not update.message.from_user.id == 0: # только администратор может добавлять сотрудников
        return

    args = context.args
    if len(args) != 2:
        update.message.reply_text("Неверный формат команды. Используйте: /add_employee имя телеграм_id")
        return

    name = args[0]
    try:
        telegram_id = int(args[1])
    except ValueError:
        update.message.reply_text(f"ID пользователя {args[1]} не является числом.")
        return

    employees[name] = telegram_id
    update.message.reply_text(f"Сотрудник {name} успешно добавлен!")

def list_employees(update: Update, context: CallbackContext) -> None:
    if not update.message.from_user.id == 0:  # только админ может просматривать список сотрудников
        return

    employee_list = "\n".join([f"{name}: {id}" for name, id in employees.items()])
    update.message.reply_text(f"Текущие сотрудники:\n{employee_list}")

def assign_task(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = user.id
    task_description = update.message.text.split(maxsplit=1)[1].strip()

    tasks[chat_id] = {"description": task_description, "status": "new"}
    update.message.reply_text(
        f'Задача "{task_description}" создана.\nЧтобы назначить её сотруднику используйте команду:\n/assign_task <имя сотрудника>'
    )

def my_tasks(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    current_tasks = tasks.get(chat_id, {}).get('tasks', [])

    if current_tasks:
        message = "Ваши текущие задачи:\n"
        for index, task in enumerate(current_tasks):
            message += f"{index + 1}. {task['description']}\n"
            reply_markup = generate_task_buttons(chat_id, index)
            update.message.reply_text(message, reply_markup=reply_markup)
    else:
        message = "У вас нет активных задач."
        update.message.reply_text(message)

def accept_task(update: Update, context: CallbackContext) -> None:
    """Принятие задачи"""
    chat_id = update.message.chat_id
    args = update.message.text.strip().split()[1:]

    try:
        task_index = int(args[0]) - 1
    except (ValueError, IndexError):
        update.message.reply_text('Ошибка: укажите номер задачи.')
        return

    current_tasks = tasks[chat_id]['tasks']
    if task_index >= len(current_tasks):
        update.message.reply_text("Ошибка: неверный индекс задачи.")
        return

    task = current_tasks[task_index]
    task['status'] = 'accepted'
    update.message.reply_text("Вы приняли задачу.")

def complete_task(update: Update, context: CallbackContext) -> None:
    """
    Завершение задачи.
    Команда: /complete_task <номер_задачи>
    """
    chat_id = update.effective_chat.id
    try:
        task_number = int(context.args[0])
    except ValueError:
        update.message.reply_text('Номер задачи должен быть целым числом!')
        return

    # Проверяем наличие задачи у пользователя
    if chat_id not in tasks or len(tasks[chat_id]["tasks"]) <= task_number:
        update.message.reply_text(f"У вас нет задачи под номером {task_number}.")
        return

    completed_task = tasks[chat_id]["tasks"].pop(task_number - 1)
    update.message.reply_text(f"Задача '{completed_task['description']}' завершена!")

def transfer_task(update: Update, context: CallbackContext) -> None:
    # Получаем параметры: номер задачи и имя сотрудника
    chat_id = update.message.chat_id
    params = context.args
    task_number, new_assignee_name = params[0], params[1]

    new_assignee_id = employees.get(new_assignee_name)
    if not new_assignee_id:
        update.message.reply_text(
            f"Сотрудник с именем {new_assignee_name} не найден. Проверьте правильность написания имени."
        )
        return

    if int(task_number) > len(tasks.get(chat_id, [])):
        update.message.reply_text("Задача с таким номером не найдена.")
        return

    old_assignee = update.effective_user.first_name
    transferred_task = tasks[int(task_number)]

    tasks[new_assignee_id] = transferred_task
    del tasks[old_assignee]

    update.message.reply_text(f'Задача передана от {old_assignee} к {new_assignee_name}')

def generate_task_buttons(chat_id, task_index):
    keyboard = [
        [InlineKeyboardButton("Принять", callback_data=f"accept_{task_index}_{chat_id}")],
        [InlineKeyboardButton("Передать другому", callback_data=f"transfer_{task_index}_{chat_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def button_accept_task(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, task_index, chat_id = query.data.split('_')
    task_index = int(task_index)
    chat_id = int(chat_id)

    current_tasks = tasks[chat_id]['tasks']
    if task_index >= len(current_tasks):
        query.answer(text="Ошибка: неверный индекс задачи.", show_alert=True)
        return

    task = current_tasks[task_index]
    task['status'] = 'accepted'
    query.edit_message_text(text=f"Вы приняли задачу: {task['description']}")
    query.answer(text="Задача принята.")

def button_transfer_task(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, task_index, chat_id = query.data.split('_')
    task_index = int(task_index)
    chat_id = int(chat_id)

    current_tasks = tasks[chat_id]['tasks']
    if task_index >= len(current_tasks):
        query.answer(text="Ошибка: неверный индекс задачи.", show_alert=True)
        return

    task = current_tasks[task_index]
    query.edit_message_text(text=f"Выберите сотрудника для передачи задачи: {task['description']}")
    query.answer(text="Кого выбрать?")

def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^/add_task'), assign_task))
    dispatcher.add_handler(CommandHandler('my_tasks', my_tasks))
    dispatcher.add_handler(CallbackQueryHandler(button_accept_task, pattern=r'^accept_\d+_\
