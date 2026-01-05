# PowerShell script to check database tables
python -c "import sqlite3; conn = sqlite3.connect('gmet_weather.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\''); tables = [t[0] for t in cursor.fetchall()]; print('Tables:', tables); conn.close()"

