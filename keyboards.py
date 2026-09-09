from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import pricing

def main_menu_kb():
    """Asosiy menyu tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Telegram Stars", callback_data="cat_stars", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text="Telegram Premium", callback_data="cat_premium", icon_custom_emoji_id="5274026806477857971")
        ],
        [
            InlineKeyboardButton(text="Telegram Gift", callback_data="cat_gift", icon_custom_emoji_id="5224628072619216265")
        ],
        [
            InlineKeyboardButton(text="Statistika", callback_data="bot_stats", icon_custom_emoji_id="5364265190353286344"),
            InlineKeyboardButton(text="TOP Reyting", callback_data="top_rating", icon_custom_emoji_id="5415655814079723871")
        ],
        [
            InlineKeyboardButton(text="Profil", callback_data="user_profile", icon_custom_emoji_id="5256143829672672750"),
            InlineKeyboardButton(text="Qo'llab-quvvatlash", callback_data="support", icon_custom_emoji_id="5307746710682869587")
        ]
    ])
    
def sub_check_kb(channel_ids):
    """Barcha kanallarga obuna bo'lish va tekshirish tugmalari."""
    if isinstance(channel_ids, str):
        channel_ids = [channel_ids]
    rows = []
    for index, channel_id in enumerate(channel_ids, 1):
        channel_name = str(channel_id).replace('@', '')
        rows.append([
            InlineKeyboardButton(
                text="📢 Obuna bo'ling",
                url=f"https://t.me/{channel_name}"
            )
        ])
    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def cancel_kb():
    """Bekor qilish / Orqaga tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")]
    ])

def payment_back_kb():
    """To'lov ekranida orqaga tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")]
    ])

def stars_menu_kb():
    """Telegram Stars tariflari (narxlar prices.json dan olinadi)."""
    prices = pricing.load_prices()["stars"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"50 - {pricing.format_price(prices['50'])} so'm", callback_data=f"buy_stars_50_{prices['50']}", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text=f"75 - {pricing.format_price(prices['75'])} so'm", callback_data=f"buy_stars_75_{prices['75']}", icon_custom_emoji_id="5346309121794659890")
        ],
        [
            InlineKeyboardButton(text=f"100 - {pricing.format_price(prices['100'])} so'm", callback_data=f"buy_stars_100_{prices['100']}", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text=f"150 - {pricing.format_price(prices['150'])} so'm", callback_data=f"buy_stars_150_{prices['150']}", icon_custom_emoji_id="5346309121794659890")
        ],
        [
            InlineKeyboardButton(text=f"250 - {pricing.format_price(prices['250'])} so'm", callback_data=f"buy_stars_250_{prices['250']}", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text=f"300 - {pricing.format_price(prices['300'])} so'm", callback_data=f"buy_stars_300_{prices['300']}", icon_custom_emoji_id="5346309121794659890")
        ],
        [
            InlineKeyboardButton(text=f"500 - {pricing.format_price(prices['500'])} so'm", callback_data=f"buy_stars_500_{prices['500']}", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text=f"750 - {pricing.format_price(prices['750'])} so'm", callback_data=f"buy_stars_750_{prices['750']}", icon_custom_emoji_id="5346309121794659890")
        ],
        [
            InlineKeyboardButton(text=f"1000 - {pricing.format_price(prices['1000'])} so'm", callback_data=f"buy_stars_1000_{prices['1000']}", icon_custom_emoji_id="5346309121794659890"),
            InlineKeyboardButton(text=f"1500 - {pricing.format_price(prices['1500'])} so'm", callback_data=f"buy_stars_1500_{prices['1500']}", icon_custom_emoji_id="5346309121794659890")
        ],
        [
            InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")
        ]
    ])


def premium_options_kb():
    """Premium tanlash: akkauntga kirib yoki kirmasdan"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Akkauntga kirib", callback_data="premium_with_account", icon_custom_emoji_id="5345905193005371012")],
        [InlineKeyboardButton(text="Akkauntga kirmasdan", callback_data="premium_without_account", icon_custom_emoji_id="5350619413533958825")],
        [InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")]
    ])

def premium_menu_with_account_kb():
    prices = pricing.load_prices()["premium_with"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1 Oylik Premium — {pricing.format_price(prices['1'])} so'm", callback_data=f"buy_premium_with_account_1_{prices['1']}", icon_custom_emoji_id="5274026806477857971")],
        [InlineKeyboardButton(text=f"12 Oylik Premium — {pricing.format_price(prices['12'])} so'm", callback_data=f"buy_premium_with_account_12_{prices['12']}", icon_custom_emoji_id="5274026806477857971")],
        [InlineKeyboardButton(text="Orqaga", callback_data="back_premium_options", icon_custom_emoji_id="5350576283472373136")]
    ])

def premium_menu_without_account_kb():
    prices = pricing.load_prices()["premium_without"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"3 Oylik Premium — {pricing.format_price(prices['3'])} so'm", callback_data=f"buy_premium_without_account_3_{prices['3']}", icon_custom_emoji_id="5274026806477857971")],
        [InlineKeyboardButton(text=f"6 Oylik Premium — {pricing.format_price(prices['6'])} so'm", callback_data=f"buy_premium_without_account_6_{prices['6']}", icon_custom_emoji_id="5274026806477857971")],
        [InlineKeyboardButton(text=f"12 Oylik Premium — {pricing.format_price(prices['12'])} so'm", callback_data=f"buy_premium_without_account_12_{prices['12']}", icon_custom_emoji_id="5274026806477857971")],
        [InlineKeyboardButton(text="Orqaga", callback_data="back_premium_options", icon_custom_emoji_id="5350576283472373136")]
    ])


def gift_method_kb():
    """Gift yuborish usulini tanlash menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="@visasum", callback_data="gift_method_visasum", icon_custom_emoji_id="5258011929993026890")],
        [InlineKeyboardButton(text="Anonim ", callback_data="gift_method_anonim", icon_custom_emoji_id="5258093637450866522")],
        [InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")]
    ])

def gift_button(label: str, gift_name: str, method_label: str, price_group: str, emoji_id: str):
    price = pricing.get_price("gifts", price_group)
    return InlineKeyboardButton(
        text=f"{label} {pricing.format_price(price)} so'm",
        callback_data=f"buy_gift_{gift_name} ({method_label})_{price}",
        icon_custom_emoji_id=emoji_id
    )

def gift_menu_kb(method: str = "visasum"):
    """Rasmdagidek giftlar ro'yxati (2 talik ustun va tugmalar)"""
    method_label = "@visasum" if method == "visasum" else "Anonim"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        # 1-qator
        [
            gift_button("Yurak", "Yurak", method_label, "2985", "5283228279988309088"),
            gift_button("Ayiqcha", "Ayiqcha", method_label, "2985", "5280598054901145762")
        ],
        # 2-qator
        [
            gift_button("Sovg'a", "Sovg'a", method_label, "4975", "5280615440928758599"),
            gift_button("Atirgul", "Atirgul", method_label, "4975", "5280947338821524402")
        ],
        # 3-qator
        [
            gift_button("Kort", "Kort", method_label, "9950", "5280659198055575507"),
            gift_button("Raketa", "Raketa", method_label, "9950", "5280774333243873175")
        ],
        # 4-qator
        [
            gift_button("Guldasta", "Guldasta", method_label, "9950", "5283080528818360566"),
            gift_button("Shampan", "Shampan", method_label, "9950", "5451905784734574339")
        ],
        # 5-qator (3 talik)
        [
            gift_button("Brilliant", "Brilliant", method_label, "19900", "5280769763398671636"),
            gift_button("Uzuk", "Uzuk", method_label, "19900", "5280922999241859582"),
            gift_button("Kubok", "Kubok", method_label, "19900", "5280651583078556009")
        ],
        # 6-qator (Katta tugma)
        [
            gift_button("Yangi gift", "Yangi Gift", method_label, "9950", "5470129614439362117")
        ],
        # 7-qator
        [
            gift_button("Pushti yurak", "PushtiYurak", method_label, "9950", "5224628072619216265"),
            gift_button("Pushti ayiq", "PushtiAyiq", method_label, "9950", "5289761157173775507")
        ],
        # 8-qator
        [
            gift_button("Oq ayiq", "Oqayiq", method_label, "9950", "5226661632259691727"),
            gift_button("Quyon", "Quyon", method_label, "9950", "5393309541620291208")
        ],
        # 9-qator
        [
            gift_button("Elf", "Elf", method_label, "9950", "5317000922096769303"),
            gift_button("Qorbobo", "Qorbobo", method_label, "9950", "5379850840691476775")
        ],
        # 10-qator
        [
            gift_button("Masqaraboz", "masqaraboz", method_label, "9950", "5359735030143196497"),
            gift_button("Usta", "usta", method_label, "9950", "5447213743417105726")
        ],
        # 11-qator
        [
            gift_button("Archa", "Archa", method_label, "9950", "5345935030143196497"),
            gift_button("Koptokli ayiq", "Koptokli Ayiq", method_label, "9950", "5397971251878732060")
        ],
        # Qaytish (Orqaga) tugmasi
        [
            InlineKeyboardButton(text=" Orqaga", callback_data="cat_gift", icon_custom_emoji_id="5350576283472373136")
        ]
    ])

def admin_user_choice_kb():
    """Admin uchun /start da tanlov menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🧑‍💼 Admin panel"),
                KeyboardButton(text="👤 Foydalanuvchi menyusi")
            ]
        ],
        resize_keyboard=True
    )


def admin_main_kb():
    """Admin paneli uchun menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Kengaytirilgan statistika"),
                KeyboardButton(text="📢 Barchaga xabar yuborish")
            ],
            [
                KeyboardButton(text="📅 Oylik statistika"),
                KeyboardButton(text="💰 Tariflarni tahrirlash")
            ],
            [
                KeyboardButton(text="🧹 Statistikani 0 qilish"),
                KeyboardButton(text="📢 Kanal qo'shish"),
                KeyboardButton(text="🗑 Kanalni o'chirish")
            ],
            [
                KeyboardButton(text="⬅️ Orqaga", icon_custom_emoji_id="5350576283472373136")
            ]
        ],
        resize_keyboard=True
    )


def reset_stats_confirm_kb():
    """Statistikani reset qilishni tasdiqlash tugmalari."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, 0 qilinsin", callback_data="reset_stats_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reset_stats_cancel")
        ]
    ])


def admin_prices_kb():
    """Admin uchun tarif tanlash menyusi."""
    rows = []
    for category, key, label, value in pricing.all_price_items():
        rows.append([
            InlineKeyboardButton(
                text=f"{label}: {pricing.format_price(value)} so'm",
                callback_data=f"price_edit:{category}:{key}"
            )
        ])
    rows.append([InlineKeyboardButton(text="Orqaga", callback_data="price_edit_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_channel_remove_kb(channel_ids):
    """Admin uchun o'chiriladigan kanallar ro'yxati."""
    rows = []
    for channel_id in channel_ids:
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 {channel_id} ni o'chirish",
                callback_data=f"remove_channel:{channel_id}"
            )
        ])
    rows.append([InlineKeyboardButton(text="Orqaga", callback_data="remove_channel_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def cancel_broadcast_kb():
    """Admin xabar yuborishni bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

def admin_order_kb(order_id: int):
    """Admin buyurtmani tasdiqlash/rad etish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{order_id}")
        ]
    ])