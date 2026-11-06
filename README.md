# 🍜 Campus Food Tracker

A Streamlit app for university food stalls. Students can order from stalls and track their food spending. Vendors can manage their menu, handle orders and see which items sell best.

## Features

**Students**
- Register and log in with a TP number
- Browse stalls, view menus and place orders
- Track order status and cancel while the order is still Pending
- View order history
- Filter and track spending by date and stall, with an optional budget bar

**Vendors**
- Register a stall and log in via a stall-name dropdown
- Add, edit, hide or delete menu items and prices
- Update order status (Preparing, Ready, Collected) or cancel orders
- View sales reports, best-selling items and download CSV

## Requirements

- [Python 3.9+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## How to run

**1. Clone the repository**
```bash
git clone https://github.com/limjiatong/campus-food-tracker.git
cd campus-food-tracker
```

**2. (Recommended) Create a virtual environment**

Mac/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Start the app**
```bash
streamlit run campus_food_app.py
```

Your browser should open automatically. If not, go to http://localhost:8501.

## First-time use

1. Open the app and choose **Vendor**, then **Register new account** to create a stall.
2. Log in as that vendor and add some menu items under **Manage menu**.
3. Log out, choose **Student**, register with a TP number and log in.
4. Browse the stall, place an order, then log back in as the vendor to update its status.

To try both sides at once, open the app in a second browser window (or an incognito window) so the two logins don't overwrite each other.

## Notes

- Data is stored in a local SQLite file, `campus_food.db`, created automatically on first run. To reset everything, stop the app and delete that file.
- The database is listed in `.gitignore` and should not be committed, because it contains student details.
- Pages don't refresh by themselves. Use the **Refresh** button to see new orders or status changes.
- Prices are shown in RM. Change `CURRENCY` at the top of `campus_food_app.py` to use another currency.

## Troubleshooting

| Problem | Fix |
|---|---|
| `File does not exist: campus_food_app.py` | Run the command from inside the project folder (use `cd`) |
| `streamlit: command not found` | Activate your virtual environment, or run `python -m streamlit run campus_food_app.py` |
| Port already in use | Run `streamlit run campus_food_app.py --server.port 8502` |

## Project structure

```
campus-food-tracker/
├── campus_food_app.py   # the whole app
├── requirements.txt
├── .gitignore
└── README.md
```
