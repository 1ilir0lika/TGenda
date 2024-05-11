from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import datetime
from calendar import Calendar
import sqlite3

today = datetime.date.today()
month = today.month
year = today.year
calendar = Calendar()
selected_buttons = []
userid = None

app = Client("my_account")
conn=sqlite3.connect('giorni.db')
c=conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS giorni(userid integer,username string,giorno integer,data date)''')
@app.on_message(filters.command("start"))
async def start(client, message):
    global selected_buttons
    global userid
    userid = message.from_user.id
    selected_buttons = []
    # Fetch previous choices from the database
    c.execute("SELECT giorno FROM giorni WHERE userid = ?", (userid,))
    previous_choices = c.fetchall()
    previous_choices = [choice[0] for choice in previous_choices] if previous_choices else []
    month_name = [InlineKeyboardButton(today.strftime("%B"), callback_data="ignore")]
    days_of_week = [InlineKeyboardButton(day, callback_data="ignore") for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
    first_day_of_month = datetime.date(year, month, 1).weekday()
    empty_buttons = [InlineKeyboardButton(" ", callback_data="ignore") for _ in range(first_day_of_month)]
    send_button = [InlineKeyboardButton("Send", callback_data="send")]
    if previous_choices!=[]:
      #le scelte precedenti sono dei giorni che sono disponibili,io voglio i giorni che non sono disponibili
      selected_buttons = [i for i in calendar.itermonthdays(year, month) if i != 0 and i not in previous_choices]
      # Fetch previous choices from the database
      buttons = [InlineKeyboardButton(f"❌" if i in selected_buttons else f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, month) if i != 0]
    else:
      buttons = [InlineKeyboardButton(f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, month) if i != 0]    
    inline_keyboard = InlineKeyboardMarkup([month_name] + [days_of_week] + [empty_buttons + buttons[:7-len(empty_buttons)]] + [buttons[i:i+7] for i in range(7-len(empty_buttons), len(buttons), 7)] + [send_button])
    await message.reply_text("choose the days where you'll not be avaible", reply_markup=inline_keyboard)

@app.on_callback_query()
async def on_button_click(client: Client, query: CallbackQuery):
    global selected_buttons
    if query.data == "send":
        await query.message.reply_text(f"You selected: {selected_buttons} \n if you wanna change your selection just type /start again")
        #print username and selected_buttons
        print(query.from_user.username + " " + str(selected_buttons))
        # Delete previous choices from the database
        c.execute("DELETE FROM giorni WHERE userid = ?", (userid,))
        #commit to db all the days that they can
        for i in calendar.itermonthdays(year, month):
          if i not in selected_buttons and i!=0:
                data=(query.from_user.id,query.from_user.username,i,today)
                c.execute("INSERT INTO giorni(userid,username,giorno,data) VALUES (?,?,?,?)",data)
        conn.commit()
        #print the database
        c.execute("SELECT * FROM giorni")
        for row in c.fetchall():
          print(row)
    elif query.data != "ignore":
        button_index = query.data.split('_')[1]  # Extract button index from callback_data
        button_index = int(button_index)
        if button_index not in selected_buttons:
            selected_buttons.append(button_index)  # Add button index to selected buttons list
        else:
            selected_buttons.remove(button_index)
        month_name = [InlineKeyboardButton(today.strftime("%B"), callback_data="ignore")]
        first_day_of_month = datetime.date(year, month, 1).weekday()
        empty_buttons = [InlineKeyboardButton(" ", callback_data="ignore") for _ in range(first_day_of_month)]
        days_of_week = [InlineKeyboardButton(day, callback_data="ignore") for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
        buttons = [InlineKeyboardButton(f"❌" if i in selected_buttons else f"{i}", callback_data=f"button_{i}") for i in calendar.itermonthdays(year, month) if i != 0]
        send_button = [InlineKeyboardButton("Send", callback_data="send")]
        inline_keyboard = InlineKeyboardMarkup([month_name] + [days_of_week] + [empty_buttons + buttons[:7-len(empty_buttons)]] + [buttons[i:i+7] for i in range(7-len(empty_buttons), len(buttons), 7)] + [send_button])
        await query.edit_message_reply_markup(reply_markup=inline_keyboard)

app.run()
conn.close()
