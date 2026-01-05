# Fix Greenlet Issue for Migration

The migration is failing because greenlet's compiled extension is missing. Here's how to fix it:

## Solution: Reinstall Greenlet

**Close all Python processes first** (including any IDEs, terminals running Python, etc.), then run:

```powershell
# Make sure you're in the project directory
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Force reinstall greenlet
pip uninstall greenlet -y
pip install --no-cache-dir greenlet

# Try migration again
.\venv\Scripts\python.exe -m alembic upgrade head
```

## Alternative: Reinstall All Dependencies

If the above doesn't work, reinstall all dependencies:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Reinstall requirements
pip install --force-reinstall --no-cache-dir -r requirements.txt

# Try migration
.\venv\Scripts\python.exe -m alembic upgrade head
```

## If Still Failing: Use Offline Mode

As a last resort, you can run the migration in offline mode (but this won't work for data migration):

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head --sql > migration.sql
```

Then manually execute the SQL file.

