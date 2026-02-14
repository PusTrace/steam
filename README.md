# Steam Trading Bot

Automated **Steam trading bot** for managing inventory, analyzing the market, and placing buy/sell orders.  
Handles authentication, 2FA, cookies, trading logic, and logging. Optional Telegram notifications supported.

---

## Features

- Analyze Steam inventory items using configurable strategies.
    
- Automatically decide which items to sell (`sell_skins.py`) or buy (`place_orders.py`).
    
- Keep the item database up-to-date (`soft_parser.py`).
    
- Logs all activity for monitoring bot performance.
    
- Handles Steam authentication and mobile confirmations via `sda.json`.
    
- Optional Telegram notifications for trading actions.
    

---

## Project Structure

```
.
├── analysis            # Data analysis and trading strategies
│   ├── cleaners.py
│   ├── features.py
│   ├── filters.py
│   ├── plot.py
│   └── strategies.py
├── config              # Credentials and configuration (not tracked in Git)
│   ├── cookies.json
│   ├── schedule.cron
│   └── sda.json
├── core                # Core logic
│   ├── db.py
│   ├── init.py
│   ├── logging_config.py
│   ├── Parsers.py
│   ├── node/
│   │   ├── get-cookies.js
│   │   └── package.json
│   └── steam/
│       ├── 2fa.py
│       ├── api.py
│       ├── confirmation.py
│       ├── cookies.py
│       ├── crypt.py
│       ├── orders.py
│       └── sell.py
├── logs                # Bot logs
├── modules             # High-level trading modules
│   ├── place_orders.py
│   ├── sell_skins.py
│   └── soft_parser.py
└── requirements.txt
```

---

## Requirements

- Python 3.x
    
- Node.js (for `get-cookies.js`)
    
- PostgreSQL database (see **Database setup**)
    

OS-independent, but tested on Linux/macOS.

---

## Setup

1. Clone the repository:
    

```bash
git clone https://github.com/PusTrace/steam.git
cd steam
```

2. Install Python dependencies:
    

```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies (for cookie fetching):
    

```bash
cd core/node
npm install
```

4. Create a `.env` file in the project root with credentials:
    

```env
# Steam account
STEAM_ACCOUNT=your_steam_username
STEAM_PASSWORD=your_steam_password
SHARED_SECRET=your_shared_secret

# Telegram bot (optional)
TG_BOT_TOKEN=your_bot_token
TG_CHAT_IDS=id1,id2,id3

# Internal default password
DEFAULT_PASSWORD=your_default_password
```

5. Configure Steam Mobile Auth in `config/sda.json`.
    

---

## Database Setup

Bot **requires a pre-existing PostgreSQL database**. Without it, modules will fail.  
The most important table is `skins`:

```sql
CREATE TABLE skins (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    item_name_id INTEGER NOT NULL,
    analysis_timestamp TIMESTAMP,
    appearance_date DATE,
    orders_timestamp TIMESTAMP,
    history_timestamp TIMESTAMP
);
```

Other tables (`orders`, `order_events`, `analysis_data`) are used for tracking orders, events, and analysis.  
You can create them using provided SQL dumps or empty tables.

💡 Minimum required: insert your inventory into `skins` with `name` and `item_name_id`.

---

## Usage

### Python Modules

- Sell items:
    

```bash
python3 modules/sell_skins.py
```

- Place buy orders:
    

```bash
python3 modules/place_orders.py
```

- Update database:
    

```bash
python3 modules/soft_parser.py
```

> **Note:** All modules require a working database. Insert at least `name` and `item_name_id` into `skins`.

### Node.js Script

Fetch cookies for Steam authentication:

```bash
cd core/node
node get-cookies.js
```

---

## Security Notes

- Never commit `config/` or `.env` files.
    
- Reset Steam password and 2FA if secrets are exposed.
    
- Store sensitive info only in `.env` and `sda.json`.
    

---

## Logs

Logs are stored in the `logs/` folder for monitoring trading activity and bot performance.
