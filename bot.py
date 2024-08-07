from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import datetime
from calendar import Calendar
from collections import Counter
import sqlite3

today = datetime.date.today()
year = today.year
calendar = Calendar()
selected_buttons = []
userid = None

app = Client("my_bot")
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS giorni(userid INTEGER, username TEXT, giorno INTEGER, password TEXT, data DATE)''')
c.execute('''CREATE TABLE IF NOT EXISTS eventi(userid INTEGER, username TEXT, nome_evento TEXT, month_evento INTEGER, password TEXT, data DATE)''')
conn.commit()

user_states = {}

def get_event_month_by_password(password):
    c.execute("SELECT month_evento FROM eventi WHERE password = ?", (password,))
    result = c.fetchone()
    if result:
        return result[0]
    return None

def get_selected_days(userid, month_event):
    c.execute("SELECT giorno FROM giorni WHERE userid = ? AND strftime('%m', data) = ?", (userid, f"{month_event:02}"))
    return [row[0] for row in c.fetchall()]

async def send_leaderboard_for_event(client, user_id, event_name, event_password):
    c.execute("SELECT giorno FROM giorni WHERE password = ?", (event_password,))
    days = [row[0] for row in c.fetchall()]
    
    if not days:
        await client.send_message(user_id, f"No days recorded for event: {event_name}")
        return
    
    day_counts = Counter(days)
    leaderboard = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)

    message_text = f"Leaderboard for event: {event_name}\n"
    for day, count in leaderboard:
        message_text += f"Day {day}: {count} times\n"

    await client.send_message(user_id, message_text)

@app.on_message(filters.command("start"))
async def start(client, message):
    global selected_buttons, userid
    userid = message.from_user.id
    selected_buttons = []

    await message.reply_text(
        "Hi, I'm a bot that helps you organize your events. Click on the button below to start.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Join event", callback_data="join_event"),
              InlineKeyboardButton("Create event", callback_data="create_event"),
              InlineKeyboardButton("Stats", callback_data="stats")]]
        )
    )

@app.on_callback_query()
async def on_button_click(client, query: CallbackQuery):
    global selected_buttons, user_states
    user_id = query.from_user.id

    if query.data == "create_event":
        user_states[user_id] = {'step': 'name_event'}
        await query.message.reply_text("Insert the name of the event:")

    elif query.data == "join_event":
        user_states[user_id] = {'step': 'join_password'}
        await query.message.reply_text("Insert the password of the event:")

    elif query.data == "stats":
        #tells the most common days for your events
        c.execute("SELECT nome_evento, password FROM eventi WHERE userid = ?", (user_id,))
        events = c.fetchall()
        for event in events:
            event_name, event_password = event
            await send_leaderboard_for_event(client, user_id, event_name, event_password)
    elif query.data == "send":
        await query.message.reply_text(f"You selected: {selected_buttons}\n If you want to change your selection, just type /start again.")
        username = query.from_user.username or query.from_user.first_name
        month_event = user_states[user_id]['month_event']
        month = month_event
        c.execute("DELETE FROM giorni WHERE userid = ? and password = ?", (userid, user_states[user_id]['password']))
        for i in calendar.itermonthdays(year, month):
            if i not in selected_buttons and i != 0:
                data = (query.from_user.id, username, i, user_states[user_id]['password'], today)
                c.execute("INSERT INTO giorni(userid, username, giorno, password, data) VALUES (?, ?, ?, ?, ?)", data)
        conn.commit()
        c.execute("SELECT * FROM giorni")
        for row in c.fetchall():
            print(row)

    elif query.data != "ignore":
        if user_id not in user_states:
            await query.message.reply_text("Please start the process again by typing /start.")
            return

        button_index = int(query.data.split('_')[1])
        if button_index in selected_buttons:
            selected_buttons.remove(button_index)
        else:
            selected_buttons.append(button_index)
        
        state = user_states[user_id]
        month_event = state['month_event']

        nome_evento = c.execute("SELECT nome_evento FROM eventi WHERE month_evento = ?", (month_event,)).fetchone()[0]
        name_event = [InlineKeyboardButton(nome_evento, callback_data="ignore")]
        month_name = [InlineKeyboardButton(datetime.date(year, month_event, 1).strftime("%B"), callback_data="ignore")]
        first_day_of_month = datetime.date(year, month_event, 1).weekday()
        empty_buttons = [InlineKeyboardButton(" ", callback_data="ignore") for _ in range(first_day_of_month)]
        days_of_week = [InlineKeyboardButton(day, callback_data="ignore") for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
        buttons = [InlineKeyboardButton(f"❌" if i in selected_buttons else f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, month_event) if i != 0]
        
        send_button = [InlineKeyboardButton("Send", callback_data="send")]

        inline_keyboard = InlineKeyboardMarkup(
            [name_event] + [month_name] + [days_of_week] + [empty_buttons + buttons[:7 - len(empty_buttons)]] + [buttons[i:i + 7] for i in range(7 - len(empty_buttons), len(buttons), 7)] + [send_button]
        )
        await query.edit_message_reply_markup(reply_markup=inline_keyboard)

@app.on_message(filters.private & filters.text)
async def on_message(client, message: Message):
    global user_states, selected_buttons
    user_id = message.from_user.id

    if user_id in user_states:
        state = user_states[user_id]

        if state['step'] == 'name_event':
            state['name_event'] = message.text
            state['step'] = 'month_event'
            await message.reply_text("Insert the month of the event (as a number, e.g., 6 for June):")

        elif state['step'] == 'month_event':
            state['month_event'] = int(message.text)
            state['step'] = 'password'
            await message.reply_text("Insert a password for the event:")

        elif state['step'] == 'password':
            password = message.text
            c.execute("SELECT * FROM eventi WHERE password = ?", (password,))
            if c.fetchone() is not None:
                await message.reply_text("Password already in use, please insert another one:")
                return

            state['password'] = password
            today_str = today.strftime('%Y-%m-%d')
            data = (user_id, message.from_user.username, state['name_event'], state['month_event'], state['password'], today_str)

            c.execute("INSERT INTO eventi(userid, username, nome_evento, month_evento, password, data) VALUES (?, ?, ?, ?, ?, ?)", data)
            conn.commit()
            await message.reply_text("Event created successfully!")

            del user_states[user_id]

        elif state['step'] == 'join_password':
            password = message.text
            event_month = get_event_month_by_password(password)
            if event_month is None:
                await message.reply_text("Password not found, please insert another one:")
                return
            
            c.execute("SELECT giorno FROM giorni WHERE userid = ? AND password = ?", (user_id, password))
            previous_choices = [row[0] for row in c.fetchall()]
            state['month_event'] = event_month
            state['password'] = password
            selected_buttons = get_selected_days(user_id, event_month)
            nome_evento = c.execute("SELECT nome_evento FROM eventi WHERE month_evento = ?", (event_month,)).fetchone()[0]
            name_event = [InlineKeyboardButton(nome_evento, callback_data="ignore")]
            month_name = [InlineKeyboardButton(datetime.date(year, event_month, 1).strftime('%B'), callback_data="ignore")]
            days_of_week = [InlineKeyboardButton(day, callback_data="ignore") for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
            first_day_of_month = datetime.date(year, event_month, 1).weekday()
            empty_buttons = [InlineKeyboardButton(" ", callback_data="ignore") for _ in range(first_day_of_month)]
            send_button = [InlineKeyboardButton("Send", callback_data="send")]
            
            if previous_choices:
                selected_buttons = [i for i in calendar.itermonthdays(year, event_month) if i != 0 and i not in previous_choices]
                buttons = [InlineKeyboardButton(f"❌" if i in selected_buttons else f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, event_month) if i != 0]
            else:
                buttons = [InlineKeyboardButton(f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, event_month) if i != 0]    
            
            inline_keyboard = InlineKeyboardMarkup(
                [name_event] + [month_name] + [days_of_week] + [empty_buttons + buttons[:7 - len(empty_buttons)]] + [buttons[i:i + 7] for i in range(7 - len(empty_buttons), len(buttons), 7)] + [send_button]
            )

            await message.reply_text("Select the days where you'll not be available:", reply_markup=inline_keyboard)
            user_states[user_id]['step'] = 'survey'

app.run()
conn.close()
