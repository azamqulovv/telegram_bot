import csv
import os
import re
from datetime import datetime

import aiosqlite

DB_NAME = "bot_database.db"
LOG_FILE_NAME = "admin_orders_log.csv"

async def init_db():
    """Baza jadvallarini yaratish va yangilash (Migration)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                price TEXT,
                target_username TEXT,
                photo_id TEXT,
                file_type TEXT DEFAULT 'photo',
                approved_num INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monthly_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT UNIQUE,
                total_users INTEGER DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                total_stars INTEGER DEFAULT 0,
                total_stars_revenue INTEGER DEFAULT 0,
                total_premium INTEGER DEFAULT 0,
                prem_1m INTEGER DEFAULT 0,
                prem_3m INTEGER DEFAULT 0,
                prem_6m INTEGER DEFAULT 0,
                prem_12m INTEGER DEFAULT 0,
                with_1m INTEGER DEFAULT 0,
                with_12m INTEGER DEFAULT 0,
                without_3m INTEGER DEFAULT 0,
                without_6m INTEGER DEFAULT 0,
                without_12m INTEGER DEFAULT 0,
                total_gifts INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats_control (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")

        # Eski jadvalga yangi ustunlarni xavfsiz qo'shish
        for column_def in [
            "photo_id TEXT",
            "approved_num INTEGER",
            "file_type TEXT DEFAULT 'photo'"
        ]:
            try:
                await db.execute(f"ALTER TABLE orders ADD COLUMN {column_def}")
            except Exception:
                pass

        for column_def in [
            "prem_1m INTEGER DEFAULT 0",
            "prem_3m INTEGER DEFAULT 0",
            "prem_6m INTEGER DEFAULT 0",
            "prem_12m INTEGER DEFAULT 0",
            "with_1m INTEGER DEFAULT 0",
            "with_12m INTEGER DEFAULT 0",
            "without_3m INTEGER DEFAULT 0",
            "without_6m INTEGER DEFAULT 0",
            "without_12m INTEGER DEFAULT 0"
        ]:
            try:
                await db.execute(f"ALTER TABLE monthly_stats ADD COLUMN {column_def}")
            except Exception:
                pass

        await db.commit()

async def add_user(user_id: int, username: str, full_name: str):
    """Yangi foydalanuvchini saqlash yoki ma'lumotlarini yangilash"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))
        await db.commit()

async def export_orders_to_csv():
    """Barcha buyurtmalarni admin uchun CSV fayliga yozib boradi."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, LOG_FILE_NAME)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT id, user_id, product_name, price, target_username, photo_id, file_type, approved_num, status, created_at
            FROM orders
            ORDER BY id ASC
        """) as cursor:
            rows = await cursor.fetchall()

    with open(log_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "id",
            "user_id",
            "product_name",
            "price",
            "target_username",
            "photo_id",
            "file_type",
            "approved_num",
            "status",
            "created_at",
        ])
        for row in rows:
            writer.writerow(row)

    return log_path


async def reset_all_activity():
    """Bot faoliyatini tozalab, buyurtma va chek raqamlarini qayta boshlaydi."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM orders")
        await db.execute("DELETE FROM users")
        await db.execute("DELETE FROM monthly_stats")
        await db.execute("DELETE FROM stats_control")
        await db.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders', 'monthly_stats')")
        await db.commit()

    await export_orders_to_csv()


async def create_order(user_id: int, product_name: str, price: str, target_username: str, photo_id: str, file_type: str = "photo") -> int:
    """Yangi buyurtma yaratish va fayl turini saqlash"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, product_name, price, target_username, photo_id, file_type) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, product_name, price, target_username, photo_id, file_type)
        )
        await db.commit()
        order_id = cursor.lastrowid

    await export_orders_to_csv()
    return order_id

async def approve_and_number_order(order_id: int):
    """Buyurtmani tasdiqlash va tartib raqam berish"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT MAX(approved_num) FROM orders WHERE status = 'approved'") as cursor:
            res = await cursor.fetchone()
            next_num = (res[0] if res[0] is not None else -1) + 1

        await db.execute(
            "UPDATE orders SET status = 'approved', approved_num = ? WHERE id = ?",
            (next_num, order_id)
        )
        await db.commit()

        async with db.execute(
            "SELECT user_id, product_name, price, target_username, photo_id, file_type, approved_num FROM orders WHERE id = ?",
            (order_id,)
        ) as cursor:
            result = await cursor.fetchone()

    await export_orders_to_csv()
    return result

async def update_order_status(order_id: int, status: str):
    """Buyurtma holatini yangilash (approved/rejected)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        await db.commit()

    await export_orders_to_csv()

async def get_order(order_id: int):
    """Buyurtma haqida ma'lumot olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, product_name, price, target_username, status FROM orders WHERE id = ?",
            (order_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_user_order_history(user_id: int, limit: int = 5):
    """Foydalanuvchining oxirgi buyurtmalari va statuslarini qaytaradi."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT id, product_name, price, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ) as cursor:
            return await cursor.fetchall()

async def get_stats():
    """Oddiy statistika"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            total_orders = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'approved'") as cursor:
            approved_orders = (await cursor.fetchone())[0]

        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "approved_orders": approved_orders
        }

def _extract_stars_quantity(product_name: str | None) -> int:
    """Mahsulot nomidan stars miqdorini ajratib oladi."""
    if not product_name:
        return 0

    text = product_name.upper()
    match = re.search(r"(\d+(?:\s*\d+)*)\s*(?:TA|TAS|STAR|STARS)?", text)
    if not match:
        return 0

    number_text = match.group(1).replace(" ", "")
    try:
        return int(number_text)
    except ValueError:
        return 0


def _premium_access_type(product_name: str | None) -> str:
    """Premium buyurtmangiz usulini aniqlaydi: 'with' yoki 'without'."""
    if not product_name:
        return "unknown"
    text = product_name.upper()
    if "KIRMASDAN" in text or "WITHOUT" in text:
        return "without"
    if "KIRIB" in text or "WITH" in text:
        return "with"
    return "unknown"


def _premium_month_value(product_name: str | None) -> int | None:
    """Premium buyurtma muddati (1, 3, 6, 12) ni qaytaradi."""
    if not product_name:
        return None
    text = product_name.upper()
    for value in [12, 6, 3, 1]:
        if re.search(rf"(?:^|[-\s]){value}(?:\s*(?:OY|OYLIK|M))?(?:$|\s)", text) or (value == 12 and "1 YIL" in text):
            return value
    return None


def _count_premium_breakdown(rows):
    """Premium buyurtmalarni o'qish usuli bo'yicha ajratib beradi."""
    stats = {
        "with_1m": 0,
        "with_12m": 0,
        "without_3m": 0,
        "without_6m": 0,
        "without_12m": 0,
    }

    for row in rows:
        product_name = row[0] if isinstance(row, tuple) else row
        access_type = _premium_access_type(product_name)
        month = _premium_month_value(product_name)
        if month is None:
            continue

        if access_type == "unknown":
            access_type = "with" if month == 1 else "without"

        if access_type == "with":
            if month == 1:
                stats["with_1m"] += 1
            elif month == 12:
                stats["with_12m"] += 1
        elif access_type == "without":
            if month == 3:
                stats["without_3m"] += 1
            elif month == 6:
                stats["without_6m"] += 1
            elif month == 12:
                stats["without_12m"] += 1

    return stats


async def refresh_monthly_stats(month: str | None = None):
    """Joriy oy bo'yicha statistika hisobotini yangilash."""
    month = month or datetime.now().strftime("%Y-%m")

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM stats_control WHERE key = 'reset_at'") as cursor:
            reset_row = await cursor.fetchone()
        reset_at = reset_row[0] if reset_row else "1970-01-01 00:00:00"

        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (reset_at,)) as cursor:
            total_users = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'approved' AND created_at >= ?", (reset_at,)) as cursor:
            total_orders = (await cursor.fetchone())[0]

        order_scope = "status = 'approved' AND created_at >= ?"
        async with db.execute(f"SELECT product_name FROM orders WHERE UPPER(product_name) LIKE '%STARS%' AND {order_scope}", (reset_at,)) as cursor:
            star_rows = await cursor.fetchall()
        total_stars = sum(_extract_stars_quantity(name[0]) for name in star_rows)

        async with db.execute(f"SELECT COALESCE(SUM(CAST(price AS INTEGER)), 0) FROM orders WHERE UPPER(product_name) LIKE '%STARS%' AND {order_scope}", (reset_at,)) as cursor:
            total_stars_revenue = (await cursor.fetchone())[0] or 0

        async with db.execute(f"SELECT product_name FROM orders WHERE UPPER(product_name) LIKE '%PREMIUM%' AND {order_scope}", (reset_at,)) as cursor:
            premium_rows = await cursor.fetchall()
        premium_breakdown = _count_premium_breakdown(premium_rows)
        total_premium = len(premium_rows)
        prem_1m = premium_breakdown["with_1m"]
        prem_3m = premium_breakdown["without_3m"]
        prem_6m = premium_breakdown["without_6m"]
        prem_12m = premium_breakdown["with_12m"] + premium_breakdown["without_12m"]
        with_1m = premium_breakdown["with_1m"]
        with_12m = premium_breakdown["with_12m"]
        without_3m = premium_breakdown["without_3m"]
        without_6m = premium_breakdown["without_6m"]
        without_12m = premium_breakdown["without_12m"]

        async with db.execute(f"SELECT COUNT(*) FROM orders WHERE UPPER(product_name) LIKE '%GIFT%' AND {order_scope}", (reset_at,)) as cursor:
            total_gifts = (await cursor.fetchone())[0]

        async with db.execute(f"SELECT COALESCE(SUM(CAST(price AS INTEGER)), 0) FROM orders WHERE {order_scope}", (reset_at,)) as cursor:
            total_revenue = (await cursor.fetchone())[0] or 0

        await db.execute("""
            INSERT INTO monthly_stats (
                month, total_users, total_orders, total_stars,
                total_stars_revenue, total_premium, prem_1m, prem_3m, prem_6m, prem_12m, total_gifts, total_revenue
                , with_1m, with_12m, without_3m, without_6m, without_12m
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
                total_users = excluded.total_users,
                total_orders = excluded.total_orders,
                total_stars = excluded.total_stars,
                total_stars_revenue = excluded.total_stars_revenue,
                total_premium = excluded.total_premium,
                prem_1m = excluded.prem_1m,
                prem_3m = excluded.prem_3m,
                prem_6m = excluded.prem_6m,
                prem_12m = excluded.prem_12m,
                with_1m = excluded.with_1m,
                with_12m = excluded.with_12m,
                without_3m = excluded.without_3m,
                without_6m = excluded.without_6m,
                without_12m = excluded.without_12m,
                total_gifts = excluded.total_gifts,
                total_revenue = excluded.total_revenue
        """, (
            month,
            total_users,
            total_orders,
            total_stars,
            total_stars_revenue,
            total_premium,
            prem_1m,
            prem_3m,
            prem_6m,
            prem_12m,
            total_gifts,
            total_revenue,
            with_1m,
            with_12m,
            without_3m,
            without_6m,
            without_12m,
        ))
        await db.commit()


async def reset_monthly_stats():
    """Joriy statistika uchun yangi hisoblash nuqtasini o'rnatadi."""
    reset_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO stats_control (key, value) VALUES ('reset_at', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (reset_at,)
        )
        await db.execute("DELETE FROM monthly_stats")
        await db.commit()


async def get_monthly_stats(month: str | None = None):
    """Oylik statistika ma'lumotlarini olish."""
    month = month or datetime.now().strftime("%Y-%m")

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT month, total_users, total_orders, total_stars,
                   total_stars_revenue, total_premium, prem_1m, prem_3m, prem_6m, prem_12m, total_gifts, total_revenue
                   , with_1m, with_12m, without_3m, without_6m, without_12m
            FROM monthly_stats
            WHERE month = ?
        """, (month,)) as cursor:
            row = await cursor.fetchone()

    if not row:
        return {
            "month": month,
            "total_users": 0,
            "total_orders": 0,
            "total_stars": 0,
            "total_stars_revenue": 0,
            "total_premium": 0,
            "prem_1m": 0,
            "prem_3m": 0,
            "prem_6m": 0,
            "prem_12m": 0,
            "with_1m": 0,
            "with_12m": 0,
            "without_3m": 0,
            "without_6m": 0,
            "without_12m": 0,
            "total_gifts": 0,
            "total_revenue": 0,
        }

    return {
        "month": row[0],
        "total_users": row[1],
        "total_orders": row[2],
        "total_stars": row[3],
        "total_stars_revenue": row[4],
        "total_premium": row[5],
        "prem_1m": row[6],
        "prem_3m": row[7],
        "prem_6m": row[8],
        "prem_12m": row[9],
        "total_gifts": row[10],
        "total_revenue": row[11],
        "with_1m": row[12],
        "with_12m": row[13],
        "without_3m": row[14],
        "without_6m": row[15],
        "without_12m": row[16],
    }


async def get_all_user_ids():
    """Barcha foydalanuvchilar ID larini olish (Xabar yuborish uchun)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_advanced_stats():
    """Kengaytirilgan statistika (Premium va Stars tafsilotlari bilan)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]

        async with db.execute("SELECT product_name FROM orders WHERE UPPER(product_name) LIKE '%STARS%' AND status = 'approved'") as cursor:
            star_rows = await cursor.fetchall()
        total_stars_orders = sum(_extract_stars_quantity(name[0]) for name in star_rows)

        async with db.execute("SELECT COALESCE(SUM(CAST(price AS INTEGER)), 0) FROM orders WHERE UPPER(product_name) LIKE '%STARS%' AND status = 'approved'") as cursor:
            total_stars_revenue = (await cursor.fetchone())[0] or 0

        async with db.execute("SELECT COUNT(*) FROM orders WHERE UPPER(product_name) LIKE '%GIFT%' AND status = 'approved'") as cursor:
            total_gifts = (await cursor.fetchone())[0]

        async with db.execute("SELECT product_name FROM orders WHERE UPPER(product_name) LIKE '%PREMIUM%' AND status = 'approved'") as cursor:
            premium_rows = await cursor.fetchall()
        premium_breakdown = _count_premium_breakdown(premium_rows)
        total_premium = len(premium_rows)
        prem_1m = premium_breakdown["with_1m"]
        prem_3m = premium_breakdown["without_3m"]
        prem_6m = premium_breakdown["without_6m"]
        prem_12m = premium_breakdown["with_12m"] + premium_breakdown["without_12m"]

        async with db.execute("SELECT COALESCE(SUM(CAST(price AS INTEGER)), 0) FROM orders WHERE status = 'approved'") as cursor:
            res = await cursor.fetchone()
            total_revenue = res[0] if res[0] else 0

        async with db.execute("""
            SELECT u.full_name, o.user_id, SUM(CAST(o.price AS INTEGER)) as total_spent, COUNT(o.id) as order_count
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'approved'
            GROUP BY o.user_id
            ORDER BY total_spent DESC
            LIMIT 5
        """) as cursor:
            top_users = await cursor.fetchall()

        return {
            "total_users": total_users,
            "total_stars_orders": total_stars_orders,
            "total_stars_revenue": total_stars_revenue,
            "total_gifts": total_gifts,
            "total_premium": total_premium,
            "prem_1m": prem_1m,
            "prem_3m": prem_3m,
            "prem_6m": prem_6m,
            "prem_12m": prem_12m,
            "total_revenue": total_revenue,
            "top_users": top_users
        }


async def get_top_buyers(limit: int = 5):
    """TOP xaridorlar"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT u.full_name, u.user_id, SUM(CAST(o.price AS INTEGER)) as total_spent
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'approved'
            GROUP BY o.user_id
            ORDER BY total_spent DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()


async def get_user_order_stats(user_id: int):
    """Foydalanuvchining barcha buyurtmalari bo'yicha status statistikasi."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(status = 'approved'), 0),
                COALESCE(SUM(status = 'rejected'), 0),
                COALESCE(SUM(status = 'pending'), 0)
            FROM orders
            WHERE user_id = ?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return {
        "total": row[0],
        "approved": row[1],
        "rejected": row[2],
        "pending": row[3],
    }