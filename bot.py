import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8738389743:AAGzzdVDkANNvaQ9ehoBsDgwyaLPVNjytW8"

user_balances = {}
user_bets = {}
user_upgrade_data = {}
user_blackjack = {}
user_bet_input = {}

PROGRESS_EMPTY = "⬜️"
PROGRESS_FILL = "🟩"
PROGRESS_LENGTH = 12

SUITS = ["♠️", "♥️", "♦️", "♣️"]
VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

def get_balance(user_id: int) -> int:
    return user_balances.get(user_id, 0)

def set_balance(user_id: int, amount: int):
    user_balances[user_id] = amount

def card_value(card: str) -> int:
    val = card.split(" ")[0]
    if val in ["J", "Q", "K"]:
        return 10
    elif val == "A":
        return 11
    return int(val)

def hand_value(cards: list) -> int:
    total = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c.startswith("A"))
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def new_deck() -> list:
    deck = [f"{v} {s}" for s in SUITS for v in VALUES]
    random.shuffle(deck)
    return deck

# ===== КАЛЬКУЛЯТОР СТАВКИ =====
def get_bet_keyboard(user_id: int, return_to: str) -> InlineKeyboardMarkup:
    current = user_bet_input.get(user_id, str(user_bets.get(user_id, 100)))
    buttons = [
        [InlineKeyboardButton("1", callback_data=f"num_1_{return_to}"),
         InlineKeyboardButton("2", callback_data=f"num_2_{return_to}"),
         InlineKeyboardButton("3", callback_data=f"num_3_{return_to}")],
        [InlineKeyboardButton("4", callback_data=f"num_4_{return_to}"),
         InlineKeyboardButton("5", callback_data=f"num_5_{return_to}"),
         InlineKeyboardButton("6", callback_data=f"num_6_{return_to}")],
        [InlineKeyboardButton("7", callback_data=f"num_7_{return_to}"),
         InlineKeyboardButton("8", callback_data=f"num_8_{return_to}"),
         InlineKeyboardButton("9", callback_data=f"num_9_{return_to}")],
        [InlineKeyboardButton("0", callback_data=f"num_0_{return_to}"),
         InlineKeyboardButton("00", callback_data=f"num_00_{return_to}"),
         InlineKeyboardButton("⌫", callback_data=f"num_del_{return_to}")],
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"num_ok_{return_to}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=return_to)],
    ]
    return InlineKeyboardMarkup(buttons)

async def show_bet_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, return_to: str):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_bet_input[user_id] = str(user_bets.get(user_id, 100))

    await query.edit_message_text(
        f"💵 Введи ставку:\n\n"
        f"Сумма: {user_bet_input[user_id]} монет\n"
        f"Баланс: {get_balance(user_id)}",
        reply_markup=get_bet_keyboard(user_id, return_to)
    )

async def handle_num_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    parts = data.split('_')
    action = parts[1]
    return_to = '_'.join(parts[2:]) if len(parts) > 2 else 'main_menu'

    current = user_bet_input.get(user_id, "100")

    if action == "del":
        if len(current) > 0:
            current = current[:-1]
        if not current:
            current = "0"
    elif action == "ok":
        amount = int(current) if current else 0
        if amount < 10:
            await query.answer("⚠️ Минимальная ставка: 10", show_alert=True)
            return
        if amount > get_balance(user_id):
            await query.answer("❌ Недостаточно монет!", show_alert=True)
            return
        user_bets[user_id] = amount
        user_bet_input.pop(user_id, None)
        routes = {
            "casino": casino_menu,
            "blackjack_menu": blackjack_menu,
            "upgrade": upgrade_menu,
        }
        if return_to in routes:
            await routes[return_to](update, context)
        return
    else:
        if action == "00":
            current += "00"
        else:
            if current == "0":
                current = action
            else:
                current += action

    if len(current) > 9:
        current = current[:9]

    user_bet_input[user_id] = current

    try:
        await query.edit_message_text(
            f"💵 Введи ставку:\n\n"
            f"Сумма: {current} монет\n"
            f"Баланс: {get_balance(user_id)}",
            reply_markup=get_bet_keyboard(user_id, return_to)
        )
    except:
        pass

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
        [InlineKeyboardButton("🃏 Блэкджек", callback_data="blackjack_menu")],
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
        [InlineKeyboardButton(f"💵 Ставка: {bet}", callback_data="betcalc_casino")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f"🎰 Казино\nБаланс: {get_balance(user_id)} монет\nСтавка: {bet}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

# ===== БЛЭКДЖЕК =====
async def blackjack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    keyboard = [
        [InlineKeyboardButton("🃏 Играть", callback_data="blackjack_start")],
        [InlineKeyboardButton(f"💵 Ставка: {bet}", callback_data="betcalc_blackjack_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f"🃏 Блэкджек\n"
        f"Баланс: {get_balance(user_id)} монет\n"
        f"Ставка: {bet}\n\n"
        "📋 Правила:\n"
        "• Цель — набрать 21 или больше дилера\n"
        "• Перебор (больше 21) — мгновенный проигрыш\n"
        "• Туз = 1 или 11 очков\n"
        "• Картинки (J, Q, K) = 10 очков\n"
        "• Дилер обязан брать до 17\n"
        "• Если у обоих поровну — ничья",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def blackjack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bet = user_bets.get(user_id, 100)
    if get_balance(user_id) < bet:
        await query.edit_message_text(
            f"❌ Недостаточно монет! Баланс: {get_balance(user_id)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="blackjack_menu")
            ]])
        )
        return

    set_balance(user_id, get_balance(user_id) - bet)

    deck = new_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]

    user_blackjack[user_id] = {
        'deck': deck,
        'player': player_cards,
        'dealer': dealer_cards,
        'bet': bet,
        'done': False
    }

    if hand_value(player_cards) == 21:
        await blackjack_natural(query, user_id)
        return

    await show_blackjack_state(query, user_id)

async def blackjack_natural(query, user_id):
    data = user_blackjack.get(user_id)
    if not data:
        return

    dealer_score = hand_value(data['dealer'])
    player_display = " | ".join(data['player'])
    dealer_display = " | ".join(data['dealer'])

    if dealer_score == 21:
        set_balance(user_id, get_balance(user_id) + data['bet'])
        result_text = "🤝 У обоих Блэкджек! Ничья.\nСтавка возвращена."
    else:
        win = int(data['bet'] * 2.5)
        set_balance(user_id, get_balance(user_id) + win)
        result_text = f"🎉 БЛЭКДЖЕК! x2.5\nВыигрыш: {win} монет"

    text = (
        f"🃏 Блэкджек — БЛЭКДЖЕК!\n\n"
        f"👤 Твои карты: {player_display}\n"
        f"📊 Твои очки: 21 🎯\n\n"
        f"🏦 Карты дилера: {dealer_display}\n"
        f"📊 Очки дилера: {dealer_score}\n\n"
        f"{result_text}\n"
        f"💰 Баланс: {get_balance(user_id)}"
    )

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё раз", callback_data="blackjack_start")],
        [InlineKeyboardButton("🔙 В меню", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_blackjack[user_id]

async def show_blackjack_state(query, user_id):
    data = user_blackjack.get(user_id)
    if not data:
        return

    player_cards = data['player']
    dealer_cards = data['dealer']
    player_score = hand_value(player_cards)
    dealer_visible = card_value(dealer_cards[0])

    player_display = " | ".join(player_cards)
    dealer_display = f"{dealer_cards[0]} | 🂠"

    text = (
        f"🃏 Блэкджек\n\n"
        f"👤 Твои карты: {player_display}\n"
        f"📊 Твои очки: {player_score}\n\n"
        f"🏦 Дилер: {dealer_display}\n"
        f"📊 Очки дилера: {dealer_visible}+\n\n"
        f"💵 Ставка: {data['bet']} | 💰 Баланс: {get_balance(user_id)}"
    )

    keyboard = [
        [InlineKeyboardButton("➕ Взять карту", callback_data="bj_hit"),
         InlineKeyboardButton("✋ Оставить", callback_data="bj_stand")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def blackjack_hit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = user_blackjack.get(user_id)
    if not data or data['done']:
        return

    data['player'].append(data['deck'].pop())
    player_score = hand_value(data['player'])

    if player_score > 21:
        await blackjack_bust(query, user_id)
    elif player_score == 21:
        await blackjack_stand(query, user_id)
    else:
        await show_blackjack_state(query, user_id)

async def blackjack_stand(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if isinstance(update, Update):
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
    else:
        query = update
        user_id = user_id

    data = user_blackjack.get(user_id)
    if not data:
        return

    data['done'] = True
    player_score = hand_value(data['player'])

    dealer_score = hand_value(data['dealer'])
    while dealer_score < 17:
        data['dealer'].append(data['deck'].pop())
        dealer_score = hand_value(data['dealer'])

    player_display = " | ".join(data['player'])
    dealer_display = " | ".join(data['dealer'])

    if dealer_score > 21:
        win = data['bet'] * 2
        set_balance(user_id, get_balance(user_id) + win)
        result_text = f"🎉 У дилера перебор ({dealer_score})!\n+{win} монет"
    elif player_score > dealer_score:
        win = data['bet'] * 2
        set_balance(user_id, get_balance(user_id) + win)
        result_text = f"🎉 Ты выиграл! {player_score} > {dealer_score}\n+{win} монет"
    elif player_score == dealer_score:
        set_balance(user_id, get_balance(user_id) + data['bet'])
        result_text = f"🤝 Ничья! {player_score} = {dealer_score}\nСтавка возвращена"
    else:
        result_text = f"😢 Дилер выиграл! {dealer_score} > {player_score}\n-{data['bet']} монет"

    text = (
        f"🃏 Блэкджек — Итог\n\n"
        f"👤 Твои карты: {player_display}\n"
        f"📊 Твои очки: {player_score}\n\n"
        f"🏦 Карты дилера: {dealer_display}\n"
        f"📊 Очки дилера: {dealer_score}\n\n"
        f"{result_text}\n"
        f"💰 Баланс: {get_balance(user_id)}"
    )

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё раз", callback_data="blackjack_start")],
        [InlineKeyboardButton("🔙 В меню", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_blackjack[user_id]

async def blackjack_bust(query, user_id):
    data = user_blackjack.get(user_id)
    if not data:
        return
    data['done'] = True

    player_display = " | ".join(data['player'])
    player_score = hand_value(data['player'])
    dealer_display = " | ".join(data['dealer'])
    dealer_score = hand_value(data['dealer'])

    text = (
        f"🃏 Блэкджек — 💥 ПЕРЕБОР!\n\n"
        f"👤 Твои карты: {player_display}\n"
        f"📊 Твои очки: {player_score} (больше 21)\n\n"
        f"🏦 Карты дилера: {dealer_display}\n"
        f"📊 Очки дилера: {dealer_score}\n\n"
        f"😢 Ты проиграл!\n"
        f"-{data['bet']} монет\n"
        f"💰 Баланс: {get_balance(user_id)}"
    )

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё раз", callback_data="blackjack_start")],
        [InlineKeyboardButton("🔙 В меню", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_blackjack[user_id]

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
        [InlineKeyboardButton(f"💵 Ставка: {bet}", callback_data="betcalc_upgrade")],
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
    await query.edit_message_text(
        f"📈 Запускаем...\n{bar}\n0%",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏳ Идёт...", callback_data="none")
        ]])
    )

    context.job_queue.run_repeating(
        upgrade_step,
        interval=0.25,
        first=0.25,
        data={
            'user_id': user_id,
            'bet': bet,
            'percent': percent,
            'chat_id': query.message.chat_id,
            'message_id': query.message.message_id,
            'step': 0
        },
        name=f"upgrade_{user_id}"
    )

async def upgrade_step(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    step = data['step']
    user_id = data['user_id']
    chat_id = data['chat_id']
    message_id = data['message_id']
    bet = data['bet']
    percent = data['percent']

    if step >= PROGRESS_LENGTH:
        for job in context.job_queue.jobs():
            if job.name == f"upgrade_{user_id}":
                job.schedule_removal()

        win = random.randint(1, 100) <= percent
        bar = PROGRESS_FILL * PROGRESS_LENGTH
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
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"📈 Апгрейд завершён!\n{bar}\n100%\n\n{result_text}\nБаланс: {get_balance(user_id)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
        return

    filled = PROGRESS_FILL * (step + 1)
    empty = PROGRESS_EMPTY * (PROGRESS_LENGTH - step - 1)
    bar = filled + empty
    percentage = int(((step + 1) / PROGRESS_LENGTH) * 100)

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📈 Апгрейд... {percentage}%\n{bar}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏳ Идёт...", callback_data="none")
            ]])
        )
    except:
        pass

    data['step'] += 1

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

    if data.startswith("betcalc_"):
        return_to = data.replace("betcalc_", "")
        await show_bet_calculator(update, context, return_to)
        return

    if data.startswith("num_"):
        await handle_num_button(update, context)
        return

    if data.startswith("percent_"):
        await set_percent(update, context)
        return

    routes = {
        "main_menu": show_main_menu,
        "casino": casino_menu,
        "spin": spin_slots,
        "blackjack_menu": blackjack_menu,
        "blackjack_start": blackjack_start,
        "bj_hit": blackjack_hit,
        "bj_stand": blackjack_stand,
        "upgrade": upgrade_menu,
        "balance": show_balance,
        "select_percent": select_percent,
        "run_upgrade": run_upgrade,
        "take_money_again": take_money_again,
        "take_money": handle_start_choice,
        "no_money": handle_start_choice,
    }

    if data in routes:
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