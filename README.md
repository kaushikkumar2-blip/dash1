# FDP Query Automation Agent

Automated agent that logs into `fdp.fkinternal.com`, runs a SQL query, downloads the results, and pushes them to GitHub — on a daily schedule.

## How It Works

1. **Windows Task Scheduler** triggers `run_scraper.bat` daily at the configured time
2. **Playwright** launches a headless Chromium browser
3. The agent logs in via LDAP, navigates to the query page, and executes your SQL
4. It waits for results, clicks Download, and saves the file to `data/`
5. The file is **auto-committed and pushed** to your GitHub repository

## Setup

### 1. Install Python dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your LDAP credentials:

```
FDP_USERNAME=your_username
FDP_PASSWORD=your_password
```

These are loaded as environment variables — never committed to git.

### 3. Set your SQL query

Edit `query.sql` with the query you want to run:

```sql
SELECT * FROM your_table WHERE date = CURRENT_DATE
```

### 4. Configure the site selectors

Edit `config.yaml` if the default CSS selectors don't match the FDP page. Key fields:

- `login.username_selector` — the login form username input
- `login.password_selector` — the login form password input
- `query.text_area_selector` — the SQL editor on the query page
- `query.run_button_selector` — the Run/Execute button
- `download.button_selector` — the Download/Export button

### 5. Connect to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

### 6. Test a manual run

```bash
.venv\Scripts\activate
set FDP_USERNAME=your_username
set FDP_PASSWORD=your_password
python scraper.py
```

Tip: set `browser.headless: false` in `config.yaml` to watch it run and verify selectors are correct.

### 7. Schedule daily runs

Run `setup_scheduler.bat` **as Administrator**. It creates a Windows Task Scheduler entry that runs daily at 08:00.

To change the time, edit `RUN_TIME` in `setup_scheduler.bat` and re-run it.

## Project Structure

```
├── config.yaml             # All scraper settings (URL, selectors, schedule)
├── query.sql               # Your SQL query (loaded by the scraper)
├── scraper.py              # Main automation agent
├── run_scraper.bat         # Launcher script (loads .env, runs scraper)
├── setup_scheduler.bat     # One-time setup for Windows Task Scheduler
├── requirements.txt        # Python dependencies
├── .env.example            # Credential template
├── .gitignore              # Excludes .env, downloads, caches
├── data/                   # Output folder (auto-created)
│   └── fdp_data_YYYY-MM-DD.csv
└── README.md
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Login fails | Check `login.*_selector` values in `config.yaml` match the actual form |
| Query doesn't type | Try different `text_area_selector`; some editors use CodeMirror |
| Download times out | Increase `download.wait_ms` in `config.yaml` |
| Git push fails | Ensure `git remote` is set and you have push access |
| Can't see what's happening | Set `browser.headless: false` to watch the browser |
