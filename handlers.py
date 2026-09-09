import asyncio

from aiogram import Router, F, Bot, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db
import keyboards as kb
import pricing
import channels
from states import BuyProduct

# Premium Custom Emoji ID
GIFT_PREMIUM_EMOJI_ID = "5368324170671202286"


# Barcha mahsulotlar uchun yagona Custom Emoji ID lug'ati
ALL_EMOJI_IDS = {
    # Stars va Premium
    "STARS": "5346309121794659890",
    "PREMIUM": "5274026806477857971",
    
    # Giftlar
    "YURAK": "5283228279988309088",
    "AYIQCHA": "5280598054901145762",
    "SOVG'A": "5280615440928758599",
    "ATIRGUL": "5280947338821524402",
    "KORT": "5280659198055572187",
    "RAKETA": "5280774333243873175",
    "GULDASTA": "5283080528818360566",
    "SHAMPAN": "5451905784734574339",
    "BRILLIANT": "5280769763398671636",
    "UZUK": "5280922999241859582",
    "KUBOK": "5280651583078556009",
    "YANGI GIFT": "5470129614439362117",
    "PUSHTI YURAK": "5224628072619216265",
    "PUSHTI AYIQ": "5289761157173775507",
    "OQAYIQ": "5226661632259691727",
    "QUYON": "5393309541620291208",
    "ELF": "5317000922096769303",
    "QORBOBO": "5379850840691476775",
    "MASQARABOZ": "5359736160224586485",
    "USTA": "5447213743417105726",
    "ARCHA": "5345935030143196497",
    "KOPTOKLI AYIQ": "5397971251878732060"
}

router = Router()
sub_cache = {}
payment_timer_tasks = {}



def get_custom_emoji_tag(product_name: str) -> str:
    if not product_name:
        return ""
    p_upper = product_name.upper()
    
    if "STAR" in p_upper:
        emoji_id = ALL_EMOJI_IDS["STARS"]
        fallback = "⭐️"
    elif "PREMIUM" in p_upper:
        emoji_id = ALL_EMOJI_IDS["PREMIUM"]
        fallback = "💎"
    else:
        # Gift nomidan kalit so'zni topish
        emoji_id = "5280615440928758599" # Standart gift
        fallback = "🎁"
        for key, eid in ALL_EMOJI_IDS.items():
            if key in p_upper:
                emoji_id = eid
                break
                
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# Admin uchun xabar yuborish (Rassylka) holati
class AdminBroadcast(StatesGroup):
    waiting_for_message = State()


class AdminPriceEdit(StatesGroup):
    waiting_for_price = State()


class AdminChannelAdd(StatesGroup):
    waiting_for_channel = State()


# Sonlarni joy tashlab ajratish (masalan: 7519151 -> 7 519 151)
def fmt(num: int) -> str:
    if num is None:
        return "0"
    return f"{num:,}".replace(",", " ")


async def safe_edit_message(message, *, text: str | None = None, caption: str | None = None, reply_markup=None, parse_mode=None):
    current_text = getattr(message, "text", None)
    current_caption = getattr(message, "caption", None)
    current_markup = getattr(message, "reply_markup", None)

    if text is not None and current_text == text and current_markup == reply_markup:
        return
    if caption is not None and current_caption == caption and current_markup == reply_markup:
        return

    try:
        if caption is not None:
            await message.edit_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        raise


def payment_text(data: dict, seconds_left: int) -> str:
    minutes, seconds = divmod(max(seconds_left, 0), 60)
    return (
        f"💳 <b>To'lov ma'lumotlari:</b>\n\n"
        f"Karta raqami: <code>{config.CARD_NUMBER}</code>\n"
        f"Egalari: <b>{config.CARD_HOLDER}</b>\n"
        f"To'lov summasi: <b>{data['price']} so'm</b>\n\n"
        f"⏳ Chek yuborish uchun qolgan vaqt: <b>{minutes:02d}:{seconds:02d}</b>\n\n"
        f"To'lovni amalga oshirgach, <b>to'lov chekini rasm (PNG/JPG) yoki fayl ko'rinishida</b> yuboring:"
    )


def cancel_payment_timer(user_id: int):
    task = payment_timer_tasks.pop(user_id, None)
    if task and not task.done():
        task.cancel()


async def payment_countdown(message: types.Message, state: FSMContext, user_id: int, timer_token: str):
    try:
        for seconds_left in range(300, -1, -1):
            data = await state.get_data()
            if data.get("payment_timer_token") != timer_token:
                return
            await safe_edit_message(
                message,
                text=payment_text(data, seconds_left),
                reply_markup=kb.payment_back_kb(),
                parse_mode="HTML"
            )
            if seconds_left:
                await asyncio.sleep(1)

        data = await state.get_data()
        if data.get("payment_timer_token") == timer_token:
            await state.clear()
            await safe_edit_message(
                message,
                text="⌛ <b>To'lov vaqti tugadi.</b>\n\nBuyurtmani qaytadan boshlashingiz mumkin.",
                reply_markup=kb.cancel_kb(),
                parse_mode="HTML"
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        return
    finally:
        if payment_timer_tasks.get(user_id) is asyncio.current_task():
            payment_timer_tasks.pop(user_id, None)

# Kanallarga obunani tekshirish (keshli)
async def check_subscription(bot: Bot, user_id: int) -> bool:
    if user_id in sub_cache:
        return sub_cache[user_id]
    try:
        is_sub = True
        for channel_id in channels.get_channels():
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            channel_subscribed = member.status in ['creator', 'administrator', 'member'] or (
                member.status == 'restricted' and getattr(member, 'is_member', False)
            )
            if not channel_subscribed:
                is_sub = False
                break
        if is_sub:
            sub_cache[user_id] = True
        return is_sub
    except Exception:
        return False


async def get_unsubscribed_channels(bot: Bot, user_id: int) -> list[str]:
    """Foydalanuvchi obuna bo'lmagan kanallarni qaytaradi."""
    missing = []
    for channel_id in channels.get_channels():
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            subscribed = member.status in ['creator', 'administrator', 'member'] or (
                member.status == 'restricted' and getattr(member, 'is_member', False)
            )
        except Exception:
            subscribed = False
        if not subscribed:
            missing.append(channel_id)
    return missing

# ==================== /START VA OBUNA ====================

@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot, state: FSMContext, command: CommandObject | None = None):
    await state.clear()
    await db.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)

    args = (command.args if command and command.args else "").strip().lower()

    if args == "stars":
        await message.answer("⭐️ <b>Telegram Stars</b> tarifini tanlang:", reply_markup=kb.stars_menu_kb(), parse_mode="HTML")
        return
    if args == "premium":
        await message.answer("💎 <b>Telegram Premium</b> muddatini tanlang:", reply_markup=kb.premium_options_kb(), parse_mode="HTML")
        return
    if args == "gift":
        caption = (
            f"<blockquote>🎁 <b>Telegram Gift yuborish</b></blockquote>\n\n"
            f"Iltimos, gift yuborish usulini tanlang:\n\n"
            f"1️⃣ <b>@visasum</b> — Profildan to'g'ridan-to'g'ri yuboriladi.\n"
            f"2️⃣ <b>Anonim</b> — anonim holatda yuboriladi."
        )
        await message.answer(caption, reply_markup=kb.gift_method_kb(), parse_mode="HTML")
        return

    is_admin = message.from_user.id in [config.ADMIN_ID, config.ADMIN_ID_2]

    if await check_subscription(bot, message.from_user.id):
        if is_admin:
            await message.answer(
                "👨‍💻 <b>Admin uchun tanlov</b>\n\nKerakli oynani tanlang:",
                reply_markup=kb.admin_user_choice_kb(),
                parse_mode="HTML"
            )
        else:
            await message.answer("👋 Xush kelibsiz! Asosiy menyudan kerakli bo'limni tanlang:", reply_markup=kb.main_menu_kb())
    else:
        missing_channels = await get_unsubscribed_channels(bot, message.from_user.id)
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "📢 <b>Kanallarimizga obuna bo'ling</b>\n"
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=kb.sub_check_kb(missing_channels)
        )

@router.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if user_id in sub_cache:
        del sub_cache[user_id]
        
    is_admin = user_id in [config.ADMIN_ID, config.ADMIN_ID_2]

    if await check_subscription(bot, user_id):
        if is_admin:
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
            await callback.message.answer(
                "👨‍💻 <b>Admin uchun tanlov</b>\n\nKerakli oynani tanlang:",
                reply_markup=kb.admin_user_choice_kb(),
                parse_mode="HTML"
            )
        else:
            await safe_edit_message(
                callback.message,
                text="✅ Obuna tasdiqlandi!\n\nAsosiy menyu:",
                reply_markup=kb.main_menu_kb()
            )
        await callback.answer("✅ Obuna tasdiqlandi!")
    else:
        missing_channels = await get_unsubscribed_channels(bot, user_id)
        await callback.message.edit_reply_markup(reply_markup=kb.sub_check_kb(missing_channels))
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    cancel_payment_timer(callback.from_user.id)
    await state.clear()
    if callback.from_user.id in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.message.delete()
        await callback.message.answer(
            "👨‍💻 <b>Admin uchun tanlov</b>\n\nKerakli oynani tanlang:",
            reply_markup=kb.admin_user_choice_kb(),
            parse_mode="HTML"
        )
    else:
        await safe_edit_message(callback.message, text="Asosiy menyu:", reply_markup=kb.main_menu_kb())


@router.message(F.text == "🧑‍💼 Admin panel")
async def open_admin_panel_from_choice(message: types.Message):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    await message.answer(
        "👨‍💻 <b>Admin paneliga xush kelibsiz!</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )


@router.message(F.text == "👤 Foydalanuvchi menyusi")
async def open_user_menu_from_choice(message: types.Message):
    if message.from_user.id in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await message.answer("👋 Xush kelibsiz! Asosiy menyudan kerakli bo'limni tanlang:", reply_markup=kb.main_menu_kb())


@router.message(F.text.in_({"⬅️ Orqaga", "◀️ Orqaga", "Orqaga"}))
async def back_from_any_menu(message: types.Message):
    if message.from_user.id in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await message.answer(
            "👨‍💻 <b>Admin uchun tanlov</b>\n\nKerakli oynani tanlang:",
            reply_markup=kb.admin_user_choice_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer("👋 Xush kelibsiz! Asosiy menyudan kerakli bo'limni tanlang:", reply_markup=kb.main_menu_kb())

# ==================== KATALOGLAR ====================

@router.callback_query(F.data == "cat_stars")
async def cat_stars(callback: types.CallbackQuery):
    await safe_edit_message(callback.message, text="⭐️ <b>Telegram Stars</b> tarifini tanlang:", reply_markup=kb.stars_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "cat_premium")
async def cat_premium(callback: types.CallbackQuery):
    text = (
        "💎 "
        "<b>Telegram Premium</b> akkauntga kirish usulini tanlang:"
    )
    await safe_edit_message(
        callback.message,
        text=text,
        reply_markup=kb.premium_options_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "premium_with_account")
async def premium_with_account(callback: types.CallbackQuery):
    text = (
        "💎 "
        "<b>Telegram Premium</b> muddatini tanlang:"
    )
    await safe_edit_message(
        callback.message,
        text=text,
        reply_markup=kb.premium_menu_with_account_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "premium_without_account")
async def premium_without_account(callback: types.CallbackQuery):
    await safe_edit_message(
        callback.message,
        text="💎 <b>Telegram Premium</b> (Akkauntga kirmasdan) muddatini tanlang:",
        reply_markup=kb.premium_menu_without_account_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_premium_options")
async def back_premium_options(callback: types.CallbackQuery):
    text = (
        "💎 <b>Telegram Premium</b> akkauntga kirish usulini tanlang:"
    )
    await safe_edit_message(
        callback.message,
        text=text,
        reply_markup=kb.premium_options_kb(),
        parse_mode="HTML"
    )

# 1-QADAM: Usul tanlashni so'rash
@router.callback_query(F.data == "cat_gift")
async def cat_gift(callback: types.CallbackQuery):
    caption = (
        f"<blockquote>🎁 <b>Telegram Gift yuborish</b></blockquote>\n\n"
        f"Iltimos, gift yuborish usulini tanlang:\n\n"
        f"1️⃣ <b>@visasum</b> — Profildan to'g'ridan-to'g'ri yuboriladi.\n"
        f"2️⃣ <b>Anonim</b> — anonim holatda yuboriladi."
    )
    await safe_edit_message(callback.message, text=caption, reply_markup=kb.gift_method_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("gift_method_"))
async def process_gift_method(callback: types.CallbackQuery):
    method = callback.data.split("_")[2] # 'visasum' yoki 'anonim'
    sender_info = "@visasum" if method == "visasum" else "anonim "

    caption = (
        f"<blockquote>🎁 Giftlarni starsga almashtirish mumkin bo'ladi va {sender_info} jonatiladi</blockquote>\n"
        f"<blockquote>Qanday gift olmoqchisiz tanlang 👉</blockquote>"
    )

    await safe_edit_message(callback.message, text=caption, reply_markup=kb.gift_menu_kb(method), parse_mode="HTML")

# ==================== STATISTIKA VA REYTING ====================

@router.callback_query(F.data == "bot_stats")
async def show_stats(callback: types.CallbackQuery):
    stats = await db.get_advanced_stats()
    
    top_text = ""
    if stats["top_users"]:
        for idx, row in enumerate(stats["top_users"], 1):
            # row can be (name, user_id, total_spent) or (name, user_id, total_spent, order_count)
            name = row[0] if len(row) > 0 else None
            u_id = row[1] if len(row) > 1 else None
            spent = row[2] if len(row) > 2 else 0
            user_name = name if name else "Foydalanuvchi"
            sep = "\n──────────────\n" if idx > 1 else ""
            top_text += f"{sep}<b>{idx}.</b> {user_name} <b>{fmt(spent)} so'm</b>\n<i>ID: {u_id}</i>"
    else:
        top_text = "<i>Hozircha xaridorlar yo'q</i>"

    stars_count = stats.get('total_stars_orders') or stats.get('total_stars') or 0
    stars_revenue = stats.get('total_stars_revenue') or 0
    caption = (
        f"<blockquote>🏆 <b>Botning umumiy statistikasi</b>\n"
        f"──────────────\n"
        f"🕵️ Jami foydalanuvchilar: <b>{fmt(stats['total_users'])} ta</b>\n"
        f"⭐ Olingan umumiy miqdor: <b>{fmt(stars_count)} ta</b>\n"
        f"💰 Stars daromadi: <b>{fmt(stars_revenue)} so'm</b>\n"
        f"🎁 Sotilgan giftlar: <b>{fmt(stats['total_gifts'])} ta</b>\n"
        f"💳 Jami tushgan mablag': <b>{fmt(stats['total_revenue'])} so'm</b></blockquote>\n\n"

        f"<blockquote>💎 <b>Premium muddatlar bo'yicha</b>\n"
        f"──────────────\n"
        f"• 1 oy: <b>{fmt(stats.get('prem_1m') or 0)} ta</b>\n"
        f"• 3 oy: <b>{fmt(stats.get('prem_3m') or 0)} ta</b>\n"
        f"• 6 oy: <b>{fmt(stats.get('prem_6m') or 0)} ta</b>\n"
        f"• 12 oy: <b>{fmt(stats.get('prem_12m') or 0)} ta</b></blockquote>\n\n"

        f"<blockquote>💳 <b>Savdolar bo'yicha TOP Reyting</b>\n"
        f"──────────────\n"
        f"{top_text}</blockquote>"
    )
    
    kb_stats = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Yangilash", callback_data="bot_stats", icon_custom_emoji_id="5370715282044100355"),
            InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="530576283472373136")
        ],
        [
            InlineKeyboardButton(text="📅 Oylik statistika", callback_data="monthly_stats")
        ]
    ])

    await safe_edit_message(callback.message, text=caption, reply_markup=kb_stats, parse_mode="HTML")


@router.callback_query(F.data == "monthly_stats")
async def show_monthly_stats(callback: types.CallbackQuery):
    await db.refresh_monthly_stats()
    stats = await db.get_monthly_stats()

    text = (
        f"📅 <b>Oylik statistika</b>\n\n"
        f"📆 Oy: <b>{stats['month']}</b>\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🧾 Jami buyurtmalar: <b>{stats['total_orders']}</b>\n"
        f"⭐ Stars: <b>{stats['total_stars']} ta</b>\n"
        f"💰 Stars summasi: <b>{fmt(stats['total_stars_revenue'])} so'm</b>\n"
        f"💎 Premium (jami): <b>{stats['total_premium']} ta</b>\n"
        f"  ├ Akkauntga kirib: <b>{stats.get('with_1m', 0) + stats.get('with_12m', 0)} ta</b>\n"
        f"  │   ├ 1 oy: <b>{stats.get('with_1m', 0)} ta</b>\n"
        f"  │   └ 12 oy: <b>{stats.get('with_12m', 0)} ta</b>\n"
        f"  └ Akkauntga kirmasdan: <b>{stats.get('without_3m', 0) + stats.get('without_6m', 0) + stats.get('without_12m', 0)} ta</b>\n"
        f"      ├ 3 oy: <b>{stats.get('without_3m', 0)} ta</b>\n"
        f"      ├ 6 oy: <b>{stats.get('without_6m', 0)} ta</b>\n"
        f"      └ 12 oy: <b>{stats.get('without_12m', 0)} ta</b>\n"
        f"🎁 Giftlar: <b>{stats['total_gifts']}</b>\n"
        f"💳 Umumiy tushum: <b>{fmt(stats['total_revenue'])} so'm</b>"
    )

    kb_monthly = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="monthly_stats"),
            InlineKeyboardButton(text="Orqaga", callback_data="bot_stats", icon_custom_emoji_id="530576283472373136")
        ]
    ])

    await safe_edit_message(callback.message, text=text, reply_markup=kb_monthly, parse_mode="HTML")
    await callback.answer()


@router.message(F.text == "📅 Oylik statistika")
async def show_monthly_stats_from_reply(message: types.Message):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return

    await db.refresh_monthly_stats()
    stats = await db.get_monthly_stats()
    await message.answer(
        f"📅 <b>Oylik statistika</b>\n\n"
        f"📆 Oy: <b>{stats['month']}</b>\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🧾 Jami buyurtmalar: <b>{stats['total_orders']}</b>\n"
        f"⭐ Stars: <b>{stats['total_stars']} ta</b>\n"
        f"💰 Stars summasi: <b>{fmt(stats['total_stars_revenue'])} so'm</b>\n"
        f"💎 Premium (jami): <b>{stats['total_premium']} ta</b>\n"
        f"  ├ Akkauntga kirib: <b>{stats.get('with_1m', 0) + stats.get('with_12m', 0)} ta</b>\n"
        f"  │   ├ 1 oy: <b>{stats.get('with_1m', 0)} ta</b>\n"
        f"  │   └ 12 oy: <b>{stats.get('with_12m', 0)} ta</b>\n"
        f"  └ Akkauntga kirmasdan: <b>{stats.get('without_3m', 0) + stats.get('without_6m', 0) + stats.get('without_12m', 0)} ta</b>\n"
        f"      ├ 3 oy: <b>{stats.get('without_3m', 0)} ta</b>\n"
        f"      ├ 6 oy: <b>{stats.get('without_6m', 0)} ta</b>\n"
        f"      └ 12 oy: <b>{stats.get('without_12m', 0)} ta</b>\n"
        f"🎁 Giftlar: <b>{stats['total_gifts']}</b>\n"
        f"💳 Umumiy tushum: <b>{fmt(stats['total_revenue'])} so'm</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_main_kb()
    )

@router.callback_query(F.data == "top_rating")
async def show_top_rating(callback: types.CallbackQuery):
    top_buyers = await db.get_top_buyers(limit=5)
    
    top_text = ""
    if top_buyers:
        for idx, (name, u_id, spent) in enumerate(top_buyers, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            icon = medals.get(idx, f"<b>{idx}.</b>")
            user_name = name if name else "Foydalanuvchi"
            sep = "\n──────────────\n" if idx > 1 else ""
            top_text += f"{sep}{icon} {user_name} — <b>{fmt(spent)} so'm</b>\n<i>ID: {u_id}</i>"
    else:
        top_text = "<i>Hozircha tasdiqlangan xaridorlar yo'q</i>"

    caption = (
        f"🏆 <b>Eng ko'p xarid qilgan TOP xaridorlar</b>\n\n"
        f"<blockquote>{top_text}</blockquote>\n"
        f"<i>Reyting faqat admin tasdiqlagan to'lovlar bo'yicha hisoblanadi.</i>"
    )
    
    kb_top = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Yangilash", callback_data="top_rating", icon_custom_emoji_id="5370715282044100355"),
            InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="530576283472373136")
        ]
    ])
    await safe_edit_message(callback.message, text=caption, reply_markup=kb_top, parse_mode="HTML")

# ==================== PROFIL VA ALOQA ====================

@router.callback_query(F.data == "user_profile")
async def user_profile(callback: types.CallbackQuery):
    user = callback.from_user
    username_str = f"@{user.username}" if user.username else "Mavjud emas"
    order_history = await db.get_user_order_history(user.id, limit=5)
    order_stats = await db.get_user_order_stats(user.id)

    if order_history:
        order_lines = []
        for order_id, product_name, price, status, created_at in order_history:
            status_labels = {
                "approved": "🟢 Tasdiqlangan",
                "rejected": "🔴 Bekor qilingan",
                "pending": "🟡 Kutilmoqda",
            }
            status_label = status_labels.get(status, f"⚪ {status}")
            public_id = max(order_id - 1, 0)
            order_lines.append(
                f"#{public_id} | <b>{product_name}</b> | {fmt(int(price or 0))} so'm\n"
                f"   {status_label}"
            )
        orders_text = "\n".join(order_lines)
    else:
        orders_text = "<i>Hozircha buyurtmalar mavjud emas</i>"
    
    caption = (
        f"👤 <b>Sizning profilingiz:</b>\n\n"
        f"<blockquote>"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Ism: <b>{user.full_name}</b>\n"
        f"🔗 Username: <b>{username_str}</b>"
        f"</blockquote>\n\n"
        f"📦 <b>Buyurtmalar statistikasi</b>\n"
        f"Jami buyurtmalar: <b>{order_stats['total']}</b> ta\n"
        f"🟢 Tasdiqlangan: <b>{order_stats['approved']}</b>\n"
        f"🔴 Bekor qilingan: <b>{order_stats['rejected']}</b>\n"
        f"🟡 Kutilmoqda: <b>{order_stats['pending']}</b>\n\n"
        f"🧾 <b>Oxirgi 5 ta buyurtma:</b>\n{orders_text}"
    )
    await safe_edit_message(callback.message, text=caption, reply_markup=kb.cancel_kb(), parse_mode="HTML")

@router.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    support_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Admin bilan bog'lanish", url=f"https://t.me/{config.ADMIN_USERNAME}", icon_custom_emoji_id="5443038326535759644")],
        [InlineKeyboardButton(text="Orqaga", callback_data="back_to_main", icon_custom_emoji_id="5350576283472373136")]
    ])
    caption = (
        f"👨‍💻 <b>Qo'llab-quvvatlash xizmati</b>\n\n"
        f"Savollar yoki to'lov bo'yicha murojaat uchun admin bilan bog'laning."
    )
    await safe_edit_message(callback.message, text=caption, reply_markup=support_kb, parse_mode="HTML")

# ==================== XARID QILISH JARAYONI ====================

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    raw = callback.data
    if raw.startswith("buy_"):
        payload = raw[4:]
        if "_" not in payload:
            await callback.answer("❌ Buyurtma ma'lumotlari noto‘g‘ri.", show_alert=True)
            return

        product_part, price = payload.rsplit("_", 1)
        product_parts = product_part.split("_")

        if len(product_parts) < 2:
            await callback.answer("❌ Buyurtma ma'lumotlari noto‘g‘ri.", show_alert=True)
            return

        p_type = product_parts[0]
        access_method = ""
        if p_type.upper() == "PREMIUM" and len(product_parts) >= 4 and product_parts[1] in {"with", "without"}:
            access_method = "with" if product_parts[1] == "with" else "without"
            p_name = product_parts[-1]
        else:
            p_name = "_".join(product_parts[1:])
    else:
        p_type = ""
        p_name = ""
        price = "0"
        access_method = ""

    p_type_upper = p_type.upper()
    if p_type_upper == "PREMIUM":
        price_category = "premium_with" if access_method == "with" else "premium_without"
        current_price = pricing.get_price(price_category, p_name)
        if current_price:
            price = str(current_price)
        if access_method == "without":
            display_name = f"{p_name} oy"
            full_product_name = f"{p_type_upper} - AKKAUNTGA KIRMASDAN - {display_name}"
        elif access_method == "with":
            display_name = f"{p_name} oy"
            full_product_name = f"{p_type_upper} - AKKAUNTGA KIRIB - {display_name}"
        else:
            display_name = f"{p_name} oy"
            full_product_name = f"{p_type_upper} - {display_name}"
    elif p_type_upper == "STARS":
        current_price = pricing.get_price("stars", p_name)
        if current_price:
            price = str(current_price)
        display_name = f"{p_name} ta"
        full_product_name = f"{p_type_upper} - {display_name}"
    else:
        if p_type_upper == "GIFT":
            gift_name = p_name.split(" (")[0].strip()
            current_price = pricing.get_price("gifts", pricing.gift_group(gift_name))
            if current_price:
                price = str(current_price)
        display_name = p_name
        full_product_name = f"{p_type_upper} - {display_name}"

    await state.update_data(product_name=full_product_name, price=price)

    await state.set_state(BuyProduct.enter_target_username)
    await safe_edit_message(
        callback.message,
        text=(
            f"🛒 Tanlandi: <b>{full_product_name}</b>\n"
            f"💵 Narxi: <b>{price} so'm</b>\n\n"
            f"Ushbu xarid qaysi Telegram profilga yuborilishi kerak?\n"
            f"Iltimos, username'ni kiriting (masalan: <code>@username</code>):"
        ),
        reply_markup=kb.payment_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BuyProduct.enter_target_username)
async def process_target_username(message: types.Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"):
        target = "@" + target
        
    await state.update_data(target_username=target)
    data = await state.get_data()
    
    await state.set_state(BuyProduct.upload_receipt)
    cancel_payment_timer(message.from_user.id)
    timer_token = str(id(data))
    await state.update_data(payment_timer_token=timer_token)
    payment_message = await message.answer(
        payment_text(data, 300),
        reply_markup=kb.payment_back_kb(),
        parse_mode="HTML"
    )
    payment_timer_tasks[message.from_user.id] = asyncio.create_task(
        payment_countdown(payment_message, state, message.from_user.id, timer_token)
    )

@router.message(BuyProduct.upload_receipt, F.photo | F.document)
async def process_receipt(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cancel_payment_timer(message.from_user.id)
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        file_id = message.document.file_id
        file_type = "document"
    
    order_id = await db.create_order(
        user_id=message.from_user.id,
        product_name=data['product_name'],
        price=data['price'],
        target_username=data['target_username'],
        photo_id=file_id,
        file_type=file_type
    )
    display_order_id = max(order_id - 1, 0)
    
    await state.clear()
    await message.answer("✅ Buyurtmangiz qabul qilindi! Admin tekshiruvidan so'ng sizga xabar beriladi.", reply_markup=kb.main_menu_kb())
    
    # Yagona custom emoji tegi orqali mahsulotni chiqarish
    product_display = f"{get_custom_emoji_tag(data['product_name'])} <b>{data['product_name']}</b>"

    admin_text = (
        f"📥 <b>YANGI BUYURTMA #{display_order_id}</b>\n\n"
        f"� Buyurtma raqami: <b>#{order_id}</b>\n"
        f"�👤 Xaridor: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
        f"📦 Mahsulot: {product_display}\n"
        f"💵 Summa: <b>{data['price']} so'm</b>\n"
        f"🎯 Qabul qiluvchi: <b>{data['target_username']}</b>"
    )
    admin_text = admin_text.replace(f"#{order_id}", f"#{display_order_id}")
    
    if file_type == "photo":
        await bot.send_photo(chat_id=config.ADMIN_ID, photo=file_id, caption=admin_text, reply_markup=kb.admin_order_kb(order_id), parse_mode="HTML")
    else:
        await bot.send_document(chat_id=config.ADMIN_ID, document=file_id, caption=admin_text, reply_markup=kb.admin_order_kb(order_id), parse_mode="HTML")

@router.message(BuyProduct.upload_receipt)
async def invalid_receipt(message: types.Message):
    await message.answer("⚠️ Iltimos, to'lov chekini rasm yoki fayl (PNG/PDF) ko'rinishida yuboring!")


def get_product_cta(product_name: str):
    """Mahsulot turiga qarab buyurtma tugmasini qaytaradi."""
    name = (product_name or "").upper()
    if "STARS" in name:
        return "⭐ Stars olish", "stars"
    if "PREMIUM" in name:
        return "💎 Premium olish", "premium"
    if "GIFT" in name:
        return "🎁 Gift olish", "gift"
    return "🤖 Botga o'tish", "main"

# ==================== ADMIN TASDIQLASH / RAD ETISH ====================

@router.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)
    
    if order:
        user_id, product_name, price, target_username, status = order
        await db.update_order_status(order_id, "rejected")
        
        await safe_edit_message(
            callback.message,
            caption=(callback.message.caption or "") + "\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML"
        )
        await bot.send_message(
            chat_id=user_id,
            text=f"❌ <b>Buyurtmangiz #{max(order_id - 1, 0)} rad etildi.</b>\n\nTo'lovda xatolik bo'lishi mumkin. Ma'lumot uchun adminga murojaat qiling.",
            parse_mode="HTML"
        )
    await callback.answer("Buyurtma rad etildi!")

# ==================== ADMIN PANEL (FAQAT 2 TA TUGMA) ====================

@router.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order_data = await db.approve_and_number_order(order_id)
    
    if order_data:
        user_id, product_name, price, target_username, file_id, file_type, approved_num = order_data
        formatted_num = str(approved_num)
        product_action, start_target = get_product_cta(product_name)
        
        await safe_edit_message(
            callback.message,
            caption=(callback.message.caption or "") + f"\n\n✅ <b>TASDIQLANDI</b>\n📌 Buyurtma raqami: <b>#{max(order_id - 1, 0)}</b>\n📄 Chek №{formatted_num}",
            parse_mode="HTML"
        )
        
        # Foydalanuvchiga bildirishnoma
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Buyurtmangiz muvaffaqiyatli bajarildi!</b>\n\n"
                f"🧾 Chek raqami: <b>№{formatted_num}</b>\n"
                f"📦 Mahsulot: {get_custom_emoji_tag(product_name)} <b>{product_name}</b>\n"
                f"🎯 Qabul qiluvchi: <b>{target_username}</b>\n\n"
                f"Xaridingiz uchun rahmat!"
            ),
            parse_mode="HTML"
        )
        
        # Gift nomini tozalash
        clean_gift_name = product_name
        if "GIFT -" in product_name.upper():
            clean_gift_name = product_name.split("GIFT -")[-1].strip()
        elif "GIFT" in product_name.upper():
            clean_gift_name = product_name.replace("GIFT", "").strip(" -")

        p_upper = product_name.upper()
        
        if "STAR" in p_upper:
            stars_count = product_name.replace("Stars", "").replace("STAR", "").strip()
            header_title = f"{get_custom_emoji_tag(product_name)} Profilga botdan stars olindi"
            details_block = (
                f"👤 Xaridor: <b>{target_username}</b>\n"
                f"{get_custom_emoji_tag(product_name)} Miqdor: <b>{stars_count} ta</b>\n"
                f"💳 Narxi: <b>{fmt(int(price))} so'm</b>"
            )
            
        elif "PREMIUM" in p_upper:
            if "KIRMASDAN" in p_upper or "WITHOUT" in p_upper:
                access_method = "Akkauntga kirmasdan"
            else:
                access_method = "Akkauntga kirib"

            tariff_name = product_name
            tariff_parts = product_name.split(" - ")
            if len(tariff_parts) >= 3:
                tariff_name = f"{tariff_parts[0]} - {tariff_parts[-1]}"

            header_title = f"{get_custom_emoji_tag(product_name)} Telegram Premium olindi"
            details_block = (
                f"👤 Xaridor: <b>{target_username}</b>\n"
                f"{get_custom_emoji_tag(product_name)} Tarif: <b>{tariff_name}</b>\n"
                f"🔑 Usuli: <b>{access_method}</b>\n"
                f"💳 Narxi: <b>{fmt(int(price))} so'm</b>"
            )
            
        else:
            # Gift uchun qaysi usul tanlangan bo'lsa, faqat o'shani chiqarish
            if "ANONIM" in p_upper:
                gift_method = "Anonim"
            else:
                gift_method = "@visasum dan"
                
            header_title = f"{get_custom_emoji_tag(product_name)} Gift sotib olindi"
            details_block = (
                f"👤 Xaridor: <b>{target_username}</b>\n"
                f"🎁 Gift: {get_custom_emoji_tag(product_name)}\n"
                f"📦 Yuborilish: <b>{gift_method}</b>\n"
                f"💳 Narxi: <b>{fmt(int(price))} so'm</b>"
            )

        channel_text = (
            f"<b>{header_title}</b>\n\n"
            f"📌 <b>Chek №{formatted_num}</b>\n\n"
            f"<blockquote>"
            f"{details_block}"
            f"</blockquote>"
        )

        bot_info = await bot.get_me()
        bot_username = getattr(bot_info, "username", None)
        channel_kb = None
        
        if bot_username:
            channel_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=product_action,
                    url=f"https://t.me/{bot_username}?start={start_target}"
                )
            ]])

        try:
            await bot.send_message(
                chat_id=config.CHECKS_CHANNEL_ID,
                text=channel_text,
                parse_mode="HTML",
                reply_markup=channel_kb
            )
        except Exception as e:
            print(f"Kanalga post qilishda xatolik: {e}")

    await callback.answer(f"Buyurtma №{approved_num} sifatida tasdiqlandi!")

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await message.answer(
            "👨‍💻 <b>Admin paneliga xush kelibsiz!</b>\n\nKerakli bo'limni tanlang:",
            reply_markup=kb.admin_main_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Siz admin emassiz!")

@router.message(F.text == "📊 Kengaytirilgan statistika")
async def show_adv_stats(message: types.Message):
    if int(message.from_user.id) not in [int(config.ADMIN_ID), int(config.ADMIN_ID_2)]:
        return
        
    stats = await db.get_advanced_stats()
    
    top_str = ""
    if stats["top_users"]:
        for idx, item in enumerate(stats["top_users"], 1):
            name, u_id, spent, order_count = item[0], item[1], item[2], item[3]
            user_name = name if name else "Noma'lum"
            top_str += f"\n  {idx}. {user_name} (ID: <code>{u_id}</code>) — <b>{fmt(spent)} so'm</b> ({order_count} ta xarid)"
    else:
        top_str = "\n  <i>Hozircha xaridorlar yo'q</i>"

    text = (
        f"📊 <b>ADMIN STATISTIKASI</b>\n\n"
        f"👥 Barcha foydalanuvchilar: <b>{stats['total_users']} ta</b>\n\n"
        f"🛒 <b>Sotuvlar ko'rsatkichlari:</b>\n"
        f"⭐ Olingan umumiy stars miqdori: <b>{stats['total_stars_orders']} ta</b>\n"
        f"💰 Stars daromadi: <b>{fmt(stats.get('total_stars_revenue') or 0)} so'm</b>\n"
        f"🎁 Sotilgan Giftlar: <b>{stats['total_gifts']} ta</b>\n"
        f"💎 Sotilgan Premium (Jami): <b>{stats['total_premium']} ta</b>\n"
        f"  ├ Akkauntga kirib: <b>{stats.get('prem_1m', 0) + stats.get('prem_12m', 0)} ta</b>\n"
        f"  │   ├ 1 oylik: <b>{stats['prem_1m']} ta</b>\n"
        f"  │   └ 12 oylik: <b>{stats['prem_12m']} ta</b>\n"
        f"  └ Akkauntga kirmasdan: <b>{stats.get('prem_3m', 0) + stats.get('prem_6m', 0)} ta</b>\n"
        f"      ├ 3 oylik: <b>{stats['prem_3m']} ta</b>\n"
        f"      ├ 6 oylik: <b>{stats['prem_6m']} ta</b>\n"
        f"      └ 12 oylik: <b>{stats['prem_12m']} ta</b>\n\n"
        f"💰 Umumiy tushum: <b>{fmt(stats['total_revenue'])} so'm</b>\n\n"
        f"🏆 <b>TOP Xaridorlar:</b>{top_str}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🧹 Statistikani 0 qilish")
async def request_stats_reset(message: types.Message):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    await message.answer(
        "⚠️ <b>Statistikani 0 qilishni tasdiqlaysizmi?</b>\n\n"
        "Barcha foydalanuvchilar, buyurtmalar, umumiy statistika va cheklar tarixi o'chiriladi.\n"
        "Keyingi buyurtma #0, keyingi chek №0 dan boshlanadi.",
        reply_markup=kb.reset_stats_confirm_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "reset_stats_cancel")
async def cancel_stats_reset(callback: types.CallbackQuery):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await callback.message.edit_text("❌ Statistikani 0 qilish bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "reset_stats_confirm")
async def confirm_stats_reset(callback: types.CallbackQuery):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await db.reset_all_activity()
    await callback.message.edit_text(
        "✅ <b>Bot faoliyati tozalandi.</b>\n\n"
        "Barcha buyurtmalar, foydalanuvchilar va statistika o'chirildi.\n"
        "Keyingi buyurtma #0, keyingi chek №0 dan boshlanadi.",
        parse_mode="HTML"
    )
    await callback.answer("Statistika 0 qilindi")


@router.message(F.text == "💰 Tariflarni tahrirlash")
async def show_price_editor(message: types.Message):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    await message.answer(
        "💰 <b>Tarif narxini tanlang:</b>",
        reply_markup=kb.admin_prices_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "price_edit_back")
async def price_editor_back(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await safe_edit_message(
        callback.message,
        text="💰 <b>Tarif narxini tanlang:</b>",
        reply_markup=kb.admin_prices_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("price_edit:"))
async def select_price_to_edit(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    _, category, key = callback.data.split(":")
    current_price = pricing.get_price(category, key)
    await state.update_data(price_category=category, price_key=key)
    await state.set_state(AdminPriceEdit.waiting_for_price)
    await safe_edit_message(
        callback.message,
        text=(
            f"💰 <b>{category} / {key}</b>\n"
            f"Hozirgi narx: <b>{pricing.format_price(current_price)} so'm</b>\n\n"
            "Yangi narxni faqat raqam ko'rinishida yuboring:"
        ),
        reply_markup=kb.cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminPriceEdit.waiting_for_price)
async def save_edited_price(message: types.Message, state: FSMContext):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return

    if not message.text or message.text.strip().lower() in {"orqaga", "⬅️ orqaga", "◀️ orqaga"}:
        await state.clear()
        await message.answer("💰 <b>Tariflar menyusi:</b>", reply_markup=kb.admin_prices_kb(), parse_mode="HTML")
        return

    raw_price = message.text.replace(" ", "").replace("'", "").strip()
    if not raw_price.isdigit() or int(raw_price) <= 0:
        await message.answer("⚠️ Narx faqat musbat raqam bo'lishi kerak. Masalan: 35000")
        return

    data = await state.get_data()
    pricing.update_price(data["price_category"], data["price_key"], int(raw_price))
    await state.clear()
    await message.answer(
        f"✅ Narx yangilandi: <b>{pricing.format_price(int(raw_price))} so'm</b>",
        reply_markup=kb.admin_prices_kb(),
        parse_mode="HTML"
    )

@router.message(F.text == "📢 Barchaga xabar yuborish")
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
        
    await state.set_state(AdminBroadcast.waiting_for_message)
    await message.answer(
        "📢 Yubormoqchi bo'lgan xabaringizni kiriting (Matn, Rasm, Video, Audio va h.k.):\n\n"
        "<i>Jarayonni bekor qilish uchun '❌ Bekor qilish' tugmasini bosing.</i>",
        reply_markup=kb.cancel_broadcast_kb(),
        parse_mode="HTML"
    )

@router.message(AdminBroadcast.waiting_for_message, F.text == "❌ Bekor qilish")
async def cancel_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=kb.admin_main_kb())

@router.message(AdminBroadcast.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    
    await message.answer(f"🚀 Xabar <b>{len(user_ids)} ta</b> foydalanuvchiga yuborilmoqda...", parse_mode="HTML")
    
    count = 0
    blocked_count = 0
    
    for u_id in user_ids:
        try:
            await message.copy_to(chat_id=u_id)
            count += 1
        except Exception:
            blocked_count += 1
            
    await message.answer(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"📨 Muvaffaqiyatli yetib bordi: <b>{count} ta</b>\n"
        f"🚫 Botni bloklaganlar: <b>{blocked_count} ta</b>",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )


@router.message(F.text == "📢 Kanal qo'shish")
async def request_channel_add(message: types.Message, state: FSMContext):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    await state.set_state(AdminChannelAdd.waiting_for_channel)
    await message.answer(
        "📢 <b>Yangi kanal qo'shish</b>\n\n"
        "Kanal username'ini yuboring, masalan: <code>@yangi_kanal</code>\n"
        "Yoki <code>https://t.me/yangi_kanal</code> ko'rinishida yuboring.\n\n"
        "Bot yangi kanalga kirgan yoki admin bo'lgan bo'lishi kerak.",
        reply_markup=kb.cancel_kb(),
        parse_mode="HTML"
    )


@router.message(F.text == "🗑 Kanalni o'chirish")
async def show_channel_remover(message: types.Message):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    removable = [
        channel_id for channel_id in channels.get_channels()
        if channel_id != channels._normalize_channel(config.CHANNEL_ID)
    ]
    if not removable:
        await message.answer(
            "ℹ️ O'chirish uchun qo'shilgan kanal yo'q.",
            reply_markup=kb.admin_main_kb()
        )
        return
    await message.answer(
        "🗑 <b>O'chiriladigan kanalni tanlang:</b>",
        reply_markup=kb.admin_channel_remove_kb(removable),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "remove_channel_back")
async def channel_remover_back(callback: types.CallbackQuery):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer(
        "👨‍💻 <b>Admin paneli</b>",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_channel:"))
async def remove_selected_channel(callback: types.CallbackQuery):
    if callback.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    channel_id = callback.data.split(":", 1)[1]
    if channels.remove_channel(channel_id):
        sub_cache.clear()
        await callback.answer("Kanal o'chirildi")
    else:
        await callback.answer("Asosiy kanalni o'chirib bo'lmaydi", show_alert=True)
    removable = [
        item for item in channels.get_channels()
        if item != channels._normalize_channel(config.CHANNEL_ID)
    ]
    if removable:
        await safe_edit_message(
            callback.message,
            text="🗑 <b>O'chiriladigan kanalni tanlang:</b>",
            reply_markup=kb.admin_channel_remove_kb(removable),
            parse_mode="HTML"
        )
    else:
        await callback.message.delete()
        await callback.message.answer("✅ Barcha qo'shilgan kanallar o'chirildi.", reply_markup=kb.admin_main_kb())


@router.message(AdminChannelAdd.waiting_for_channel)
async def save_new_channel(message: types.Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in [config.ADMIN_ID, config.ADMIN_ID_2]:
        return
    value = (message.text or "").strip()
    if not value or " " in value or value in {"@", "https://t.me/", "t.me/"}:
        await message.answer("⚠️ Kanal username'i noto'g'ri. Masalan: @yangi_kanal")
        return

    channel_id = channels.add_channel(value)
    try:
        await bot.get_chat(channel_id)
    except Exception:
        channels_list = channels.get_channels()
        if channel_id in channels_list and len(channels_list) > 1:
            channels_list.remove(channel_id)
            channels.save_channels(channels_list)
        await message.answer(
            "❌ Kanal topilmadi yoki bot kanalga kira olmaydi. Username va bot huquqlarini tekshiring."
        )
        return

    await state.clear()
    sub_cache.clear()
    channel_list = "\n".join(f"{index}. {item}" for index, item in enumerate(channels.get_channels(), 1))
    await message.answer(
        f"✅ Kanal qo'shildi: <b>{channel_id}</b>\n\n"
        f"📋 <b>Majburiy kanallar:</b>\n{channel_list}",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )