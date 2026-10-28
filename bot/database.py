import os
import sqlite3
import time

os.makedirs("/root/sheikh/data", exist_ok=True)


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init()

    def _init(self):
        c = self.cur
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            points INTEGER DEFAULT 0,
            premium INTEGER DEFAULT 0,
            premium_until INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            phone TEXT,
            phone_verified INTEGER DEFAULT 0,
            registered_at INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT DEFAULT 'open',
            created_at INTEGER,
            updated_at INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS ticket_msgs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            sender TEXT,
            text TEXT,
            created_at INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            kind TEXT,
            amount INTEGER,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            created_at INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            result TEXT,
            cost INTEGER,
            created_at INTEGER
        )""")
        self.conn.commit()

    def get_user(self, uid):
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        r = self.cur.fetchone()
        if not r:
            self.cur.execute(
                "INSERT INTO users(user_id, registered_at) VALUES(?,?)",
                (uid, int(time.time())),
            )
            self.conn.commit()
            self.cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            r = self.cur.fetchone()
        return dict(r)

    def add_points(self, uid, n):
        self.cur.execute("UPDATE users SET points=points+? WHERE user_id=?", (n, uid))
        self.conn.commit()

    def take_points(self, uid, n):
        u = self.get_user(uid)
        if u["points"] < n:
            return False
        self.cur.execute("UPDATE users SET points=points-? WHERE user_id=?", (n, uid))
        self.conn.commit()
        return True

    def set_premium(self, uid, days=30):
        self.cur.execute(
            "UPDATE users SET premium=1, premium_until=? WHERE user_id=?",
            (int(time.time()) + days * 86400, uid),
        )
        self.conn.commit()

    def is_premium(self, uid):
        u = self.get_user(uid)
        return u["premium"] == 1 and u["premium_until"] > time.time()

    def set_phone(self, uid, phone, verified=True):
        self.cur.execute(
            "UPDATE users SET phone=?, phone_verified=? WHERE user_id=?",
            (phone, 1 if verified else 0, uid),
        )
        self.conn.commit()

    def set_daily(self, uid, ts):
        self.cur.execute("UPDATE users SET last_daily=? WHERE user_id=?", (ts, uid))
        self.conn.commit()

    def new_payment(self, uid, kind, amount):
        self.cur.execute(
            "INSERT INTO payments(user_id, kind, amount, created_at) VALUES(?,?,?,?)",
            (uid, kind, amount, int(time.time())),
        )
        self.conn.commit()
        return self.cur.lastrowid

    def set_payment_hash(self, pid, tx):
        self.cur.execute("UPDATE payments SET tx_hash=? WHERE id=?", (tx, pid))
        self.conn.commit()

    def mark_payment_paid(self, pid):
        self.cur.execute("UPDATE payments SET status='paid' WHERE id=?", (pid,))
        self.conn.commit()

    def log_search(self, uid, q, res, cost):
        self.cur.execute(
            "INSERT INTO searches(user_id, query, result, cost, created_at) VALUES(?,?,?,?,?)",
            (uid, q, res, cost, int(time.time())),
        )
        self.conn.commit()


db = DB("/root/sheikh/data/sheikh.db")
