# Gram Network Bot Scripts 🚀

This collection of Python scripts automates tasks and mining on the **Gram Network** platform — a Telegram-based Web3 ecosystem where users earn GRM tokens by completing social tasks and running mining sessions.

🔗 Register: [Gram Network](https://t.me/Gramnetwork_bot?startapp=921415493)

---

## ✨ Features Overview

### General Features

- **Multi-Account Support**: Reads Telegram initData from `accounts.txt` to process multiple accounts in parallel.
- **Colorful CLI**: Uses `colorama` for visually appealing output with box-drawing borders and colored icons.
- **Asynchronous Execution**: Built with `asyncio` for efficient concurrent task processing (configurable thread count).
- **Error Handling**: Comprehensive error catching with retry logic (configurable attempts) for API failures.
- **Bilingual Support**: Supports both English and Vietnamese output.
- **Proxy Support**: Supports SOCKS5 proxies via `proxies.txt` (`host:port:user:pass` format).

---

### Included Scripts

✨ **Task Bot** (`social.py`)

- ✅ Automatic task listing & completion
- ✅ X (Twitter) Like & Retweet tasks
- ✅ YouTube watch, like & subscribe tasks
- ✅ Facebook follow & share tasks
- ✅ Telegram channel & bot join tasks
- ✅ Wallet app join tasks (OKX, Bitget, MyTonWallet, CryptoBot)
- ✅ Boost & vote tasks
- ✅ Secure referer headers included
- ✅ Proxy & multi-threading support

✨ **Mining Bot** (`mining.py`)

- ✅ Automatic mining start for inactive accounts
- ✅ Detailed mining info display: Status, Rate, Power, Time Left, Tokens Earned, Energy
- ✅ Balance & USD value display
- ✅ Daily reward & referral info
- ✅ Automatic re-fetch after mining start
- ✅ Proxy & multi-threading support

✨ **Boost Bot** (`boost.py`)

- ✅ Automatic check Boost availability
- ✅ Display current Mining Power & Active Boost
- ✅ One-click Boost activation (+5 GH/s & +0.1 GRM)
- ✅ Show Boost cooldown timer
- ✅ Proxy & multi-threading support

---

## 🛠️ Prerequisites

Before running the scripts, ensure you have the following installed:

- **Python 3.8+**
- **pip** (Python package manager)
- **Dependencies**: Install via `pip install -r requirements.txt`
- **accounts.txt**: Add Telegram initData (one per line) — obtain via browser DevTools on the Gram Network mini app
- **proxies.txt** (optional): Add proxy addresses for network requests

---

## 📦 Installation

1. **Clone or download this repository:**
   ```sh
   git clone https://github.com/thog9/Gramnetwork-telegram.git
   cd Gramnetwork-telegram
   ```

2. **Install Dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Prepare Input Files:**

   Create `accounts.txt` in the root directory with Telegram query data (one per line):
   ```
   query_id=AAFFr-s9AAAAA...
   query_id=AAFFr-s9AAAAA...
   ```

   Create `proxy.txt` (optional) — one proxy per line:
   ```
   http://user:pass@ip:port
   socks5://user:pass@ip:port
   ```

4. **Run:**
   ```sh
   python main.py
   ```
   - Choose a language (Vietnamese / English).
   - Select the script you want to run.

**Language Selection:**
- Choose between Vietnamese (Tiếng Việt) and English.
- All scripts support bilingual output.

---

## 📁 Project Structure

```
Gram-Network/
├── main.py                # Central menu system
├── accounts.txt           # Telegram initData
├── proxies.txt            # Proxies (optional)
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── scripts/               # Individual scripts
    ├── social.py          # Task automation bot
    ├── mining.py          # Mining automation bot
    └── boost.py           # Boost Power bot

```

---

## 📨 Contact

Connect with us for support or updates:

- **Telegram**: [thog099](https://t.me/thog099)
- **Channel**: [CHANNEL](https://t.me/thogairdrops)
- **Group**: [GROUP CHAT](https://t.me/thogchats)
- **X**: [Thog](https://x.com/thog099)

---

## ☕ Support Us

Love these scripts? Fuel our work with a coffee!

🔗 BUYMECAFE: [BUY ME CAFE](https://buymecafe.vercel.app/)

🔗 WEBSITE: [BUY SCRIPTS](https://thogtoolhub.com/)