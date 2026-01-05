# How to Run Database Migration on Windows (Step-by-Step)

## Quick Start Commands

Open **PowerShell** in your project folder and run these commands:

```powershell
# 1. Navigate to project (if not already there)
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. If you get execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Fix dependencies (if needed)
pip install --upgrade pydantic pydantic-core

# 5. Backup database
Copy-Item gmet_weather.db gmet_weather.db.backup

# 6. Run migration
python -m alembic upgrade head

# 7. Verify
python -m alembic current
```

## Detailed Instructions

### Step 1: Open PowerShell

1. Press `Windows Key + X`
2. Select "Windows PowerShell" or "Terminal"
3. Navigate to your project:
   ```powershell
   cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"
   ```

### Step 2: Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

**If you see an execution policy error**, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again.

### Step 3: Fix Dependencies (If Needed)

If you get errors about missing modules, reinstall dependencies:

```powershell
# Make sure you're in the activated venv (you should see (venv) in prompt)
pip install --upgrade -r requirements.txt
```

### Step 4: Backup Database

**IMPORTANT**: Always backup before migration!

```powershell
Copy-Item gmet_weather.db gmet_weather.db.backup
```

### Step 5: Check Current Status

```powershell
python -m alembic current
```

This shows what migration is currently applied.

### Step 6: Run Migration

```powershell
python -m alembic upgrade head
```

### Step 7: Verify Migration

```powershell
python -m alembic current
```

Should show: `b3c4d5e6f789 (head)`

## Complete Command Sequence

Copy and paste this entire block into PowerShell:

```powershell
# Navigate to project
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Fix execution policy if needed (run once)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Fix dependencies
pip install --upgrade pydantic pydantic-core alembic sqlalchemy

# Backup database
Copy-Item gmet_weather.db gmet_weather.db.backup

# Check current migration
python -m alembic current

# Run migration
python -m alembic upgrade head

# Verify
python -m alembic current
```

## Expected Output

When migration runs successfully, you'll see:

```
INFO  [alembic.runtime.migration] Context impl AsyncImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 822df6608e6c -> b3c4d5e6f789, Update to synoptic observations at 0600/0900/1200/1500 and daily summaries
```

## Troubleshooting

### Error: "Python was not found"
- Make sure virtual environment is activated (you should see `(venv)` in your prompt)
- Try: `.\venv\Scripts\python.exe -m alembic upgrade head`

### Error: "Execution policy"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "ModuleNotFoundError: No module named 'pydantic_core'"
```powershell
pip install --upgrade pydantic pydantic-core
```

### Error: "No such table: observations"
This means the old table doesn't exist. The migration will still work - it will just skip the data migration step.

### Migration Fails
1. Restore backup: `Copy-Item gmet_weather.db.backup gmet_weather.db`
2. Check error message
3. Make sure `alembic.ini` has: `sqlalchemy.url = sqlite:///gmet_weather.db`

## Verify Database Changes

After migration, verify new tables exist:

```powershell
python -c "import sqlite3; conn = sqlite3.connect('gmet_weather.db'); cursor = conn.cursor(); tables = cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('synoptic_observations', 'daily_summaries')\").fetchall(); print('Tables found:', tables)"
```

Should show:
```
Tables found: [('synoptic_observations',), ('daily_summaries',)]
```

## What Gets Changed

✅ Creates `synoptic_observations` table  
✅ Creates `daily_summaries` table  
✅ Migrates data from `observations` → `synoptic_observations`  
✅ Drops old `observations` table  

Your data is preserved during migration!

