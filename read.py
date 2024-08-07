import sqlite3
from collections import Counter

# Connect to the SQLite database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Function to print leaderboard for each event
def print_leaderboard_for_event(event_name, event_password):
    c.execute("SELECT giorno FROM giorni WHERE password = ?", (event_password,))
    days = [row[0] for row in c.fetchall()]
    
    if not days:
        print(f"No days recorded for event: {event_name}")
        return
    
    day_counts = Counter(days)
    leaderboard = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"Leaderboard for event: {event_name}")
    for day, count in leaderboard:
        print(f"Day {day}: {count} people")
    print()

# Iterate through every event and print a leaderboard of the most common days
c.execute("SELECT nome_evento, password FROM eventi")
events = c.fetchall()

for event in events:
    event_name, event_password = event
    print_leaderboard_for_event(event_name, event_password)

# Close the connection
conn.close()
