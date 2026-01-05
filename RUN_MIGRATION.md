# How to Run the Database Migration (Windows PowerShell)

Since Docker is not available, follow these steps to run the migration manually using your virtual environment.

## Step-by-Step Instructions

### Step 1: Activate Virtual Environment

Open PowerShell in your project directory and run:

```powershell
# Navigate to project directory (if not already there)
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Backup Your Database (Recommended)

```powershell
# Backup SQLite database
Copy-Item gmet_weather.db gmet_weather.db.backup
```

### Step 3: Check Current Migration Status

```powershell
# Check what migration is currently applied
.\venv\Scripts\alembic.exe current
```

### Step 4: Run the Migration

```powershell
# Apply the migration
.\venv\Scripts\alembic.exe upgrade head
```

### Step 5: Verify Migration

```powershell
# Check migration was applied
.\venv\Scripts\alembic.exe current

# Should show: b3c4d5e6f789 (head)
```

## Complete Command Sequence

Copy and paste these commands one by one in PowerShell:

```powershell
# 1. Navigate to project
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Backup database
Copy-Item gmet_weather.db gmet_weather.db.backup

# 4. Check current status
.\venv\Scripts\alembic.exe current

# 5. Run migration
.\venv\Scripts\alembic.exe upgrade head

# 6. Verify
.\venv\Scripts\alembic.exe current
```

## Alternative: Using Python Module

If the above doesn't work, try using Python module syntax:

```powershell
# Activate venv first
.\venv\Scripts\Activate.ps1

# Then run
python -m alembic upgrade head
```

## Expected Output

When you run `alembic upgrade head`, you should see:

```
INFO  [alembic.runtime.migration] Context impl AsyncImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 822df6608e6c -> b3c4d5e6f789, Update to synoptic observations at 0600/0900/1200/1500 and daily summaries
```

## Troubleshooting

### If you get "Python was not found"

Make sure you activated the virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```

### If you get execution policy error

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### If migration fails

1. Check the error message
2. Restore backup: `Copy-Item gmet_weather.db.backup gmet_weather.db`
3. Check `alembic.ini` has correct database path: `sqlalchemy.url = sqlite:///gmet_weather.db`

### Verify Database Changes

After migration, you can verify the new tables exist using a SQLite browser or Python:

```powershell
# Using Python (after activating venv)
python -c "import sqlite3; conn = sqlite3.connect('gmet_weather.db'); cursor = conn.cursor(); cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('synoptic_observations', 'daily_summaries')\"); print(cursor.fetchall())"
```

## What the Migration Does

1. Creates `synoptic_observations` table
2. Creates `daily_summaries` table  
3. Migrates data from old `observations` table to `synoptic_observations`
4. Drops the old `observations` table

Your existing data will be preserved and migrated to the new structure.

