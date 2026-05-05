# Rates & Credit Monitor — How to Run This

Hey 👋 — this is a step-by-step guide. No prior coding knowledge needed.

You have two options:

- **Option A: Run it on your own computer** (5 minutes, you keep it private)
- **Option B: Put it on the internet** (15 minutes, you get a link to share)

Pick whichever you want. Option A is easier — start there.

---

## Option A: Run it on your own computer

### Step 1 — Install Python (one-time, skip if you already have it)

Python is the language the app is written in. You need it on your computer.

**On Mac:**
1. Open the **Terminal** app (press `Cmd + Space`, type "terminal", press Enter)
2. Copy-paste this line and press Enter:
   ```
   python3 --version
   ```
3. If you see something like `Python 3.10.x` or higher, you're good ✅. Skip to Step 2.
4. If you get an error, go to [python.org/downloads](https://www.python.org/downloads/) and download the latest version. Run the installer, click "Next" through everything.

**On Windows:**
1. Open **Command Prompt** (press `Windows key`, type "cmd", press Enter)
2. Type:
   ```
   python --version
   ```
3. If you see `Python 3.10.x` or higher, you're good ✅.
4. If not, go to [python.org/downloads](https://www.python.org/downloads/) → download → run installer.
   ⚠️ **IMPORTANT**: On the first install screen, tick the box that says **"Add Python to PATH"** before clicking Install. Otherwise nothing will work.

### Step 2 — Open the project folder in Terminal

You should have a folder called `rates_monitor` somewhere (Downloads, Desktop, wherever you put it). It contains `app.py`, `README.md`, `requirements.txt`, and a `data` folder.

**On Mac:**
1. Open Terminal
2. Type `cd ` (with a space after it — don't press Enter yet)
3. Drag the `rates_monitor` folder from Finder into the Terminal window. The path will fill in automatically.
4. Press Enter.

**On Windows:**
1. Open the `rates_monitor` folder in File Explorer
2. Click in the address bar at the top, delete what's there, type `cmd`, press Enter
3. A black Command Prompt window will open, already in the right folder ✅

### Step 3 — Install the app's helpers (one-time)

The app uses a few Python tools (Streamlit, pandas, plotly). Install them all at once.

Copy-paste this line into your Terminal/Command Prompt and press Enter:

**Mac:**
```
pip3 install -r requirements.txt
```

**Windows:**
```
pip install -r requirements.txt
```

You'll see a wall of text scroll by for 1–2 minutes. When it stops and you can type again, you're done.

### Step 4 — Run the app

Copy-paste this and press Enter:

**Mac:**
```
streamlit run app.py
```

**Windows:**
```
streamlit run app.py
```

Your web browser will pop open automatically with the dashboard. If it doesn't, look at the Terminal — it'll say something like `Local URL: http://localhost:8501`. Copy that into your browser.

🎉 **That's it.** You're running the dashboard.

### To stop the app

Go back to the Terminal window and press `Ctrl + C` (yes, even on Mac — `Ctrl`, not `Cmd`).

### To run it again later

Just do Steps 2 and 4. You only do Steps 1 and 3 once, ever.

---

## Option B: Put it on the internet

This gives you a link like `your-app.streamlit.app` that you (or anyone you share it with) can open from any browser, no setup needed.

This is **free** through a service called Streamlit Community Cloud, but it requires a GitHub account.

### Step 1 — Make a GitHub account (free)

1. Go to [github.com](https://github.com)
2. Click **Sign up**, follow the prompts. Pick any username.

### Step 2 — Upload your folder to GitHub

1. Once logged in, click the **+** icon in the top right → **New repository**
2. Give it a name like `rates-monitor`. Leave it **Public** (or Private — both work).
3. Click **Create repository**.
4. On the next page, click **"uploading an existing file"** (it's a blue link).
5. Drag your entire `rates_monitor` folder contents into the upload box — `app.py`, `README.md`, `requirements.txt`, AND the `data` folder with `DATA.xlsx` inside.
6. Scroll down, click **Commit changes**.

### Step 3 — Deploy with Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **Sign in with GitHub** — it'll ask for permission, allow it.
3. Click **Create app** → **Deploy a public app from GitHub**
4. Pick the repository you just made (`rates-monitor`)
5. In **Main file path**, type: `app.py`
6. Click **Deploy**

Wait 1–2 minutes. You'll get a link like `https://your-name-rates-monitor.streamlit.app` — bookmark it. That's your dashboard, live on the internet.

### To update the data later

When your `DATA.xlsx` gets refreshed:
1. Go to your GitHub repo → click into the `data` folder → click `DATA.xlsx`
2. Click the trash icon to delete it
3. Go back, click **Add file → Upload files**, drop your new `DATA.xlsx` in
4. Commit. Streamlit will auto-redeploy in ~1 minute.

---

## What's in the dashboard

Five sections, top to bottom:

1. **Curve slopes** — 12 small charts showing 2s10s and 5s30s for the major countries
2. **Real rates** — 6 charts of 10Y inflation-linked yields
3. **Money-market spreads** — 5 stacked charts showing funding stress in the US system
4. **XCCY basis swaps** — 5 charts on dollar funding pressure across currencies
5. **Credit** — 1 big chart with IG, HY, EMBI, and bank CDS

The **left sidebar** has a date selector. Pick 1Y, 3Y, etc. to zoom every chart at once. Hover over any line for the daily numbers.

---

## When something goes wrong

**"streamlit: command not found"**
→ The install in Step 3 didn't finish. Re-run Step 3, watch for any red error text.

**"No module named pandas" (or plotly, openpyxl)**
→ Same fix — re-run Step 3.

**The app opens but a section is empty**
→ Some Bloomberg series have gaps. Try a longer lookback (5Y or Max) in the sidebar.

**Nothing makes sense**
→ Take a screenshot, send it to me, I'll talk you through it.
