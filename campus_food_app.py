"""
Campus Food Tracker - Streamlit app
Run:  pip install streamlit pandas
      streamlit run campus_food_app.py
Data is stored in a local SQLite file (campus_food.db), created automatically.
"""
import hashlib
import hmac
import os
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

DB_PATH = "campus_food.db"
CURRENCY = "RM"
ACTIVE_STATUSES = ("Pending", "Preparing", "Ready")
STATUS_ICON = {"Pending": "🕒", "Preparing": "👨‍🍳", "Ready": "✅",
               "Completed": "📦", "Cancelled": "❌"}

st.set_page_config(page_title="Campus Food Tracker", page_icon="🍜", layout="wide")


# ------------------------------------------------------------------ database
def run(sql, params=(), fetch=False, one=False):
    """Run a query. fetch=True returns list of dicts (or one dict if one=True)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        if fetch:
            rows = [dict(r) for r in cur.fetchall()]
            return (rows[0] if rows else None) if one else rows
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students(
        tp_number TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL UNIQUE,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS menu_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER NOT NULL REFERENCES vendors(id),
        name TEXT NOT NULL,
        price REAL NOT NULL,
        available INTEGER NOT NULL DEFAULT 1,
        deleted INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tp_number TEXT NOT NULL REFERENCES students(tp_number),
        vendor_id INTEGER NOT NULL REFERENCES vendors(id),
        status TEXT NOT NULL DEFAULT 'Pending',
        total REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES orders(id),
        item_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        qty INTEGER NOT NULL
    );
    """)
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ security
def hash_pw(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return salt.hex() + "$" + digest.hex()


def verify_pw(password, stored):
    salt_hex, digest_hex = stored.split("$")
    new = hash_pw(password, bytes.fromhex(salt_hex)).split("$")[1]
    return hmac.compare_digest(new, digest_hex)


# ------------------------------------------------------------------ helpers
def money(x):
    return f"{CURRENCY} {x:,.2f}"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def order_items_text(order_id):
    items = run("SELECT item_name, qty FROM order_items WHERE order_id=?",
                (order_id,), fetch=True)
    return ", ".join(f"{i['qty']}× {i['item_name']}" for i in items)


def date_range_picker(label, key, default_days=30):
    today = date.today()
    picked = st.date_input(label, value=(today - timedelta(days=default_days), today), key=key)
    if isinstance(picked, (tuple, list)):
        if len(picked) == 2:
            return picked[0], picked[1]
        if len(picked) == 1:
            return picked[0], picked[0]
    return picked, picked


def logout():
    for k in ("role", "user"):
        st.session_state.pop(k, None)
    st.rerun()


# ------------------------------------------------------------------ auth page
def auth_page():
    st.title("🍜 Campus Food Tracker")
    st.caption("Order from campus stalls, track what you spend, and help vendors see what's popular.")
    role = st.radio("I am a…", ["Student", "Vendor"], horizontal=True)
    tab_login, tab_reg = st.tabs(["Log in", "Register new account"])

    if role == "Student":
        with tab_login:
            with st.form("student_login"):
                tp = st.text_input("TP number").strip().upper()
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary"):
                    s = run("SELECT * FROM students WHERE tp_number=?", (tp,), fetch=True, one=True)
                    if s and verify_pw(pw, s["password"]):
                        st.session_state.update(role="student", user=s)
                        st.rerun()
                    else:
                        st.error("Invalid TP number or password.")
        with tab_reg:
            with st.form("student_reg"):
                tp = st.text_input("TP number (e.g. TP012345)").strip().upper()
                name = st.text_input("Full name").strip()
                pw = st.text_input("Password", type="password")
                pw2 = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create student account"):
                    if not (tp and name and pw):
                        st.error("Please fill in all fields.")
                    elif pw != pw2:
                        st.error("Passwords do not match.")
                    elif len(pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif run("SELECT 1 FROM students WHERE tp_number=?", (tp,), fetch=True):
                        st.error("That TP number is already registered.")
                    else:
                        run("INSERT INTO students VALUES (?,?,?)", (tp, name, hash_pw(pw)))
                        st.success("Account created! Switch to the Log in tab.")
    else:
        with tab_login:
            shops = run("SELECT * FROM vendors ORDER BY shop_name", fetch=True)
            if not shops:
                st.info("No stalls registered yet. Register one in the next tab.")
            else:
                with st.form("vendor_login"):
                    shop = st.selectbox("Stall name", [s["shop_name"] for s in shops])
                    uname = st.text_input("Username").strip()
                    pw = st.text_input("Password", type="password")
                    if st.form_submit_button("Log in", type="primary"):
                        v = run("SELECT * FROM vendors WHERE shop_name=? AND username=?",
                                (shop, uname), fetch=True, one=True)
                        if v and verify_pw(pw, v["password"]):
                            st.session_state.update(role="vendor", user=v)
                            st.rerun()
                        else:
                            st.error("Invalid username or password for that stall.")
        with tab_reg:
            with st.form("vendor_reg"):
                shop = st.text_input("Shop name").strip()
                uname = st.text_input("Username").strip()
                pw = st.text_input("Password", type="password")
                pw2 = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create vendor account"):
                    if not (shop and uname and pw):
                        st.error("Please fill in all fields.")
                    elif pw != pw2:
                        st.error("Passwords do not match.")
                    elif len(pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif run("SELECT 1 FROM vendors WHERE shop_name=? OR username=?",
                             (shop, uname), fetch=True):
                        st.error("Shop name or username already taken.")
                    else:
                        run("INSERT INTO vendors(shop_name, username, password) VALUES (?,?,?)",
                            (shop, uname, hash_pw(pw)))
                        st.success("Account created! Log in, then add your menu items.")


# ================================================================== STUDENT
def student_browse(student):
    st.header("🏪 Browse stalls")
    vendors = run("""SELECT v.id, v.shop_name,
                     (SELECT COUNT(*) FROM menu_items m
                      WHERE m.vendor_id=v.id AND m.available=1 AND m.deleted=0) AS n_items
                     FROM vendors v ORDER BY v.shop_name""", fetch=True)
    if not vendors:
        st.info("No stalls available yet.")
        return
    labels = {f"{v['shop_name']}  ({v['n_items']} items available)": v for v in vendors}
    vendor = labels[st.selectbox("Choose a stall", list(labels))]

    items = run("""SELECT * FROM menu_items WHERE vendor_id=? AND available=1 AND deleted=0
                   ORDER BY name""", (vendor["id"],), fetch=True)
    st.subheader(f"{vendor['shop_name']} – Menu")
    if not items:
        st.warning("This stall has no items on the menu right now.")
        return

    ver = st.session_state.setdefault("cart_version", 0)
    with st.form(f"menu_form_{vendor['id']}_{ver}"):
        qtys = {}
        for it in items:
            c1, c2, c3 = st.columns([4, 2, 2])
            c1.markdown(f"**{it['name']}**")
            c2.write(money(it["price"]))
            qtys[it["id"]] = c3.number_input("Qty", 0, 20, 0, key=f"q_{ver}_{it['id']}",
                                             label_visibility="collapsed")
        submitted = st.form_submit_button("Check out", type="primary")

    if submitted:
        chosen = [(it, qtys[it["id"]]) for it in items if qtys[it["id"]] > 0]
        if not chosen:
            st.warning("Select at least one item.")
            return
        total = sum(it["price"] * q for it, q in chosen)
        oid = run("INSERT INTO orders(tp_number, vendor_id, status, total, created_at) VALUES (?,?,?,?,?)",
                  (student["tp_number"], vendor["id"], "Pending", total, now_str()))
        for it, q in chosen:
            run("INSERT INTO order_items(order_id, item_name, unit_price, qty) VALUES (?,?,?,?)",
                (oid, it["name"], it["price"], q))
        st.session_state["cart_version"] = ver + 1
        st.session_state["flash"] = f"Order #{oid} placed – total {money(total)}. Track it under 'My orders'."
        st.rerun()


def student_orders(student):
    st.header("📋 My orders")
    if st.button("🔄 Refresh"):
        st.rerun()
    orders = run("""SELECT o.*, v.shop_name FROM orders o JOIN vendors v ON v.id=o.vendor_id
                    WHERE o.tp_number=? AND o.status IN ('Pending','Preparing','Ready')
                    ORDER BY o.id DESC""", (student["tp_number"],), fetch=True)
    if not orders:
        st.info("You have no active orders.")
        return
    for o in orders:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**Order #{o['id']}** · {o['shop_name']} · {o['created_at']}")
            c1.write(order_items_text(o["id"]))
            c1.write(f"Total: **{money(o['total'])}**")
            c2.markdown(f"### {STATUS_ICON[o['status']]} {o['status']}")
            if o["status"] == "Pending":
                if c2.button("Cancel order", key=f"cancel_{o['id']}"):
                    run("UPDATE orders SET status='Cancelled' WHERE id=? AND status='Pending'", (o["id"],))
                    st.rerun()
            else:
                c2.caption("Can't cancel once the stall starts preparing.")


def load_student_history(tp):
    rows = run("""SELECT o.id AS order_id, o.created_at, v.shop_name AS stall, o.status, o.total,
                  GROUP_CONCAT(oi.qty || 'x ' || oi.item_name, ', ') AS items
                  FROM orders o JOIN vendors v ON v.id=o.vendor_id
                  LEFT JOIN order_items oi ON oi.order_id=o.id
                  WHERE o.tp_number=? GROUP BY o.id ORDER BY o.id DESC""", (tp,), fetch=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def student_history(student):
    st.header("🧾 Order history")
    df = load_student_history(student["tp_number"])
    if df.empty:
        st.info("No orders yet.")
        return
    show = df.copy()
    show["created_at"] = show["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    show["total"] = show["total"].map(money)
    st.dataframe(show.rename(columns={"order_id": "Order #", "created_at": "Date", "stall": "Stall",
                                      "status": "Status", "total": "Total", "items": "Items"}),
                 hide_index=True, use_container_width=True)


def student_spending(student):
    st.header("💰 Spending tracker")
    df = load_student_history(student["tp_number"])
    df = df[df["status"] != "Cancelled"] if not df.empty else df
    if df.empty:
        st.info("No spending to show yet. Place an order first!")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        start, end = date_range_picker("Date range", "sp_dates")
    with c2:
        stalls = st.multiselect("Stalls", sorted(df["stall"].unique()))
    with c3:
        budget = st.number_input(f"Budget for this period ({CURRENCY}, 0 = none)", 0.0, step=10.0)

    mask = (df["created_at"].dt.date >= start) & (df["created_at"].dt.date <= end)
    if stalls:
        mask &= df["stall"].isin(stalls)
    f = df[mask]
    if f.empty:
        st.warning("No orders match these filters.")
        return

    total = f["total"].sum()
    top = f.groupby("stall")["total"].sum().idxmax()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total spent", money(total))
    m2.metric("Orders", len(f))
    m3.metric("Average per order", money(total / len(f)))
    m4.metric("Most spent at", top)
    if budget > 0:
        st.progress(min(total / budget, 1.0),
                    text=f"{money(total)} of {money(budget)} budget ({total / budget:.0%})")
        if total > budget:
            st.error(f"Over budget by {money(total - budget)}")

    left, right = st.columns(2)
    with left:
        st.subheader("Spending per day")
        st.bar_chart(f.groupby(f["created_at"].dt.date)["total"].sum())
    with right:
        st.subheader("Spending per stall")
        st.bar_chart(f.groupby("stall")["total"].sum())

    st.subheader("Orders in this view")
    show = f.copy()
    show["created_at"] = show["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    show["total"] = show["total"].map(money)
    st.dataframe(show[["order_id", "created_at", "stall", "items", "total"]],
                 hide_index=True, use_container_width=True)


def student_app():
    student = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"### 🎓 {student['name']}")
        st.caption(student["tp_number"])
        page = st.radio("Menu", ["Browse stalls", "My orders", "Order history", "Spending tracker"])
        if st.button("Log out"):
            logout()
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    {"Browse stalls": student_browse, "My orders": student_orders,
     "Order history": student_history, "Spending tracker": student_spending}[page](student)


# ================================================================== VENDOR
def vendor_orders(vendor):
    st.header("📥 Incoming orders")
    if st.button("🔄 Refresh"):
        st.rerun()
    orders = run("""SELECT o.*, s.name AS student_name FROM orders o
                    JOIN students s ON s.tp_number=o.tp_number
                    WHERE o.vendor_id=? AND o.status IN ('Pending','Preparing','Ready')
                    ORDER BY o.id""", (vendor["id"],), fetch=True)
    if not orders:
        st.info("No active orders right now.")
        return
    for o in orders:
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"**Order #{o['id']}** · {o['student_name']} ({o['tp_number']}) · {o['created_at']}")
            c1.write(order_items_text(o["id"]))
            c1.write(f"Total: **{money(o['total'])}**")
            c2.markdown(f"**Status:** {STATUS_ICON[o['status']]} {o['status']}")
            b1, b2 = c2.columns(2)
            nxt = {"Pending": ("Start preparing", "Preparing"),
                   "Preparing": ("Mark ready", "Ready"),
                   "Ready": ("Mark collected", "Completed")}[o["status"]]
            if b1.button(nxt[0], key=f"adv_{o['id']}", type="primary"):
                run("UPDATE orders SET status=? WHERE id=?", (nxt[1], o["id"]))
                st.rerun()
            if o["status"] in ("Pending", "Preparing"):
                if b2.button("Cancel", key=f"vc_{o['id']}"):
                    run("UPDATE orders SET status='Cancelled' WHERE id=?", (o["id"],))
                    st.rerun()


def vendor_menu(vendor):
    st.header("🍽️ Manage menu")
    with st.expander("➕ Add a new item", expanded=True):
        with st.form("add_item", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Item name").strip()
            price = c2.number_input(f"Price ({CURRENCY})", 0.0, step=0.5, format="%.2f")
            if st.form_submit_button("Add item", type="primary"):
                if not name or price <= 0:
                    st.error("Enter a name and a price above 0.")
                else:
                    run("INSERT INTO menu_items(vendor_id, name, price) VALUES (?,?,?)",
                        (vendor["id"], name, price))
                    st.success(f"Added {name}.")
                    st.rerun()

    st.subheader("Current menu")
    items = run("SELECT * FROM menu_items WHERE vendor_id=? AND deleted=0 ORDER BY name",
                (vendor["id"],), fetch=True)
    if not items:
        st.info("Your menu is empty. Add your first item above.")
    for it in items:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.2, 1, 1])
            name = c1.text_input("Name", it["name"], key=f"n_{it['id']}")
            price = c2.number_input("Price", 0.0, value=float(it["price"]), step=0.5,
                                    format="%.2f", key=f"p_{it['id']}")
            avail = c3.checkbox("Available", bool(it["available"]), key=f"a_{it['id']}")
            if c4.button("Save", key=f"s_{it['id']}"):
                if name.strip() and price > 0:
                    run("UPDATE menu_items SET name=?, price=?, available=? WHERE id=?",
                        (name.strip(), price, int(avail), it["id"]))
                    st.toast("Saved ✔")
                    st.rerun()
                else:
                    st.error("Invalid name or price.")
            if c5.button("Delete", key=f"d_{it['id']}"):
                # soft delete so past orders/reports stay intact
                run("UPDATE menu_items SET deleted=1 WHERE id=?", (it["id"],))
                st.rerun()


def load_vendor_orders(vendor_id):
    rows = run("""SELECT o.id AS order_id, o.created_at, o.tp_number, o.status, o.total
                  FROM orders o WHERE o.vendor_id=? ORDER BY o.id DESC""", (vendor_id,), fetch=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["items"] = df["order_id"].map(order_items_text)
    return df


def vendor_report(vendor):
    st.header("📊 Order history & sales report")
    df = load_vendor_orders(vendor["id"])
    if df.empty:
        st.info("No orders yet.")
        return
    c1, c2 = st.columns(2)
    with c1:
        start, end = date_range_picker("Date range", "vr_dates")
    with c2:
        statuses = st.multiselect("Status", ["Pending", "Preparing", "Ready", "Completed", "Cancelled"],
                                  default=["Pending", "Preparing", "Ready", "Completed", "Cancelled"])
    mask = (df["created_at"].dt.date >= start) & (df["created_at"].dt.date <= end) & df["status"].isin(statuses)
    f = df[mask]
    if f.empty:
        st.warning("No orders match these filters.")
        return

    valid = f[f["status"] != "Cancelled"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Revenue (excl. cancelled)", money(valid["total"].sum()))
    m2.metric("Valid orders", len(valid))
    m3.metric("Cancelled", int((f["status"] == "Cancelled").sum()))
    m4.metric("Avg order value", money(valid["total"].mean()) if len(valid) else money(0))

    ids = tuple(valid["order_id"].tolist())
    if ids:
        ph = ",".join("?" * len(ids))
        pop = pd.DataFrame(run(f"""SELECT item_name AS item, SUM(qty) AS sold,
                                   SUM(qty*unit_price) AS revenue FROM order_items
                                   WHERE order_id IN ({ph}) GROUP BY item_name
                                   ORDER BY sold DESC""", ids, fetch=True))
        left, right = st.columns(2)
        with left:
            st.subheader("🔥 Most popular items")
            st.bar_chart(pop.set_index("item")["sold"])
            top = pop.iloc[0]
            st.caption(f"Best seller: **{top['item']}** ({int(top['sold'])} sold)")
        with right:
            st.subheader("Revenue per day")
            st.bar_chart(valid.groupby(valid["created_at"].dt.date)["total"].sum())
        st.subheader("Item breakdown")
        pop["revenue"] = pop["revenue"].map(money)
        st.dataframe(pop.rename(columns={"item": "Item", "sold": "Units sold", "revenue": "Revenue"}),
                     hide_index=True, use_container_width=True)

    st.subheader("All orders")
    show = f.copy()
    show["created_at"] = show["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    show["total"] = show["total"].map(money)
    st.dataframe(show.rename(columns={"order_id": "Order #", "created_at": "Date", "tp_number": "Student",
                                      "status": "Status", "total": "Total", "items": "Items"}),
                 hide_index=True, use_container_width=True)
    st.download_button("⬇️ Download CSV", f.to_csv(index=False).encode(),
                       "sales_report.csv", "text/csv")


def vendor_app():
    vendor = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"### 🏪 {vendor['shop_name']}")
        st.caption(f"@{vendor['username']}")
        page = st.radio("Menu", ["Incoming orders", "Manage menu", "History & reports"])
        if st.button("Log out"):
            logout()
    {"Incoming orders": vendor_orders, "Manage menu": vendor_menu,
     "History & reports": vendor_report}[page](vendor)


# ------------------------------------------------------------------ main
def main():
    init_db()
    role = st.session_state.get("role")
    if role == "student":
        student_app()
    elif role == "vendor":
        vendor_app()
    else:
        auth_page()


main()
