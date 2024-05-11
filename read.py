import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('giorni.db')
c = conn.cursor()

# Execute the SQL query to fetch all data
c.execute('SELECT * FROM giorni')

# Fetch and print all data
print("All data in 'giorni' table:")
for row in c.fetchall():
    print(row)

# Execute the SQL query to get the leaderboard
c.execute('''
    SELECT giorno, COUNT(*) AS count
    FROM giorni
    GROUP BY giorno
    ORDER BY count DESC
''')

# Fetch and print the leaderboard
print("\nLeaderboard - Most Common Days:")
for day in c.fetchall():
    print("Giorno:", day[0], "- Count:", day[1])

# Close the connection
conn.close()