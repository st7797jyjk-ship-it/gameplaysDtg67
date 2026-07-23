import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8738389743:AAGzzdVDkANNvaQ9ehoBsDgwyaLPVNjytW8"

user_balances = {}
user_bets = {}
user_upgrade_data = {}

PROGRESS_EMPTY = "⬜️"
PROGRESS_FILL = "🟩"
PROGRESS_LENGTH = 12

def get_balance(user_id: int) -> int:
    return user_balances.get(user_id, 0)

def set_balance(user_id: int, amount: int):
    user_balances[user_id] = amount

# ===== СТАРТ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_balances:
        await show_main_menu(update, context, new_msg=True)
        return

    keyboard = [
        [InlineKeyboardButton("💰 Да, хочу 10000!", callback_data="take_money")],
        [InlineKeyboardButton("🚫 Нет, начну с нуля", callback_data="no_money")],
    ]
    await update.message.reply_text(
        "🎮 Привет! Это игровое казино.\n\n"
        "Хочешь получить стартовый капитал 10000 монет?\n"
        "Или начнёшь честно с нуля?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_start_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "take_money":
        user_balances[user_id] = 10000
        text = "✅ Ты получил 10000 монет! Удачи!"
    else:
        user_balances[user_id] = 0
        text = "💪 Ты начал с нуля! Респект!"

    keyboard = [[InlineKeyboardButton("🎮 В меню", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== ГЛАВНОЕ МЕНЮ =====
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, new_msg=False):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton("📈 Апгрейд", callback_data="upgrade")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
    ]
    text = f"🎮 Главное меню\nБаланс: {get_balance(user_id)} монет"
    
    if new_msg:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== КАЗИНО =====
async def casino_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    keyboard = [
        [InlineKeyboardButton("🎰 Крутить", callback_data="spin")],
        [InlineKeyboardButton(f"💵 Ставка: {bet}", callback_data="change_bet_casino")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f"🎰 Казино\nБаланс: {get_balance(user_id)} монет\nСтавка: {bet}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_bet_casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    current = user_bets.get(user_id, 100)
    keyboard = [
        [InlineKeyboardButton("+100", callback_data="cb_100"),
         InlineKeyboardButton("+500", callback_data="cb_500")],
        [InlineKeyboardButton("x2", callback_data="cb_x2"),
         InlineKeyboardButton("/2", callback_data="cb_div2")],
        [InlineKeyboardButton("🔙 Назад", callback_data="casino")],
    ]
    await query.edit_message_text(
        f"💵 Текущая ставка: {current}\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bet_action_casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data
    await query.answer()

    current = user_bets.get(user_id, 100)
    if action == "cb_100":
        user_bets[user_id] = current + 100
    elif action == "cb_500":
        user_bets[user_id] = current + 500
    elif action == "cb_x2":
        user_bets[user_id] = current * 2
    elif action == "cb_div2":
        user_bets[user_id] = max(10, current // 2)

    await casino_menu(update, context)

async def spin_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    if get_balance(user_id) < bet:
        await query.edit_message_text(
            f"❌ Недостаточно монет! Баланс: {get_balance(user_id)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="casino")
            ]])
        )
        return

    set_balance(user_id, get_balance(user_id) - bet)
    slots = ["🍒", "🍋", "🍊", "💎", "7️⃣", "⭐"]

    # Анимация
    for frame in range(3):
        temp = [random.choice(slots) for _ in range(3)]
        display = f"🎰 | {' | '.join(temp)} | 🎰"
        try:
            await query.edit_message_text(
                f"{display}\n\nКрутим...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎰 Крутится...", callback_data="none")
                ]])
            )
            await asyncio.sleep(0.4)
        except:
            pass

    result = [random.choice(slots) for _ in range(3)]
    display = f"🎰 | {' | '.join(result)} | 🎰"

    if result[0] == result[1] == result[2]:
        win = bet * 10
        set_balance(user_id, get_balance(user_id) + win)
        status = f"🎉 ДЖЕКПОТ! x10\nВыигрыш: {win} монет"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win = bet * 2
        set_balance(user_id, get_balance(user_id) + win)
        status = f"✨ Повезло! x2\nВыигрыш: {win} монет"
    else:
        status = f"😢 Не повезло\nПотеряно: {bet} монет"

    keyboard = [
        [InlineKeyboardButton("🎰 Ещё раз", callback_data="spin")],
        [InlineKeyboardButton("🔙 В казино", callback_data="casino")],
    ]
    await query.edit_message_text(
        f"{display}\n\n{status}\nБаланс: {get_balance(user_id)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== АПГРЕЙД =====
async def upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    upgrade_data = user_upgrade_data.get(user_id, {})
    percent = upgrade_data.get('percent', 75)
    multiplier = round(100 / percent, 2)
    possible_win = int(bet * multiplier)

    keyboard = [
        [InlineKeyboardButton("📈 Запустить", callback_data="run_upgrade")],
        [InlineKeyboardButton(f"💵 Ставка: {bet}", callback_data="change_bet_upgrade")],
        [InlineKeyboardButton(f"🎯 Шанс: {percent}%", callback_data="select_percent")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]

    text = (
        f"📈 Апгрейд\n\n"
        f"Ставка: {bet} монет\n"
        f"Шанс: {percent}%\n"
        f"Множитель: x{multiplier}\n"
        f"Возможный выигрыш: {possible_win} монет\n"
        f"Баланс: {get_balance(user_id)}"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def change_bet_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    current = user_bets.get(user_id, 100)
    keyboard = [
        [InlineKeyboardButton("+100", callback_data="ub_100"),
         InlineKeyboardButton("+500", callback_data="ub_500")],
        [InlineKeyboardButton("x2", callback_data="ub_x2"),
         InlineKeyboardButton("/2", callback_data="ub_div2")],
        [InlineKeyboardButton("🔙 Назад", callback_data="upgrade")],
    ]
    await query.edit_message_text(
        f"💵 Текущая ставка: {current}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bet_action_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data
    await query.answer()

    current = user_bets.get(user_id, 100)
    if action == "ub_100":
        user_bets[user_id] = current + 100
    elif action == "ub_500":
        user_bets[user_id] = current + 500
    elif action == "ub_x2":
        user_bets[user_id] = current * 2
    elif action == "ub_div2":
        user_bets[user_id] = max(10, current // 2)

    await upgrade_menu(update, context)

async def select_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("75% — x1.33", callback_data="percent_75")],
        [InlineKeyboardButton("50% — x2", callback_data="percent_50")],
        [InlineKeyboardButton("25% — x4", callback_data="percent_25")],
        [InlineKeyboardButton("5% — x20", callback_data="percent_5")],
        [InlineKeyboardButton("🔙 Назад", callback_data="upgrade")],
    ]
    await query.edit_message_text("🎯 Выбери шанс выигрыша:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    percent = int(query.data.split('_')[1])
    if user_id not in user_upgrade_data:
        user_upgrade_data[user_id] = {}
    user_upgrade_data[user_id]['percent'] = percent

    bet = user_bets.get(user_id, 100)
    multiplier = round(100 / percent, 2)
    possible_win = int(bet * multiplier)

    await query.edit_message_text(
        f"✅ Выбран шанс {percent}%\n"
        f"Множитель: x{multiplier}\n"
        f"При ставке {bet} — выигрыш: {possible_win}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К апгрейду", callback_data="upgrade")
        ]])
    )

async def run_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    if get_balance(user_id) < bet:
        await query.edit_message_text(
            "❌ Недостаточно монет!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="upgrade")
            ]])
        )
        return

    upgrade_data = user_upgrade_data.get(user_id, {})
    percent = upgrade_data.get('percent', 75)
    set_balance(user_id, get_balance(user_id) - bet)

    bar = PROGRESS_EMPTY * PROGRESS_LENGTH
    msg = await query.edit_message_text(
        f"📈 Запускаем...\n{bar}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏳ Идёт...", callback_data="none")
        ]])
    )

    for i in range(PROGRESS_LENGTH + 1):
        filled = PROGRESS_FILL * i
        empty = PROGRESS_EMPTY * (PROGRESS_LENGTH - i)
        bar = filled + empty
        percentage = int((i / PROGRESS_LENGTH) * 100)
        try:
            await msg.edit_text(
                f"📈 Апгрейд... {percentage}%\n{bar}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏳ Идёт...", callback_data="none")
                ]])
            )
            await asyncio.sleep(0.25)
        except:
            break

    win = random.randint(1, 100) <= percent
    if win:
        multiplier = round(100 / percent, 2)
        prize = int(bet * multiplier)
        set_balance(user_id, get_balance(user_id) + prize)
        result_text = f"🎉 ВЫИГРЫШ!\n+{prize} монет (x{multiplier})"
    else:
        result_text = f"😢 Проигрыш\n-{bet} монет"

    keyboard = [
        [InlineKeyboardButton("📈 Ещё раз", callback_data="run_upgrade")],
        [InlineKeyboardButton("🔙 К апгрейду", callback_data="upgrade")],
    ]
    await msg.edit_message_text(
        f"📈 Апгрейд завершён!\n{bar}\n\n{result_text}\nБаланс: {get_balance(user_id)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== БАЛАНС =====
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💸 Взять 10000", callback_data="take_money_again")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f"💰 Твой баланс: {get_balance(user_id)} монет\n\nМожешь взять ещё 10000 если проигрался:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def take_money_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    set_balance(user_id, get_balance(user_id) + 10000)
    await query.edit_message_text(
        f"✅ +10000 монет!\nНовый баланс: {get_balance(user_id)}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В меню", callback_data="main_menu")
        ]])
    )

# ===== НАВИГАЦИЯ =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "none":
        await query.answer()
        return

    routes = {
        "main_menu": show_main_menu,
        "casino": casino_menu,
        "spin": spin_slots,
        "change_bet_casino": change_bet_casino,
        "upgrade": upgrade_menu,
        "change_bet_upgrade": change_bet_upgrade,
        "balance": show_balance,
        "select_percent": select_percent,
        "run_upgrade": run_upgrade,
        "take_money_again": take_money_again,
        "take_money": handle_start_choice,
        "no_money": handle_start_choice,
    }

    if data.startswith("cb_"):
        await bet_action_casino(update, context)
    elif data.startswith("ub_"):
        await bet_action_upgrade(update, context)
    elif data.startswith("percent_"):
        await set_percent(update, context)
    elif data in routes:
        await routes[data](update, context)

    await query.answer()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🎰 Казино бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()