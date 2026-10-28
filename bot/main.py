import asyncio
import logging
import os
import re
import sys
import time

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)

sys.path.insert(0, "/root/sheikh")
sys.path.insert(0, "/root/sheikh/realbot")
sys.path.insert(0, "/root/sheikh/modules")
import config
from database import db
from freeze_handler import router as freeze_router

from modules import crypto as crypto_mod
from modules import (
    downloader,
    group_advanced,
    group_extra,
    group_fun,
    group_locks,
    group_members,
    group_panel,
    iva_handlers,
    user_self,
)
from modules import remote as remote_shop
from modules import search as search_mod
from modules import wallet_checker as _wc
from modules.emojis import pe, pt
from modules.keyboards import (
    ALL_PACKAGES,
    admin_kyc_menu,
    admin_menu,
    admin_receipt_menu,
    back_button,
    buy_menu,
    buy_points_menu,
    charge_amounts_menu,
    crypto_charge_amounts_menu,
    fun_menu,
    kyc_cancel_menu,
    main_menu,
    premium_menu,
    remote_cart_menu,
    remote_cat_menu,
    remote_charge_menu,
    remote_main_menu,
    remote_my_account_menu,
    remote_my_subs_menu,
    remote_payment_menu,
    remote_shop_menu,
    search_confirm,
    search_menu,
    support_menu,
    wallet_menu,
)
from modules.states import S

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/sheikh.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
bot = Bot(
    token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
AI_SESSIONS = {}
AI_COUNT = {}

dp = Dispatcher()
dp.include_router(freeze_router)


@dp.message(F.text.in_(["تگ", "/tag", "/تگ"]))
async def cmd_tag_menu(m: Message):
    if m.chat.type not in ("group", "supergroup"):
        return
    try:
        member = await m.chat.get_member(m.from_user.id)
        if member.status not in ("administrator", "creator"):
            await m.reply("❌ فقط ادمین‌های گروه می‌تونن تگ بزنن")
            return
    except Exception as e:
        logging.error(f"tag admin check err: {e}")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 تگ همه اعضا", callback_data="tg_all")],
            [InlineKeyboardButton(text="👑 تگ مقام‌دارها", callback_data="tg_admins")],
            [InlineKeyboardButton(text="❌ بستن", callback_data="tg_close")],
        ]
    )
    await m.reply("🏷 <b>منوی تگ</b>\n\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=kb)


@dp.callback_query(F.data == "tg_close")
async def cb_tg_close(cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.answer("❌ بسته شد")


@dp.callback_query(F.data == "tg_all")
async def cb_tg_all(cb: CallbackQuery):
    if cb.message.chat.type not in ("group", "supergroup"):
        await cb.answer("فقط توی گروه", show_alert=True)
        return
    try:
        member = await cb.bot.get_chat_member(cb.message.chat.id, cb.from_user.id)
        if member.status not in ("administrator", "creator"):
            await cb.answer("❌ فقط ادمین‌ها", show_alert=True)
            return
    except Exception:
        await cb.answer("خطا", show_alert=True)
        return

    await cb.answer("⏳")
    await cb.message.edit_text("⏳ در حال تگ کردن همه اعضا...")

    try:
        mentions = []
        offset = 0
        while True:
            members = await cb.bot.get_chat_members(
                cb.message.chat.id, limit=200, offset=offset
            )
            if not members:
                break
            for m in members:
                if m.user.is_bot:
                    continue
                name = m.user.first_name or "کاربر"
                mentions.append(f'<a href="tg://user?id={m.user.id}">{name}</a>')
            if len(members) < 200:
                break
            offset += 200

        if not mentions:
            await cb.message.edit_text("❌ عضوی پیدا نشد")
            return

        chunks = [mentions[i : i + 30] for i in range(0, len(mentions), 30)]
        await cb.message.edit_text(
            f"🏷 <b>تگ همه</b> ({len(mentions)} نفر):\n\n" + "، ".join(chunks[0])
        )
        for chunk in chunks[1:]:
            await cb.message.reply("، ".join(chunk))
    except Exception as e:
        logging.error(f"tg_all err: {e}")
        await cb.message.edit_text("❌ خطا")


@dp.callback_query(F.data == "tg_admins")
async def cb_tg_admins(cb: CallbackQuery):
    if cb.message.chat.type not in ("group", "supergroup"):
        await cb.answer("فقط توی گروه", show_alert=True)
        return
    try:
        member = await cb.bot.get_chat_member(cb.message.chat.id, cb.from_user.id)
        if member.status not in ("administrator", "creator"):
            await cb.answer("❌ فقط ادمین‌ها", show_alert=True)
            return
    except Exception:
        await cb.answer("خطا", show_alert=True)
        return

    await cb.answer("⏳")
    try:

        admins = await cb.bot.get_chat_administrators(cb.message.chat.id)

        mentions = []
        for adm in admins:
            if adm.user.is_bot:
                continue
            name = adm.user.first_name or "کاربر"
            mentions.append(f'<a href="tg://user?id={adm.user.id}">{name}</a>')

        if not mentions:
            await cb.message.edit_text("❌ ادمینی پیدا نشد")
            return
        await cb.message.edit_text(
            f"👑 <b>تگ مقام‌دارها</b> ({len(mentions)} نفر):\n\n" + "، ".join(mentions)
        )
    except Exception as e:
        logging.error(f"tg_admins err: {e}")
        await cb.message.edit_text("❌ خطا")


# ═══════════════════════════════════════════════
# پنل سلف — توی پیوی ربات اصلی (اولویت بالا)
# ═══════════════════════════════════════════════


@dp.message(
    F.chat.type == "private", F.text.regexp(r"^(/panel|/panel_self|پنل|پنل سلف)$")
)
async def cmd_self_panel_first(m: Message, state: FSMContext):
    print(f"🚨🚨🚨 PANEL TRIGGERED: text={m.text!r} uid={m.from_user.id}", flush=True)
    await state.clear()
    uid = m.from_user.id
    try:
        is_active = user_self.is_self_active(uid)
    except Exception as e:
        print(f"❌ is_self_active err: {e}", flush=True)
        is_active = False
    print(f"🚨 is_self_active={is_active}", flush=True)

    if not is_active:
        await m.answer(
            "برای استفاده از پنل سلف، اول باید از منوی سرگرمی\n"
            "گزینه «🔓 سلف رایگان» رو بزنی و شماره‌ات رو بدی.",
            reply_markup=back_button("menu_fun"),
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔓 فعال‌سازی سلف رایگان", callback_data="self_activate"
                )
            ],
            [
                InlineKeyboardButton(text="💫 ری‌اکشن", callback_data="self_reaction"),
                InlineKeyboardButton(
                    text="⏰ ساعت پروفایل", callback_data="self_clock"
                ),
            ],
            [
                InlineKeyboardButton(text="📝 منشی", callback_data="self_secretary"),
                InlineKeyboardButton(text="👤 دشمن", callback_data="self_enemy"),
            ],
            [
                InlineKeyboardButton(text="🚫 بلاک", callback_data="self_block"),
                InlineKeyboardButton(text="🌐 ترجمه", callback_data="self_translate"),
            ],
            [InlineKeyboardButton(text="❌ بستن", callback_data="self_close")],
        ]
    )
    await m.answer(
        "🛠 <b>پنل سلف</b>\n" "━━━━━━━━━━━━━━━━━━━━\n\n" "یکی از امکانات رو انتخاب کن:",
        reply_markup=kb,
    )


PENDING = {}
AI_COUNT = {}


def is_admin(uid):
    return uid in config.ADMIN_IDS


def welcome_text(u, uid):
    prem = pe("✅") + " فعال" if db.is_premium(uid) else pe("❌") + " غیرفعال"
    self_status = (
        pe("✅") + " فعال" if user_self.is_self_active(uid) else pe("❌") + " غیرفعال"
    )
    acc = "پریمیوم " + pe("💎") if db.is_premium(uid) else "حساب عادی"
    name = u.get("first_name") or "کاربر"
    return (
        f"{pe('🔴')} <b>HELLO : {name}</b>\n\n"
        f"{pe('👋')} <b>خوش اومدی دوباره</b>\n\n"
        f"├ {pe('📊')} رکوردهای موجود: <b>0</b>\n"
        f"├ {pe('📦')} سفارش‌های تو: <b>0</b>\n"
        f"├ 🆓 نوع حساب: <b>{acc}</b>\n"
        f"├ {pe('💰')} امتیاز تو: <b>{u['points']}</b>\n"
        f"├ {pe('💎')} پریمیوم: <b>{prem}</b>\n"
        f"└ {pe('🔓')} اشتراک سلف: <b>{self_status}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('💵')} هر جستجو: <b>{config.COST_SEARCH} امتیاز</b>\n"
        f"{pe('💎')} کاربر پریمیوم: جستجوی نامحدود\n"
        f"ℹ️ اطلاعات من: رایگان\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{pe('👇')} از دکمه‌های زیر استفاده کن:"
    )


# ═══════════════════════════════════════════════
# Verification (عضویت + ثبت‌نام سایت)
# ═══════════════════════════════════════════════
FORCE_CHANNEL = "@MozahemYab_Sheikh"  # کانال اجباری
SITE_URL = "https://sheikhpanel.duckdns.org"  # آدرس سایت
BOT_SECRET = "sheikh_bot_2026_xK9mN3"  # همون secret که توی Flask گذاشتیم

VERIFY_MSG = (
    "🔒 <b>برای استفاده از ربات این مراحل رو انجام بده:</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "1️⃣ <b>عضویت در کانال</b>\n"
    f"   🔗 {FORCE_CHANNEL}\n\n"
    "بعد از عضویت، دکمه زیر رو بزن:\n"
)

REMOTE_MSG = pt(
    pe("🖥")
    + " <b>پکیج‌های ریموت فیشینگ اندروید</b>\n\n"
    + pe("🔓")
    + " <b>هک اندروید</b> — دسترسی کامل به گوشی هدف\n\n"
    + pe("📱")
    + " <b>امکانات ریموت:</b>\n"
    + "├ "
    + pe("📸")
    + " دسترسی کامل به دوربین (جلو و عقب)\n"
    + "├ "
    + pe("🎤")
    + " شنود زنده صدای محیط\n"
    + "├ "
    + pe("💬")
    + " خواندن تمام پیام‌ها و واتس‌اپ\n"
    + "├ "
    + pe("📁")
    + " دسترسی به گالری، فیلم و فایل‌ها\n"
    + "├ "
    + pe("🔑")
    + " استخراج تمام رمزهای عبور\n"
    + "├ 📞 لیست تماس‌ها و شنود مکالمات\n"
    + "├ 📍 ردیابی زنده موقعیت مکانی\n"
    + "├ "
    + pe("🌐")
    + " مرور مخفیانه اینترنت\n"
    + "├ 🔒 قفل/آنلاک از راه دور\n"
    + "├ "
    + pe("⌨️")
    + " کیلاگر (ثبت تایپ‌ها)\n"
    + "├ "
    + pe("🗑")
    + " حذف/مخفی کردن فایل‌ها\n"
    + "└ "
    + pe("🕵️")
    + " کاملاً مخفی — بدون شناسایی\n\n"
    + pe("💎")
    + " <b>سه پلن حرفه‌ای:</b>\n"
    + "• "
    + pe("🥉")
    + " پلن نوب — ۱۵ روزه\n"
    + "• "
    + pe("🥈")
    + " پلن پایه — ۱ ماهه\n"
    + "• "
    + pe("🥇")
    + " پلن حرفه‌ای — ۳ ماه + هدیه ۳ روز\n\n"
    + pe("🎁")
    + " <b>تنها ریموت ایرانی با تست رایگان ۵ دقیقه‌ای!</b>"
)

WEBSITE_MSG = pt(
    pe("🌐")
    + " <b>وب‌سایت رسمی شیخ</b>\n\n"
    + "به پنل رسمی ما سر بزن و از امکانات ویژه استفاده کن.\n\n"
    + pe("🚀")
    + " <b>sheikhpanel.duckdns.org</b>\n\n"
    + "━━━━━━━━━━━━━━━━━━━━\n"
    + pe("✨")
    + " <b>امکانات سایت:</b>\n"
    + "├ "
    + pe("🤖")
    + " چت با DJ-AI (۱۵ پیام رایگان)\n"
    + "├ 📦 مشاهده پکیج‌ها و قیمت‌ها\n"
    + "├ 🎯 استعلام دستی حرفه‌ای\n"
    + "├ "
    + pe("📊")
    + " داشبورد کاربری\n"
    + "└ "
    + pe("💬")
    + " پشتیبانی مستقیم\n\n"
    + "━━━━━━━━━━━━━━━━━━━━\n"
    + pe("🎁")
    + " <b>تخفیف ویژه کاربران جدید!</b>"
)


def verify_channel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 عضویت در کانال",
                    url=f"https://t.me/{FORCE_CHANNEL.lstrip('@')}",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ عضو شدم",
                    callback_data="verify_joined_channel",
                    style="success",
                )
            ],
        ]
    )


def verify_site_kb(user_id: int):

    site_link = f"{SITE_URL}/auth-x9k2m?tg_id={user_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 ورود به سایت", url=site_link, style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ ثبت‌نام کردم",
                    callback_data="verify_site_done",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو", callback_data="menu_home", style="danger"
                )
            ],
        ]
    )


async def send_promo_messages(m):
    kb_remote = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 مشاهده اشتراک‌های ریموت",
                    callback_data="show_remote_plans",
                    style="success",
                )
            ],
        ]
    )
    sent1 = await m.answer(REMOTE_MSG, reply_markup=kb_remote)

    kb_web = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 وب‌سایت رسمی شیخ",
                    url="https://sheikhpanel.duckdns.org",
                    style="success",
                )
            ],
        ]
    )
    sent2 = await m.answer(WEBSITE_MSG, reply_markup=kb_web)

    try:
        await bot.pin_chat_message(
            m.chat.id, sent1.message_id, disable_notification=True
        )
        await bot.pin_chat_message(
            m.chat.id, sent2.message_id, disable_notification=True
        )
    except Exception as e:
        logging.error(f"pin err: {e}")


@dp.callback_query(F.data == "show_remote_plans")
async def cb_show_remote_plans(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ تماس با پشتیبانی",
                    url="https://t.me/PV_GaBrieel",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="menu_home", style="danger"
                )
            ],
        ]
    )
    await cb.message.answer(
        "🖥 <b>پکیج‌های ریموت</b>\n\n"
        "🎯 <b>سه پلن:</b>\n\n"
        "💠 <b>نوب</b> — ۱۵ روزه\n"
        "💠 <b>پایه</b> — ۱ ماهه\n"
        "💠 <b>حرفه‌ای</b> — ۳ ماه + هدیه ۳ روز\n\n"
        "🎁 <b>تنها ریموت ایرانی با تست رایگان ۵ دقیقه‌ای</b>\n\n"
        "💰 برای خرید، به پیوی ادمین مراجعه کن",
        reply_markup=kb,
    )
    await cb.answer()


@dp.message(Command("oldremote"))
async def cmd_remote(m: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 مشاهده اشتراک‌های ریموت",
                    callback_data="show_remote_plans",
                    style="success",
                )
            ],
        ]
    )
    await m.answer(REMOTE_MSG, reply_markup=kb)


# ═══════════════════════════════════════════════
# Verification helpers
# ═══════════════════════════════════════════════


async def is_member_of_channel(user_id: int) -> bool:
    """چک کن کاربر عضو کاناله"""
    try:
        m = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return m.status not in ("left", "kicked")
    except Exception as e:
        logging.warning(f"channel check err: {e}")
        # اگه ربات توی کانال نیست یا خطا داد، اجازه بده
        return True


async def is_registered_on_site(user_id: int) -> bool:
    """چک کن کاربر توی سایت ثبت‌نام کرده"""
    try:
        import aiohttp

        url = f"{SITE_URL}/api/check-registered"
        async with aiohttp.ClientSession() as s, s.post(
            url,
            json={
                "secret": BOT_SECRET,
                "tg_id": user_id,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return False  # اگه سایت خطا داد، کاربر رو آزاد نکن
            data = await r.json()
            return bool(data.get("registered"))
    except Exception as e:
        logging.error(f"site check err: {e}")
        return False  # اگه سایت داون بود، کاربر رو آزاد نکن


async def is_user_verified(m: Message, user_id: int) -> bool:
    """چک تایید کانال و سایت + زبان"""
    u = db.get_user(user_id)

    # ─── چک کانال ───
    if not await is_member_of_channel(user_id):
        await m.answer(
            "🔒 <b>اول باید عضو کانال ما شی</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📢 کانال: {FORCE_CHANNEL}\n\n"
            "بعد از عضویت، دکمه زیر رو بزن:",
            reply_markup=verify_channel_kb(),
        )
        return False

    # ─── چک سایت ───
    try:
        site_ok = await is_registered_on_site(user_id)
    except Exception as e:
        logging.error(f"site check err: {e}")
        site_ok = False

    if not site_ok:
        await m.answer(
            "🌐 <b>حالا توی سایت ثبت‌نام کن</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "با زدن دکمه زیر، خودکار وارد سایت می‌شی.\n"
            "با Google وارد شو.\n\n"
            "بعد از ثبت‌نام برگرد و دکمه <b>✅ ثبت‌نام کردم</b> رو بزن.",
            reply_markup=verify_site_kb(user_id),
        )
        return False

    # همه چیز OK
    try:
        db.cur.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
        db.conn.commit()
    except Exception:
        pass

    # ─── چک زبان (اگه انتخاب نشده بود، منوی زبان) ───
    if not u.get("lang"):
        from modules.keyboards import menu_lang_i18n

        await m.answer(
            "🌐 <b>انتخاب زبان / Choose Language</b>\n\n" "زبان خود را انتخاب کنید:",
            reply_markup=menu_lang_i18n(),
        )
        return False

    return True


@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    logging.info(f"CMD_START called by {m.from_user.id}")
    await state.clear()
    uid = m.from_user.id
    u = db.get_user(uid)
    db.cur.execute(
        "UPDATE users SET first_name=? WHERE user_id=?", (m.from_user.first_name, uid)
    )
    db.conn.commit()

    # ─── چک تایید کانال و سایت ───
    try:
        is_verified = await is_user_verified(m, uid)
        if not is_verified:
            return
    except Exception as e:
        logging.error(f"verify check err: {e}")
        return

    logging.info(f"CMD_START: sending welcome to {uid}")
    try:
        txt = welcome_text(u, uid)
        kb = main_menu(uid, config.ADMIN_IDS)
        await m.answer(txt, reply_markup=kb)
        logging.info(f"CMD_START: sent OK to {uid}")
    except Exception as e:
        logging.error(f"CMD_START ERROR: {type(e).__name__}: {e}")
        try:
            await m.answer(f"❌ Error: {type(e).__name__}: {str(e)[:150]}")
        except Exception:
            pass


@dp.callback_query(F.data == "verify_joined_channel")
async def cb_verify_channel(cb: CallbackQuery):
    uid = cb.from_user.id
    if not await is_member_of_channel(uid):
        await cb.answer("❌ هنوز عضو کانال نشدی!", show_alert=True)
        return
    await cb.answer("✅ عضویت تایید شد")
    txt = (
        "🌐 <b>حالا توی سایت ثبت‌نام کن</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "با زدن دکمه زیر، خودکار وارد سایت می‌شی.\n"
        "با Google وارد شو.\n\n"
        "بعد از ثبت‌نام برگرد و دکمه <b>✅ ثبت‌نام کردم</b> رو بزن."
    )
    try:
        await cb.message.edit_text(
            txt,
            reply_markup=verify_site_kb(uid),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        await cb.message.answer(
            txt,
            reply_markup=verify_site_kb(uid),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


@dp.callback_query(F.data == "verify_site_done")
async def cb_verify_site(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    await cb.answer("🔍 در حال بررسی...")
    if not await is_registered_on_site(uid):
        try:
            await cb.message.edit_text(
                "❌ <b>هنوز توی سایت ثبت‌نام نکردی</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "دکمه زیر رو بزن، با Google وارد شو، بعد برگرد.",
                reply_markup=verify_site_kb(uid),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return

    try:
        db.cur.execute("UPDATE users SET verified=1 WHERE user_id=?", (uid,))
        db.conn.commit()
    except Exception:
        pass

    await cb.answer("✅ تایید شد!")
    try:
        await cb.message.edit_text(
            "🎉 <b>تبریک!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ عضویت کانال تایید شد\n"
            "✅ ثبت‌نام سایت تایید شد\n\n"
            "حالا به منوی اصلی خوش آمدی!"
        )
    except Exception:
        pass

    import asyncio

    await asyncio.sleep(1)
    u = db.get_user(uid)
    await cb.message.answer(
        welcome_text(u, uid), reply_markup=main_menu(uid, config.ADMIN_IDS)
    )
    if not u.get("website_pinned"):
        await send_promo_messages(cb.message)
        try:
            db.cur.execute("UPDATE users SET website_pinned=1 WHERE user_id=?", (uid,))
            db.conn.commit()
        except Exception:
            pass


@dp.callback_query(F.data == "menu_home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    AI_SESSIONS.pop(cb.from_user.id, None)
    AI_COUNT.pop(cb.from_user.id, None)
    u = db.get_user(cb.from_user.id)
    try:
        await cb.message.edit_text(
            welcome_text(u, cb.from_user.id),
            reply_markup=main_menu(cb.from_user.id, config.ADMIN_IDS),
        )
    except:
        await cb.message.answer(
            welcome_text(u, cb.from_user.id),
            reply_markup=main_menu(cb.from_user.id, config.ADMIN_IDS),
        )
    await cb.answer()


# ============================================================
# جستجو
# ============================================================
@dp.callback_query(F.data == "menu_search")
async def cb_search(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    u = db.get_user(cb.from_user.id)
    is_prem = db.is_premium(cb.from_user.id)
    cost = 0 if is_prem else config.COST_SEARCH
    txt = (
        f"🔍 <b>جستجو مزاحم</b>\n\n"
        f"💰 موجودی: <b>{u['points']}</b> امتیاز\n"
        f"💳 هزینه: <b>{cost if cost > 0 else 'رایگان (پریمیوم)'}</b>\n\n"
        f"روش جستجو رو انتخاب کن 👇"
    )
    try:
        await cb.message.edit_text(txt, reply_markup=search_menu())
    except:
        await cb.message.answer(txt, reply_markup=search_menu())
    await cb.answer()


SRCH_LABELS = {
    "phone": "📱 شماره تلفن",
    "name": "👤 نام و نام خانوادگی",
    "tgid": "🆔 آیدی عددی",
    "username": "🌐 یوزرنیم",
    "nid": "✅ کد ملی",
    "card": "💳 شماره کارت",
}


@dp.callback_query(F.data.in_([f"srch_{k}" for k in SRCH_LABELS]))
async def cb_srch_type(cb: CallbackQuery, state: FSMContext):
    t = cb.data.replace("srch_", "")
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    u = db.get_user(uid)
    if not is_prem and u["points"] < config.COST_SEARCH:
        await cb.answer(
            f"❌ امتیاز کم ({u['points']}/{config.COST_SEARCH})", show_alert=True
        )
        return
    await state.update_data(search_type=t, search_label=SRCH_LABELS[t])
    await cb.message.edit_text(
        f"🔎 <b>{SRCH_LABELS[t]}</b>\n\nعبارت مورد نظر رو ارسال کن:",
        reply_markup=back_button("menu_search"),
    )
    await state.set_state(S.search_query)
    await cb.answer()


@dp.callback_query(F.data.in_(["srch_premium", "srch_manual"]))
async def cb_srch_special(cb: CallbackQuery):
    if cb.data == "srch_premium":
        from aiogram.types import WebAppInfo

        msg = (
            "⭐ <b>خدمات ویژه</b>\n\n"
            "با مینی اپ جستجوی پیشرفته، به اطلاعات کامل افراد دسترسی پیدا کن.\n\n"
            "🔍 جستجو در ۳۰۱ میلیون رکورد\n"
            "⚡ سریع و دقیق\n"
            "👇 برای شروع روی دکمه زیر بزن:"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 باز کردن مینی اپ",
                        web_app=WebAppInfo(
                            url="https://sheikhpanel.duckdns.org/miniapp"
                        ),
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💬 تماس با پشتیبانی",
                        url="https://t.me/PV_GaBrieel",
                        style="primary",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت", callback_data="menu_search", style="danger"
                    )
                ],
            ]
        )
        await cb.message.edit_text(msg, reply_markup=kb)
        await cb.answer()
        return
    else:
        from aiogram.types import WebAppInfo

        msg = (
            "🎯 <b>استعلام دستی</b>\n\n"
            "با استعلام دستی، اطلاعات کامل فرد مورد نظر رو پیدا می‌کنیم.\n\n"
            "✅ <b>۱۰۰٪ تضمینی</b>\n"
            "💰 اگه پیدا نشد، پول برگشت داده می‌شه\n\n"
            "💰 هزینه: <b>۲ ترون</b>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 شروع استعلام دستی",
                        web_app=WebAppInfo(
                            url="https://sheikhpanel.duckdns.org/manual"
                        ),
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت", callback_data="menu_search", style="danger"
                    )
                ],
            ]
        )
        await cb.message.edit_text(msg, reply_markup=kb)
        await cb.answer()
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ پیوی پشتیبانی",
                    url="https://t.me/PV_GaBrieel",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="menu_search", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(msg, reply_markup=kb)
    await cb.answer()


@dp.message(S.search_query)
async def on_search_query(m: Message, state: FSMContext):
    q = m.text.strip()
    if len(q) < 3:
        await m.answer("❌ کوتاهه:")
        return
    uid = m.from_user.id
    is_prem = db.is_premium(uid)
    u = db.get_user(uid)
    cost = 0 if is_prem else config.COST_SEARCH
    if not is_prem and u["points"] < cost:
        await m.answer(
            f"❌ <b>امتیاز کافی نداری!</b>\n\n💰 موجودی: <b>{u['points']}</b>\n💳 هزینه: <b>{cost}</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💰 خرید", callback_data="menu_buy", style="success"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 بازگشت", callback_data="menu_home", style="danger"
                        )
                    ],
                ]
            ),
        )
        await state.clear()
        return
    await state.update_data(pending_query=q, pending_cost=cost)
    lbl = f"{cost} امتیاز" if cost > 0 else "رایگان (پریمیوم)"
    await m.answer(
        f"🔍 <b>تأیید جستجو</b>\n\nعبارت: <code>{q}</code>\nهزینه: <b>{lbl}</b>\n\nموافقی؟",
        reply_markup=search_confirm(lbl),
    )


@dp.callback_query(F.data == "srch_accept")
async def cb_srch_accept(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    q = data.get("pending_query")
    cost = data.get("pending_cost", config.COST_SEARCH)
    if not q:
        await cb.answer("❌ سؤالی نیست", show_alert=True)
        return
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    if not is_prem and cost > 0:
        if not db.take_points(uid, cost):
            await cb.answer("❌ امتیاز کم", show_alert=True)
            return
    await state.clear()
    await cb.message.edit_text(f"⏳ جستجو <code>{q}</code> ...")
    await bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)
    rec = await asyncio.to_thread(search_mod.search, q)
    txt = search_mod.format_record(rec)
    db.log_search(uid, q, txt[:500], cost)
    u = db.get_user(uid)
    cost_label = "رایگان" if cost == 0 else f"{cost} امتیاز"
    if not rec:
        await cb.message.edit_text(
            f"🔎 <b>نتیجه</b>\nعبارت: <code>{q}</code>\n━━━━━━━━━━━━━━━━━━━━\n\n❌ <b>یافت نشد.</b>",
            reply_markup=back_button("menu_search"),
        )
    else:
        await cb.message.edit_text(
            f"🔎 <b>نتیجه</b>\nعبارت: <code>{q}</code>\n━━━━━━━━━━━━━━━━━━━━\n\n{txt}\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💸 هزینه: <b>{cost_label}</b>\n💰 موجودی: <b>{u['points']}</b>",
            reply_markup=back_button("menu_search"),
        )
    await cb.answer()


# ============================================================
# اطلاعات من
# ============================================================
@dp.callback_query(F.data == "menu_myinfo")
async def cb_myinfo(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 اشتراک‌گذاری شماره",
                    callback_data="myinfo_share",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 اطلاعات حساب",
                    callback_data="myinfo_account",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="menu_home", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(
        "👤 <b>اطلاعات من</b>\n\nگزینه‌ای رو انتخاب کن 👇", reply_markup=kb
    )
    await cb.answer()


@dp.callback_query(F.data == "myinfo_account")
async def cb_my_account(cb: CallbackQuery):
    u = db.get_user(cb.from_user.id)
    prem = "✅ فعال" if db.is_premium(cb.from_user.id) else "❌ غیرفعال"
    self_st = "✅ فعال" if user_self.is_self_active(cb.from_user.id) else "❌ غیرفعال"
    from datetime import datetime

    reg = datetime.fromtimestamp(u.get("registered_at", 0) or 0).strftime("%Y-%m-%d")
    await cb.message.edit_text(
        f"📊 <b>اطلاعات حساب</b>\n\n🆔 <code>{u['user_id']}</code>\n"
        f"👤 {cb.from_user.full_name}\n💰 امتیاز: <b>{u['points']}</b>\n"
        f"💎 پریمیوم: <b>{prem}</b>\n🔓 سلف: <b>{self_st}</b>\n"
        f"📱 شماره: <code>{u['phone'] or '—'}</code>\n📅 {reg}",
        reply_markup=back_button("menu_myinfo"),
    )
    await cb.answer()


@dp.callback_query(F.data == "myinfo_share")
async def cb_myinfo_share(cb: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 ارسال شماره", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await cb.message.answer(
        "📱 <b>اشتراک‌گذاری شماره</b>\n\nروی دکمه بزن 👇", reply_markup=kb
    )
    await state.set_state(S.verify_my_phone)
    await cb.answer()


@dp.message(S.verify_my_phone, F.contact)
async def on_my_phone(m: Message, state: FSMContext):
    phone = m.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.clear()
    db.set_phone(m.from_user.id, phone, verified=True)
    await m.answer("⏳ بررسی...", reply_markup=ReplyKeyboardRemove())
    rec = await asyncio.to_thread(search_mod.search, phone)
    if rec:
        txt = search_mod.format_record(rec)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 پرداخت {config.PRICE_INFO_DELETE_TRON} ترون",
                        callback_data="del_info_pay",
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت", callback_data="menu_myinfo", style="danger"
                    )
                ],
            ]
        )
        await m.answer(
            f"⚠️ <b>شماره شما در دیتابیس پیدا شد!</b>\n\n{txt}\n\n"
            f"برای حذف، <b>{config.PRICE_INFO_DELETE_TRON} ترون</b> پرداخت کن:",
            reply_markup=kb,
        )
    else:
        await m.answer(
            "✅ <b>شماره شما در دیتابیس ما نیست.</b>",
            reply_markup=back_button("menu_myinfo"),
        )


@dp.callback_query(F.data == "del_info_pay")
async def cb_del_info_pay(cb: CallbackQuery):
    pid = db.new_payment(cb.from_user.id, "del_info", config.PRICE_INFO_DELETE_TRON)
    await send_payment(
        cb, pid, "حذف اطلاعات", config.PRICE_INFO_DELETE_TRON, f"DEL{pid}", "TRX"
    )


# ============================================================
# سرگرمی
# ============================================================
@dp.callback_query(F.data == "menu_fun")
async def cb_fun(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    u = db.get_user(cb.from_user.id)
    await cb.message.edit_text(
        f"🎮 <b>سرگرمی</b>\n\n💰 امتیاز: <b>{u['points']}</b>\n\nگزینه‌ای رو انتخاب کن:",
        reply_markup=fun_menu(),
    )
    await cb.answer()


@dp.callback_query(F.data == "fun_daily")
async def cb_daily(cb: CallbackQuery):
    uid = cb.from_user.id
    u = db.get_user(uid)
    now = int(time.time())
    if now - (u["last_daily"] or 0) < 86400:
        left = 86400 - (now - (u["last_daily"] or 0))
        h, r = divmod(left, 3600)
        mm, ss = divmod(r, 60)
        await cb.answer(f"⏳ {h}ساعت {mm}دقیقه دیگه", show_alert=True)
        return
    db.add_points(uid, config.DAILY_BONUS)
    db.set_daily(uid, now)
    u = db.get_user(uid)
    await cb.message.edit_text(
        f"🎁 <b>{config.DAILY_BONUS} امتیاز</b> گرفتی!\n💰 <b>{u['points']}</b>",
        reply_markup=back_button("menu_fun"),
    )
    await cb.answer("🎁")


# ============================================================
# سلف
# ============================================================
@dp.callback_query(F.data == "fun_self")
async def cb_self(cb: CallbackQuery):
    uid = cb.from_user.id
    u = db.get_user(uid)
    is_prem = db.is_premium(uid)
    already_active = user_self.is_self_active(uid)
    if already_active:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛠 راهنما پنل",
                        callback_data="self_panel_info",
                        style="primary",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت", callback_data="menu_fun", style="danger"
                    )
                ],
            ]
        )
        await cb.message.edit_text(
            "🔓 <b>سلف رایگان</b>\n\n✅ <b>سلف شما فعال است!</b>\n\n"
            "تو اکانت خودت دستور <code>پنل</code> بزن.",
            reply_markup=kb,
        )
        await cb.answer()
        return
    cost = 0 if is_prem else config.COST_SELF
    if cost > 0 and u["points"] < cost:
        await cb.answer(f"❌ امتیاز کم ({u['points']}/{cost})", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ پذیرفتن ({cost} امتیاز)",
                    callback_data="self_accept",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="menu_fun", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(
        f"🔓 <b>سلف رایگان</b>\n\n💰 هزینه: <b>{cost} امتیاز</b>\n(برای پریمیوم رایگان)\n\n"
        f"ℹ️ <b>امکانات:</b>\n• ساعت پروفایل\n• منشی\n• دشمن\n• بلاک\n• ری‌اکشن\n• ترجمه\n\n"
        f"🔒 هیچ دیتابیسی از سشن نگه‌داری نمی‌شود.\n\nآیا موافقی؟",
        reply_markup=kb,
    )
    await cb.answer()


@dp.callback_query(F.data == "self_accept")
async def cb_self_accept(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    cost = 0 if is_prem else config.COST_SELF
    if cost > 0 and not db.take_points(uid, cost):
        await cb.answer("❌ امتیاز کم", show_alert=True)
        return
    await cb.message.edit_text(
        "📱 <b>سلف — مرحله ۱ از ۳</b>\n\n"
        "شماره اکانتت رو با فرمت بین‌المللی بفرست:\n\n"
        "مثال: <code>+989123456789</code>\n\nلغو: /cancel",
        reply_markup=back_button("menu_fun"),
    )
    await state.set_state(S.self_phone)
    await cb.answer()


@dp.message(S.self_phone)
async def on_self_phone(m: Message, state: FSMContext):
    phone = m.text.strip()
    if not re.fullmatch(r"\+\d{10,15}", phone):
        await m.answer("❌ فرمت اشتباه. مثال: <code>+989123456789</code>")
        return
    uid = m.from_user.id
    await m.answer("⏳ در حال ارسال کد...")
    res = await user_self.start_login(uid, phone)
    if not res.get("ok"):
        await m.answer(
            f"❌ خطا: {res.get('error')}\n\nلغو: /cancel",
            reply_markup=back_button("menu_fun"),
        )
        return
    await state.update_data(self_phone=phone)
    await m.answer(
        "🔐 <b>مرحله ۲ از ۳</b>\n\n"
        "کد تأیید تلگرام به اکانتت اومد.\n\n"
        "کد رو با فاصله بفرست:\nمثال: <code>1 2 3 4 5</code>\n\nلغو: /cancel"
    )
    await state.set_state(S.self_code)


@dp.message(S.self_code)
async def on_self_code(m: Message, state: FSMContext):
    uid = m.from_user.id
    code = re.sub(r"\D", "", m.text.strip())
    if not code or len(code) < 4:
        await m.answer("❌ کد نامعتبر. دوباره:")
        return
    res = await user_self.submit_code(uid, code)
    # اول چک کن رمز دو مرحله‌ای لازمه یا نه
    if res.get("need_password"):
        await m.answer(
            "🔐 <b>مرحله ۳ از ۳</b>\n\nرمز دو مرحله‌ای رو بفرست:\n\nلغو: /cancel"
        )
        await state.set_state(S.self_password)
        return
    if not res.get("ok"):
        await m.answer(f"❌ {res.get('error') or 'خطای ناشناخته'}\n\nلغو: /cancel")
        return
    await _finish_self(m, res)


@dp.message(S.self_password)
async def on_self_password(m: Message, state: FSMContext):
    uid = m.from_user.id
    res = await user_self.submit_password(uid, m.text.strip())
    if not res.get("ok"):
        await m.answer(f"❌ {res.get('error')}\n\nلغو: /cancel")
        return
    await _finish_self(m, res)


async def _finish_self(m: Message, res: dict):
    uid = m.from_user.id
    await m.answer("⏳ فعال‌سازی...")
    sres = await user_self.start_self_client(uid, res["session_string"])
    if not sres.get("ok"):
        await m.answer(f"❌ {sres.get('error')}")
        return
    try:
        db.cur.execute(
            "UPDATE users SET phone=?, phone_verified=1 WHERE user_id=?",
            (res.get("phone", ""), uid),
        )
        db.conn.commit()
    except:
        pass
    await m.answer(
        f"✅ <b>سلف فعال شد!</b>\n\n"
        f"👤 {res.get('tg_first_name') or '—'}\n"
        f"🆔 <code>{res.get('tg_user_id')}</code>\n"
        f"📱 <code>{res.get('phone')}</code>\n\n"
        f"🎉 تو <b>اکانت خودت</b> دستور <code>پنل</code> بزن.",
        reply_markup=back_button("menu_fun"),
    )


@dp.callback_query(F.data == "self_panel_info")
async def cb_self_panel_info(cb: CallbackQuery):
    await cb.message.edit_text(
        "🛠 <b>پنل سلف</b>\n\nتو اکانت خودت دستور <code>پنل</code> بزن.",
        reply_markup=back_button("menu_fun"),
    )
    await cb.answer()


# ============================================================
# بمبر
# ============================================================
@dp.callback_query(F.data == "fun_sms")
async def cb_sms(cb: CallbackQuery):
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    cost = 0 if is_prem else config.COST_SMS
    u = db.get_user(uid)
    if cost > 0 and u["points"] < cost:
        await cb.answer(f"❌ امتیاز کم ({u['points']}/{cost})", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ پذیرفتن ({cost} امتیاز)",
                    callback_data="sms_accept",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="menu_fun", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(
        f"🔥 <b>اسمس بمبر</b>\n\n💰 {cost} امتیاز\n\nموافقی؟", reply_markup=kb
    )
    await cb.answer()


@dp.callback_query(F.data == "sms_accept")
async def cb_sms_accept(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    cost = 0 if is_prem else config.COST_SMS
    if cost > 0 and not db.take_points(uid, cost):
        await cb.answer("❌ امتیاز کم", show_alert=True)
        return
    await cb.message.edit_text(
        "📱 شماره هدف:\n\n<code>09123456789</code>\n\nلغو: /cancel",
        reply_markup=back_button("menu_fun"),
    )
    await state.set_state(S.sms_phone)
    await cb.answer()


@dp.message(S.sms_phone)
async def on_sms_phone(m: Message, state: FSMContext):
    await state.clear()
    phone = m.text.strip()
    if not re.fullmatch(r"(\+?98|0)?9\d{9}", phone.replace(" ", "")):
        await m.answer("❌ فرمت اشتباه:", reply_markup=back_button("menu_fun"))
        return

    await m.answer("🔥 بمبارد شروع شد...")

    result = await sms_bomber.run_bomber(phone, rounds=50, concurrency=30)

    status = "✅" if result["success"] > 0 else "⚠️"
    note = "" if result["success"] > 0 else "\n\n⚠️ API ها در حال حاضر پاسخ نمی‌دهند."
    await m.answer(
        f"{status} <b>بمبارد تموم شد</b>\n\n"
        f"📤 موفق: <b>{result['success']}</b>\n"
        f"❌ ناموفق: <b>{result['failed']}</b>{note}",
        reply_markup=back_button("menu_fun"),
    )


# ============================================================
# خرید / پریمیوم / پرداخت
# ============================================================
@dp.callback_query(F.data == "menu_buy")
async def cb_buy(cb: CallbackQuery):
    u = db.get_user(cb.from_user.id)
    await cb.message.edit_text(
        f"💰 <b>خرید امتیاز</b>\n\n💰 موجودی: <b>{u['points']}</b>\n\nبسته:",
        reply_markup=buy_menu(),
    )
    await cb.answer()


@dp.callback_query(F.data.regexp(r"^buy_\d+$"))
async def cb_buy_pick(cb: CallbackQuery):
    pts = int(cb.data.split("_")[1])
    prices = {100: 50000, 150: 75000, 200: 100000, 300: 150000}
    toman = prices[pts]
    trx = round(toman / 50000 * 0.3, 2)
    pid = db.new_payment(cb.from_user.id, f"points_{pts}", pts)
    await send_payment(cb, pid, f"{pts} امتیاز — {toman:,}ت", trx, f"PTS{pid}", "TRX")


@dp.callback_query(F.data == "menu_premium")
async def cb_premium(cb: CallbackQuery):
    await cb.message.edit_text(
        f"💎 <b>پریمیوم</b>\n\n✅ جستجو نامحدود\n✅ اسمس رایگان\n✅ سلف رایگان\n\n"
        f"💰 <b>{config.PRICE_PREMIUM_TRON} ترون</b> (۳۰ روز)",
        reply_markup=premium_menu(),
    )
    await cb.answer()


@dp.callback_query(F.data == "prem_pay")
async def cb_prem_pay(cb: CallbackQuery):
    pid = db.new_payment(cb.from_user.id, "premium", config.PRICE_PREMIUM_TRON)
    await send_payment(
        cb, pid, "پریمیوم ۳۰ روزه", config.PRICE_PREMIUM_TRON, f"PRM{pid}", "TRX"
    )


async def send_payment(cb, pid, kind, amount, memo, currency):
    wallet = config.TRON_WALLET if currency == "TRX" else config.TON_WALLET
    url = f"https://tronscan.org/#/transfer?to={wallet}&amount={amount}&token=TRX"
    txt = (
        f"💳 <b>درگاه پرداخت</b>\n\n🔹 {kind}\n🔹 مقدار: <b>{amount} {currency}</b>\n\n"
        f"📍 ولت:\n<code>{wallet}</code>\n\n📝 ممو: <code>{memo}</code>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 باز کردن کیف پول", url=url, style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ پرداخت کردم",
                    callback_data=f"paycheck_{pid}",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="menu_fun", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(txt, reply_markup=kb, disable_web_page_preview=True)
    await cb.answer()


@dp.callback_query(F.data.startswith("paycheck_"))
async def cb_paycheck(cb: CallbackQuery):
    pid = int(cb.data.split("_")[1])
    PENDING[cb.from_user.id] = pid
    await cb.message.edit_text(
        "📝 <b>هش تراکنش</b> رو بفرست:\n\n(۶۴ hex)\n\nلغو: /cancel"
    )
    await cb.answer()


@dp.message(Command("cancel"))
async def cmd_cancel(m: Message, state: FSMContext):
    uid = m.from_user.id
    await user_self.cancel_login(uid)
    await state.clear()
    AI_SESSIONS.pop(uid, None)
    AI_COUNT.pop(uid, None)
    PENDING.pop(uid, None)
    await m.answer("❌ لغو شد.", reply_markup=back_button("menu_home"))


@dp.message(F.text.regexp(r"^[0-9a-fA-F]{64}$"))
async def on_tx_hash(m: Message, state: FSMContext):
    uid = m.from_user.id
    pid = PENDING.pop(uid, None)
    if not pid:
        return
    tx = m.text.strip()
    db.cur.execute("SELECT * FROM payments WHERE id=?", (pid,))
    r = db.cur.fetchone()
    if not r:
        await m.answer("❌ پیدا نشد")
        return
    p = dict(r)
    await m.answer("⏳ بررسی...")
    info = await crypto_mod.auto_check(tx, 0.1)
    if not info.get("ok"):
        await m.answer(
            f"❌ تأیید نشد: {info.get('reason')}\n\n👉 @PV_GaBrieel",
            reply_markup=back_button("menu_home"),
        )
        return
    db.set_payment_hash(pid, tx)
    db.mark_payment_paid(pid)
    if p["kind"].startswith("wallet_charge_"):
        toman = int(p["kind"].split("_")[-1])
        # آپدیت موجودی و مجموع شارژ
        db.cur.execute(
            "UPDATE users SET wallet_balance=wallet_balance+?, total_charged_toman=total_charged_toman+?, daily_charged=daily_charged+?, last_charge_date=? WHERE user_id=?",
            (toman, toman, uid),
        )
        db.conn.commit()
        u = db.get_user(uid)
        await m.answer(
            f"✅ <b>{toman:,} تومان به کیف پولت اضافه شد!</b>\n💰 موجودی: {u['wallet_balance']:,} تومان",
            reply_markup=back_button("menu_wallet"),
        )
    elif p["kind"].startswith("points_"):
        pts = int(p["kind"].split("_")[1])
        db.add_points(uid, pts)
        u = db.get_user(uid)
        await m.answer(
            f"✅ <b>{pts} امتیاز اضافه شد!</b>\n💰 {u['points']}",
            reply_markup=back_button("menu_fun"),
        )
    elif p["kind"] == "del_info":
        await m.answer("✅ ثبت شد.", reply_markup=back_button("menu_home"))
    elif p["kind"] == "premium":
        db.set_premium(uid, days=30)
        await m.answer(
            "✅ <b>پریمیوم ۳۰ روزه فعال شد!</b>", reply_markup=back_button("menu_fun")
        )


# ============================================================
# پشتیبانی
# ============================================================
@dp.callback_query(F.data == "menu_support")
async def cb_support(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "🆘 <b>پشتیبانی</b>\n\nچطور کمکت کنیم؟", reply_markup=support_menu()
    )
    await cb.answer()


@dp.callback_query(F.data == "sup_ai")
async def cb_sup_ai(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    is_prem = db.is_premium(uid)
    cost = 0 if is_prem else config.COST_AI
    u = db.get_user(uid)
    if cost > 0 and u["points"] < cost:
        await cb.answer(f"❌ امتیاز کم ({u['points']}/{cost})", show_alert=True)
        return
    if cost > 0 and not db.take_points(uid, cost):
        await cb.answer("❌", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 شروع چت AI (Mini App)",
                    web_app=WebAppInfo(url="https://sheikhpanel.duckdns.org/chat"),
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="menu_support", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(
        f"🤖 <b>پشتیبانی هوش مصنوعی</b>\n\n"
        f"💰 هزینه پرداخت‌شده: <b>{cost} امتیاز</b>\n"
        f"🎫 اعتبار: <b>۱۵ پیام رایگان</b>\n\n"
        f"👇 روی دکمه زیر بزن تا Mini App باز شه.",
        reply_markup=kb,
    )
    await cb.answer()


@dp.callback_query(F.data == "sup_ticket")
async def cb_sup_ticket(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "📩 <b>تیکت</b>\n\nپیامت:\n\nلغو: /cancel",
        reply_markup=back_button("menu_support"),
    )
    await state.set_state(S.ticket_msg)
    await cb.answer()


@dp.message(S.ticket_msg)
async def on_ticket(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    for admin in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin,
                f"📩 <b>تیکت</b>\n\n👤 <a href='tg://user?id={uid}'>{m.from_user.full_name}</a>\n"
                f"🆔 <code>{uid}</code>\n\n{m.text}\n\nپاسخ: <code>/reply {uid} متن</code>",
            )
        except Exception as e:
            logging.error(f"ticket {e}")
    await m.answer("✅ ثبت شد.", reply_markup=back_button("menu_home"))


# ============================================================
# پنل ادمین
# ============================================================
@dp.callback_query(F.data == "menu_admin")
async def cb_admin(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔️", show_alert=True)
        return
    cur = db.cur
    cur.execute("SELECT COUNT(*) c FROM users")
    t = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM searches")
    s = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM payments WHERE status='paid'")
    pp = cur.fetchone()["c"]
    cur.execute(
        "SELECT COUNT(*) c FROM users WHERE premium=1 AND premium_until > ?",
        (int(time.time()),),
    )
    pm = cur.fetchone()["c"]
    await cb.message.edit_text(
        f"🛠 <b>ادمین</b>\n\n👥 {t}\n💎 {pm}\n🔍 {s}\n💳 {pp}", reply_markup=admin_menu()
    )
    await cb.answer()


@dp.callback_query(F.data == "adm_users")
async def cb_adm_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    db.cur.execute(
        "SELECT user_id, points, premium, premium_until FROM users ORDER BY registered_at DESC LIMIT 30"
    )
    rows = db.cur.fetchall()
    lines = ["👥 <b>۳۰ کاربر آخر</b>\n"]
    for r in rows:
        prem = "💎" if r["premium"] and r["premium_until"] > time.time() else ""
        lines.append(f"• <code>{r['user_id']}</code> {prem} — {r['points']}pts")
    await cb.message.edit_text(
        "\n".join(lines) if rows else "خالی", reply_markup=back_button("menu_admin")
    )
    await cb.answer()


@dp.callback_query(F.data == "adm_give_points")
async def cb_adm_gp(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.update_data(admin_action="give_points")
    await cb.message.edit_text(
        "➕ <code>UID AMOUNT</code>", reply_markup=back_button("menu_admin")
    )
    await state.set_state(S.admin_input)
    await cb.answer()


@dp.callback_query(F.data == "adm_give_prem")
async def cb_adm_gprem(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.update_data(admin_action="give_prem")
    await cb.message.edit_text(
        "💎 <code>UID DAYS</code>", reply_markup=back_button("menu_admin")
    )
    await state.set_state(S.admin_input)
    await cb.answer()


@dp.callback_query(F.data == "adm_ban")
async def cb_adm_ban(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.update_data(admin_action="ban")
    await cb.message.edit_text("🚫 آیدی:", reply_markup=back_button("menu_admin"))
    await state.set_state(S.admin_input)
    await cb.answer()


@dp.message(S.admin_input)
async def on_admin_input(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    data = await state.get_data()
    action = data.get("admin_action")
    await state.clear()
    if action == "ban":
        try:
            uid = int(m.text.strip())
            db.cur.execute("DELETE FROM users WHERE user_id=?", (uid,))
            db.conn.commit()
            await m.answer("✅ حذف شد.", reply_markup=back_button("menu_admin"))
        except Exception as e:
            await m.answer(f"❌ {e}")
        return
    parts = m.text.split()
    if len(parts) != 2:
        await m.answer("❌ فرمت")
        return
    try:
        uid, val = int(parts[0]), int(parts[1])
    except:
        await m.answer("❌ اعداد")
        return
    if action == "give_points":
        db.add_points(uid, val)
        u = db.get_user(uid)
        await m.answer(
            f"✅ {val} → <code>{uid}</code>\n💰 {u['points']}",
            reply_markup=back_button("menu_admin"),
        )
    elif action == "give_prem":
        db.set_premium(uid, days=val)
        await m.answer(
            f"✅ پریمیوم {val} روز → <code>{uid}</code>",
            reply_markup=back_button("menu_admin"),
        )


@dp.message(Command("reply"))
async def cmd_reply(m: Message):
    if not is_admin(m.from_user.id):
        return
    parts = m.text.split(maxsplit=2)
    if len(parts) != 3:
        await m.answer("استفاده: /reply <uid> <متن>")
        return
    try:
        uid = int(parts[1])
    except:
        await m.answer("❌")
        return
    try:
        await bot.send_message(uid, f"📩 <b>پاسخ:</b>\n\n{parts[2]}")
        await m.answer("✅")
    except Exception as e:
        await m.answer(f"❌ {e}")


@dp.message(Command("addpoints"))
async def cmd_addpoints(m: Message):
    if not is_admin(m.from_user.id):
        return
    parts = m.text.split()
    if len(parts) != 3:
        await m.answer("استفاده: /addpoints <uid> <amount>")
        return
    try:
        uid, amt = int(parts[1]), int(parts[2])
    except:
        await m.answer("❌")
        return
    db.add_points(uid, amt)
    u = db.get_user(uid)
    await m.answer(f"✅ {amt} → <code>{uid}</code>\n💰 {u['points']}")


@dp.message(Command("reload_index"))
async def cmd_reload_index(m: Message):
    if not is_admin(m.from_user.id):
        return
    n = await asyncio.to_thread(search_mod.reload_index)
    await m.answer(f"✅ ایندکس دوباره لود شد.\n📊 تعداد: <b>{n}</b>")


@dp.callback_query(F.data == "adm_stats")
async def cb_adm_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    n = await asyncio.to_thread(search_mod.reload_index)
    await cb.message.edit_text(
        f"📊 رکورد: <b>{n}</b>\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=back_button("menu_admin"),
    )
    await cb.answer()


# ============================================================
# کیف پول و KYC
# ============================================================


@dp.callback_query(F.data == "menu_wallet")
async def cb_wallet(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    balance = u.get("wallet_balance") or 0
    charged = u.get("total_charged_toman") or 0

    status_map = {
        "none": "❌ احراز نشده",
        "pending": "⏳ در انتظار بررسی",
        "approved": "✅ احراز شده",
        "rejected": "⚠️ رد شده",
    }

    text = (
        f"💰 <b>کیف پول شما</b>\n\n"
        f"┣ 🪙 موجودی: <b>{balance:,} تومان</b>\n"
        f"┣ 💎 وضعیت: <b>{status_map.get(kyc)}</b>\n"
        f"┗ 💵 شارژ شده امروز: <b>{u.get('daily_charged', 0):,} از 1,000,000 تومان</b>"
    )
    try:
        await cb.message.edit_text(text, reply_markup=wallet_menu(kyc))
    except Exception:
        await cb.message.answer(text, reply_markup=wallet_menu(kyc))
    await cb.answer()


@dp.callback_query(F.data == "wallet_kyc")
async def cb_kyc_start(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    if kyc == "approved":
        await cb.answer("✅ شما قبلاً احراز شده‌اید", show_alert=True)
        return
    if kyc == "pending":
        await cb.answer("⏳ درخواست شما در حال بررسیه", show_alert=True)
        return

    await state.set_state(S.kyc_docs)
    await state.update_data(kyc_docs=[])

    text = (
        "🪪 <b>احراز هویت</b>\n\n"
        "برای احراز، ۳ عکس بفرست:\n\n"
        "1️⃣ عکس <b>کارت ملی</b>\n"
        "2️⃣ عکس <b>کارت بانکی</b>\n"
        "3️⃣ عکس کاغذی که روش نوشته شده:\n"
        "     <i>«این احراز هویت برای پنل شیخ هست»</i>\n\n"
        "📸 عکس‌ها رو یکی‌یکی بفرست."
    )
    try:
        await cb.message.edit_text(text, reply_markup=kyc_cancel_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=kyc_cancel_menu())
    await cb.answer()


@dp.message(S.kyc_docs, F.photo)
async def kyc_got_photo(m: Message, state: FSMContext):
    data = await state.get_data()
    docs = data.get("kyc_docs", [])
    docs.append(m.photo[-1].file_id)
    await state.update_data(kyc_docs=docs)

    labels = ["🪪 کارت ملی", "💳 کارت بانکی", "📝 کاغذ"]
    if len(docs) < 3:
        await m.answer(
            f"✅ {labels[len(docs)-1]} گرفته شد.\n\n📸 عکس بعدی رو بفرست ({len(docs)}/3)"
        )
    else:
        await state.set_state(S.kyc_video)
        await m.answer(
            "✅ هر ۳ عکس گرفته شد.\n\n"
            "🎥 حالا یه <b>ویدیو سلفی</b> بفرست که توش چهره‌ت معلومه، کارت ملی تو دستته و می‌گی:\n\n"
            "<i>«این احراز هویت برای پنل شیخ هست»</i>"
        )


@dp.message(S.kyc_docs)
async def kyc_docs_invalid(m: Message):
    await m.answer("⚠️ لطفاً فقط عکس بفرست.")


@dp.message(S.kyc_video, F.video)
async def kyc_got_video(m: Message, state: FSMContext):
    data = await state.get_data()
    docs = data.get("kyc_docs", [])
    uid = m.from_user.id

    now = int(time.time())
    db.cur.execute(
        """
        INSERT INTO kyc_requests
        (user_id, national_card_file_id, bank_card_file_id, paper_file_id, video_file_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """,
        (uid, docs[0], docs[1], docs[2], m.video.file_id, now),
    )
    db.conn.commit()
    req_id = db.cur.lastrowid

    db.cur.execute("UPDATE users SET kyc_status='pending' WHERE user_id=?", (uid,))
    db.conn.commit()

    admin_id = config.ADMIN_IDS[0]
    u = db.get_user(uid)
    caption = (
        f"🪪 <b>درخواست احراز هویت #{req_id}</b>\n\n"
        f"👤 نام: {u.get('first_name') or '—'}\n"
        f"🆔 آیدی: <code>{uid}</code>\n"
        f"🔗 یوزرنیم: @{m.from_user.username or '—'}\n"
        f"📅 زمان: {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}"
    )
    await bot.send_message(admin_id, caption)
    for d in docs:
        await bot.send_photo(admin_id, d)
    await bot.send_video(
        admin_id,
        m.video.file_id,
        caption=f"🎥 ویدیو سلفی — درخواست #{req_id}",
        reply_markup=admin_kyc_menu(req_id),
    )

    await state.clear()
    await m.answer(
        "✅ درخواست احراز هویتت ثبت شد.\n\n"
        "⏳ منتظر تایید ادمین باش. بعد از تایید بهت خبر می‌دیم."
    )


@dp.message(S.kyc_video)
async def kyc_video_invalid(m: Message):
    await m.answer("⚠️ لطفاً ویدیو بفرست.")


@dp.callback_query(F.data == "wallet_cancel")
async def cb_wallet_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    u = db.get_user(cb.from_user.id)
    kyc = u.get("kyc_status") or "none"
    balance = u.get("wallet_balance") or 0
    status_map = {
        "none": "❌ احراز نشده",
        "pending": "⏳ در انتظار بررسی",
        "approved": "✅ احراز شده",
        "rejected": "⚠️ رد شده",
    }
    text = (
        f"💰 <b>کیف پول شما</b>\n\n"
        f"┣ 🪙 موجودی: <b>{balance:,} تومان</b>\n"
        f"┗ 💎 وضعیت: <b>{status_map.get(kyc)}</b>"
    )
    try:
        await cb.message.edit_text(text, reply_markup=wallet_menu(kyc))
    except Exception:
        await cb.message.answer(text, reply_markup=wallet_menu(kyc))
    await cb.answer("لغو شد")


@dp.callback_query(F.data.startswith("kyc_approve_"))
async def cb_kyc_approve(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔ دسترسی نداری", show_alert=True)
        return
    req_id = int(cb.data.split("_")[-1])
    db.cur.execute("SELECT * FROM kyc_requests WHERE id=?", (req_id,))
    row = db.cur.fetchone()
    if not row:
        await cb.answer("درخواست پیدا نشد", show_alert=True)
        return

    uid = row[1]
    now = int(time.time())
    db.cur.execute(
        "UPDATE kyc_requests SET status='approved', reviewed_at=? WHERE id=?",
        (now, req_id),
    )
    db.cur.execute("UPDATE users SET kyc_status='approved' WHERE user_id=?", (uid,))
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"✅ درخواست #{req_id} تایید شد")
    try:
        await bot.send_message(
            uid,
            "✅ <b>احراز هویت شما تایید شد!</b>\n\nالان می‌تونی با تومن شارژ کنی و خرید انجام بدی. 🎉",
        )
    except Exception:
        pass
    await cb.answer("تایید شد ✅")


@dp.callback_query(F.data.startswith("kyc_reject_"))
async def cb_kyc_reject(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔ دسترسی نداری", show_alert=True)
        return
    req_id = int(cb.data.split("_")[-1])
    db.cur.execute("SELECT * FROM kyc_requests WHERE id=?", (req_id,))
    row = db.cur.fetchone()
    if not row:
        await cb.answer("درخواست پیدا نشد", show_alert=True)
        return

    uid = row[1]
    now = int(time.time())
    db.cur.execute(
        "UPDATE kyc_requests SET status='rejected', reviewed_at=? WHERE id=?",
        (now, req_id),
    )
    db.cur.execute("UPDATE users SET kyc_status='rejected' WHERE user_id=?", (uid,))
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"❌ درخواست #{req_id} رد شد")
    try:
        await bot.send_message(
            uid,
            "❌ <b>احراز هویت شما رد شد.</b>\n\nاگه فکر می‌کنی اشتباهه، با پشتیبانی تماس بگیر.",
        )
    except Exception:
        pass
    await cb.answer("رد شد ❌")


# ============================================================
# شارژ کیف پول با تومن
# ============================================================


@dp.callback_query(F.data == "wallet_charge")
async def cb_wallet_charge(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    if kyc != "approved":
        await cb.answer("❌ برای شارژ با تومن اول باید احراز هویت کنی", show_alert=True)
        return

    from datetime import datetime as _dt

    today = _dt.now().strftime("%Y-%m-%d")
    last_day = u.get("last_charge_date") or ""
    if last_day != today:
        db.cur.execute(
            "UPDATE users SET daily_charged=0, last_charge_date=? WHERE user_id=?",
            (today, cb.from_user.id),
        )
        db.conn.commit()
        daily_charged = 0
    else:
        daily_charged = u.get("daily_charged") or 0

    remaining = 1000000 - daily_charged
    if remaining <= 0:
        await cb.answer("⚠️ به سقف شارژ روزانه رسیدی (۱ میلیون تومان)", show_alert=True)
        return

    text = (
        f"🔋 <b>شارژ کیف پول</b>\n\n"
        f"💵 سقف باقی‌مونده: <b>{remaining:,} تومان</b>\n\n"
        f"مبلغ مورد نظر رو انتخاب کن:"
    )
    try:
        await cb.message.edit_text(text, reply_markup=charge_amounts_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=charge_amounts_menu())
    await cb.answer()


@dp.callback_query(F.data.startswith("charge_amt_"))
async def cb_charge_amount(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    if kyc != "approved":
        await cb.answer("❌ اول احراز هویت کن", show_alert=True)
        return

    amount = int(cb.data.split("_")[-1])
    from datetime import datetime as _dt

    today = _dt.now().strftime("%Y-%m-%d")
    if u.get("last_charge_date") != today:
        db.cur.execute(
            "UPDATE users SET daily_charged=0, last_charge_date=? WHERE user_id=?",
            (today, cb.from_user.id),
        )
        db.conn.commit()
        charged = 0
    else:
        charged = u.get("daily_charged") or 0
    if charged + amount > 1000000:
        await cb.answer("⚠️ این مبلغ از سقف ۱ میلیون رد می‌شه", show_alert=True)
        return

    await state.set_state(S.charge_receipt)
    await state.update_data(charge_amount=amount)

    text = (
        f"💳 <b>پرداخت با کارت به کارت</b>\n\n"
        f"💰 مبلغ: <b>{amount:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n"
        f"<code>6219861809389223</code>\n\n"
        f"✅ بعد از واریز، عکس <b>رسید</b> رو همین‌جا بفرست."
    )
    await cb.message.edit_text(text, reply_markup=kyc_cancel_menu())
    await cb.answer()


@dp.message(S.charge_receipt, F.photo)
async def charge_got_receipt(m: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("charge_amount", 0)
    uid = m.from_user.id
    now = int(time.time())

    db.cur.execute(
        """
        INSERT INTO toman_receipts (user_id, amount, receipt_file_id, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    """,
        (uid, amount, m.photo[-1].file_id, now),
    )
    db.conn.commit()
    rec_id = db.cur.lastrowid

    admin_id = config.ADMIN_IDS[0]
    u = db.get_user(uid)
    caption = (
        f"💳 <b>رسید شارژ #{rec_id}</b>\n\n"
        f"👤 {u.get('first_name') or '—'}\n"
        f"🆔 <code>{uid}</code>\n"
        f"💰 مبلغ: <b>{amount:,} تومان</b>\n"
        f"📅 {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}"
    )
    await bot.send_photo(
        admin_id,
        m.photo[-1].file_id,
        caption=caption,
        reply_markup=admin_receipt_menu(rec_id),
    )

    await state.clear()
    await m.answer("✅ رسید دریافت شد.\n\n" "⏳ منتظر تایید ادمین باش.")


@dp.message(S.charge_receipt)
async def charge_invalid(m: Message):
    await m.answer("⚠️ لطفاً عکس رسید رو بفرست.")


@dp.callback_query(F.data.startswith("rec_approve_"))
async def cb_rec_approve(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔", show_alert=True)
        return
    rec_id = int(cb.data.split("_")[-1])
    db.cur.execute("SELECT * FROM toman_receipts WHERE id=?", (rec_id,))
    row = db.cur.fetchone()
    if not row or row[4] != "pending":
        await cb.answer("قبلاً بررسی شده", show_alert=True)
        return

    uid = row[1]
    amount = row[2]
    now = int(time.time())
    db.cur.execute(
        "UPDATE toman_receipts SET status='approved', reviewed_at=? WHERE id=?",
        (now, rec_id),
    )
    db.cur.execute(
        "UPDATE users SET wallet_balance=wallet_balance+?, total_charged_toman=total_charged_toman+?, daily_charged=daily_charged+?, last_charge_date=? WHERE user_id=?",
        (amount, amount, uid),
    )
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"✅ رسید #{rec_id} تایید و {amount:,} تومان شارژ شد")
    try:
        await bot.send_message(
            uid, f"✅ <b>رسید تایید شد!</b>\n\n💰 {amount:,} تومان به موجودیت اضافه شد."
        )
    except Exception:
        pass
    await cb.answer("✅")


@dp.callback_query(F.data.startswith("rec_reject_"))
async def cb_rec_reject(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔", show_alert=True)
        return
    rec_id = int(cb.data.split("_")[-1])
    db.cur.execute("SELECT * FROM toman_receipts WHERE id=?", (rec_id,))
    row = db.cur.fetchone()
    if not row or row[4] != "pending":
        await cb.answer("قبلاً بررسی شده", show_alert=True)
        return

    uid = row[1]
    now = int(time.time())
    db.cur.execute(
        "UPDATE toman_receipts SET status='rejected', reviewed_at=? WHERE id=?",
        (now, rec_id),
    )
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"❌ رسید #{rec_id} رد شد")
    try:
        await bot.send_message(
            uid,
            "❌ <b>رسیدت رد شد.</b>\n\nاگه فکر می‌کنی اشتباهه، با پشتیبانی تماس بگیر.",
        )
    except Exception:
        pass
    await cb.answer("❌")


@dp.callback_query(F.data == "buy_toman")
async def cb_buy_toman(cb: CallbackQuery):
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    if kyc != "approved":
        await cb.answer("❌ برای خرید با تومن اول احراز هویت کن", show_alert=True)
        return
    balance = u.get("wallet_balance") or 0
    await cb.message.edit_text(
        f"💵 <b>خرید امتیاز با تومن</b>\n\n"
        f"💰 موجودی شما: <b>{balance:,} تومان</b>\n\n"
        f"هنوز پکیج‌های تومن تعریف نشده.\n"
        f"برای شارژ موجودی از منوی کیف پول استفاده کن.",
        reply_markup=back_button("menu_wallet"),
    )
    await cb.answer()


@dp.callback_query(F.data == "buy_points")
async def cb_buy_points(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    u = db.get_user(uid)
    kyc = u.get("kyc_status") or "none"
    kyc_ok = kyc == "approved"
    text = "🛒 <b>خرید امتیاز</b>\n\n" "روش خرید رو انتخاب کن:\n\n"
    if not kyc_ok:
        text += "⚠️ برای خرید با تومن باید احراز هویت کنی.\n"
    try:
        await cb.message.edit_text(text, reply_markup=buy_points_menu(kyc_ok))
    except Exception:
        await cb.message.answer(text, reply_markup=buy_points_menu(kyc_ok))
    await cb.answer()


# ============================================================
# شارژ کیف پول با ارز دیجیتال
# ============================================================


@dp.callback_query(F.data == "wallet_charge_crypto")
async def cb_wallet_charge_crypto(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "₿ <b>شارژ کیف پول با ارز دیجیتال</b>\n\n"
        "مبلغ مورد نظر رو انتخاب کن:\n"
        "<i>(پرداخت با TRX)</i>"
    )
    try:
        await cb.message.edit_text(text, reply_markup=crypto_charge_amounts_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=crypto_charge_amounts_menu())
    await cb.answer()


@dp.callback_query(F.data.startswith("ccharge_"))
async def cb_crypto_charge_pick(cb: CallbackQuery):
    toman = int(cb.data.split("_")[-1])
    # نرخ تبدیل: هر 50,000 تومان ≈ 0.3 TRX (همون نرخ فعلی سیستم)
    trx = round(toman / 50000 * 0.3, 4)
    uid = cb.from_user.id

    # ساخت payment با kind wallet_charge
    pid = db.new_payment(uid, f"wallet_charge_{toman}", trx)

    wallet = config.TRON_WALLET
    url = f"https://tronscan.org/#/transfer?to={wallet}&amount={trx}&token=TRX"
    txt = (
        f"💳 <b>درگاه پرداخت — شارژ کیف پول</b>\n\n"
        f"🔹 مبلغ: <b>{toman:,} تومان</b>\n"
        f"🔹 معادل: <b>{trx} TRX</b>\n\n"
        f"📍 ولت:\n<code>{wallet}</code>\n\n"
        f"📝 ممو: <code>CHG{pid}</code>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 باز کردن کیف پول", url=url, style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ پرداخت کردم",
                    callback_data=f"paycheck_{pid}",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="menu_wallet", style="danger"
                )
            ],
        ]
    )
    await cb.message.edit_text(txt, reply_markup=kb, disable_web_page_preview=True)
    await cb.answer()


# ============================================================
# مبلغ دلخواه (تومن و کریپتو)
# ============================================================


@dp.callback_query(F.data == "charge_custom")
async def cb_charge_custom(cb: CallbackQuery, state: FSMContext):
    await state.set_state(S.charge_custom_toman)
    await cb.message.edit_text(
        "✏️ <b>مبلغ دلخواه</b>\n\n"
        "مبلغ مورد نظرت رو به <b>تومن</b> بنویس.\n\n"
        "📌 مثال: <code>75000</code>\n"
        "📌 حداقل: ۱۰,۰۰۰ تومان\n"
        "📌 حداکثر: ۱,۰۰۰,۰۰۰ تومان\n\n"
        "❌ برای لغو /cancel بزن.",
        reply_markup=kyc_cancel_menu(),
    )
    await cb.answer()


@dp.message(S.charge_custom_toman)
async def got_custom_toman(m: Message, state: FSMContext):
    uid = m.from_user.id
    if m.text == "/cancel":
        await state.clear()
        await m.answer("❌ لغو شد.", reply_markup=back_button("menu_wallet"))
        return
    try:
        amount = int(m.text.strip().replace(",", "").replace("٬", ""))
    except Exception:
        await m.answer("❌ فقط عدد بنویس. مثال: <code>75000</code>")
        return

    if amount < 10000 or amount > 1000000:
        await m.answer("❌ مبلغ باید بین ۱۰,۰۰۰ تا ۱,۰۰۰,۰۰۰ تومان باشه.")
        return

    u = db.get_user(uid)
    if (u.get("kyc_status") or "none") != "approved":
        await state.clear()
        await m.answer("❌ اول احراز هویت کن.", reply_markup=back_button("menu_wallet"))
        return

    from datetime import datetime as _dt

    today = _dt.now().strftime("%Y-%m-%d")
    if u.get("last_charge_date") != today:
        db.cur.execute(
            "UPDATE users SET daily_charged=0, last_charge_date=? WHERE user_id=?",
            (today, cb.from_user.id),
        )
        db.conn.commit()
        charged = 0
    else:
        charged = u.get("daily_charged") or 0
    if charged + amount > 1000000:
        remaining = 1000000 - charged
        await m.answer(f"❌ سقف باقی‌مونده: {remaining:,} تومان. کمتر وارد کن.")
        return

    await state.update_data(charge_amount=amount)
    await state.set_state(S.charge_receipt)
    text = (
        f"💳 <b>پرداخت با کارت به کارت</b>\n\n"
        f"💰 مبلغ: <b>{amount:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n<code>6219861809389223</code>\n\n"
        f"✅ بعد از واریز، عکس <b>رسید</b> رو بفرست."
    )
    await m.answer(text, reply_markup=kyc_cancel_menu())


@dp.callback_query(F.data == "ccharge_custom")
async def cb_ccharge_custom(cb: CallbackQuery, state: FSMContext):
    await state.set_state(S.charge_custom_crypto)
    await cb.message.edit_text(
        "✏️ <b>مبلغ دلخواه — کریپتو</b>\n\n"
        "مبلغ مورد نظرت رو به <b>تومن</b> بنویس تا معادل TRX محاسبه شه.\n\n"
        "📌 مثال: <code>75000</code>\n"
        "📌 حداقل: ۱۰,۰۰۰ تومان\n\n"
        "❌ برای لغو /cancel بزن.",
        reply_markup=kyc_cancel_menu(),
    )
    await cb.answer()


@dp.message(S.charge_custom_crypto)
async def got_custom_crypto(m: Message, state: FSMContext):
    if m.text == "/cancel":
        await state.clear()
        await m.answer("❌ لغو شد.", reply_markup=back_button("menu_wallet"))
        return
    try:
        toman = int(m.text.strip().replace(",", "").replace("٬", ""))
    except Exception:
        await m.answer("❌ فقط عدد بنویس. مثال: <code>75000</code>")
        return

    if toman < 10000:
        await m.answer("❌ حداقل ۱۰,۰۰۰ تومان.")
        return

    trx = round(toman / 50000 * 0.3, 4)
    uid = m.from_user.id
    pid = db.new_payment(uid, f"wallet_charge_{toman}", trx)

    wallet = config.TRON_WALLET
    url = f"https://tronscan.org/#/transfer?to={wallet}&amount={trx}&token=TRX"
    txt = (
        f"💳 <b>درگاه پرداخت — شارژ کیف پول</b>\n\n"
        f"🔹 مبلغ: <b>{toman:,} تومان</b>\n"
        f"🔹 معادل: <b>{trx} TRX</b>\n\n"
        f"📍 ولت:\n<code>{wallet}</code>\n\n"
        f"📝 ممو: <code>CHG{pid}</code>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 باز کردن کیف پول", url=url, style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ پرداخت کردم",
                    callback_data=f"paycheck_{pid}",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="menu_wallet", style="danger"
                )
            ],
        ]
    )
    await state.clear()
    await m.answer(txt, reply_markup=kb, disable_web_page_preview=True)


# ============================================================
# فروشگاه ریموت / VPN / اسکن کارت
# ============================================================


@dp.message(Command("remote"))
async def cmd_remote_main(m: Message, state: FSMContext):
    await state.clear()
    text = (
        "🖥 <b>فروشگاه SHEIKH</b>\n\n"
        "🛒 خرید سرویس\n"
        "🌐 VPN پرسرعت\n"
        "💳 اسکن کارت\n"
        "📦 مدیریت اشتراک\n"
        "👤 حساب کاربری\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:"
    )
    await m.answer(text, reply_markup=remote_main_menu())


@dp.callback_query(F.data == "menu_remote")
async def cb_remote_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🖥 <b>فروشگاه SHEIKH</b>\n\n"
        "🛒 خرید سرویس\n"
        "🌐 VPN پرسرعت\n"
        "💳 اسکن کارت\n"
        "📦 مدیریت اشتراک\n"
        "👤 حساب کاربری\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:"
    )
    try:
        await cb.message.edit_text(text, reply_markup=remote_main_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=remote_main_menu())
    await cb.answer()


@dp.callback_query(F.data == "remote_shop")
async def cb_remote_shop(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id

    # تعداد سبد
    db.cur.execute("SELECT COUNT(*) FROM carts WHERE user_id=?", (uid,))
    cart_count = db.cur.fetchone()[0]

    text = (
        "🛒 <b>خرید سرویس</b>\n\n"
        "لطفاً نوع عملیات را مشخص کنید:\n\n"
        "🆕 <b>خرید سرویس جدید</b> — دریافت پورت/درگاه با کد جدید\n"
        "🔄 <b>تمدید اشتراک موجود</b> — افزودن زمان به اشتراک فعلی شما\n"
    )
    if cart_count:
        text += f"\n📦 {cart_count} مورد در سبد خرید دارید."

    try:
        await cb.message.edit_text(
            text, reply_markup=remote_shop_menu(cart_count > 0, cart_count)
        )
    except Exception:
        await cb.message.answer(
            text, reply_markup=remote_shop_menu(cart_count > 0, cart_count)
        )
    await cb.answer()


@dp.callback_query(F.data == "remote_cat_remote")
async def cb_remote_cat_remote(cb: CallbackQuery):
    text = (
        "🖥 <b>پکیج‌های ریموت اندروید</b>\n\n"
        "🎯 <b>سه پلن:</b>\n\n"
        "🥉 <b>نوب</b> — ۱۵ روزه — <b>$50</b>\n"
        "🥈 <b>پایه</b> — ۳۰ روزه — <b>$80</b>\n"
        "🥇 <b>حرفه‌ای</b> — ۹۰ روزه — <b>$200</b>\n\n"
        "🎁 تنها ریموت ایرانی با تست رایگان ۵ دقیقه‌ای\n\n"
        "👇 پکیج مورد نظر رو انتخاب کن:"
    )
    try:
        await cb.message.edit_text(text, reply_markup=remote_cat_menu("remote"))
    except Exception:
        await cb.message.answer(text, reply_markup=remote_cat_menu("remote"))
    await cb.answer()


@dp.callback_query(F.data == "remote_cat_vpn")
async def cb_remote_cat_vpn(cb: CallbackQuery):
    text = "🌐 <b>پکیج‌های VPN</b>\n\n"
    for p in __import__("modules.keyboards", fromlist=["VPN_PACKAGES"]).VPN_PACKAGES:
        text += f"• {p['name']} — <b>${p['price_usdt']}</b>\n"
    text += "\n👇 یکی رو انتخاب کن:"
    try:
        await cb.message.edit_text(text, reply_markup=remote_cat_menu("vpn"))
    except Exception:
        await cb.message.answer(text, reply_markup=remote_cat_menu("vpn"))
    await cb.answer()


@dp.callback_query(F.data == "remote_cat_card")
async def cb_remote_cat_card(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "💳 <b>پکیج‌های اسکن کارت</b>\n\n"
    for p in __import__("modules.keyboards", fromlist=["CARD_PACKAGES"]).CARD_PACKAGES:
        text += f"• {p['name']} — <b>${p['price_usdt']}</b>\n"
    text += "\n👇 یکی رو انتخاب کن:"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [
                    InlineKeyboardButton(
                        text=f"{p['name']} — ${p['price_usdt']}",
                        callback_data=f"remote_pick_{p['id']}",
                        style="success",
                    )
                ]
                for p in __import__(
                    "modules.keyboards", fromlist=["CARD_PACKAGES"]
                ).CARD_PACKAGES
            ],
            [
                InlineKeyboardButton(
                    text="🔍 انجام اسکن", callback_data="iva_do_scan", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="remote_shop", style="danger"
                )
            ],
        ]
    )
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "remote_renew")
async def cb_remote_renew(cb: CallbackQuery):
    await cb.answer("🔄 تمدید اشتراک به‌زودی اضافه می‌شه", show_alert=True)


@dp.callback_query(F.data.startswith("remote_pick_"))
async def cb_remote_pick(cb: CallbackQuery):
    pkg_id = cb.data.replace("remote_pick_", "")
    pkg = ALL_PACKAGES.get(pkg_id)
    if not pkg:
        await cb.answer("❌ پکیج پیدا نشد", show_alert=True)
        return

    uid = cb.from_user.id
    now = int(time.time())

    db.cur.execute(
        """
        INSERT INTO carts (user_id, plan_id, plan_name, plan_days, plan_price_usdt, added_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (uid, pkg["id"], pkg["name"], pkg.get("days", 0), pkg["price_usdt"], now),
    )
    db.conn.commit()

    db.cur.execute("SELECT COUNT(*) FROM carts WHERE user_id=?", (uid,))
    cart_count = db.cur.fetchone()[0]

    await cb.answer(f"✅ {pkg['name']} به سبد اضافه شد", show_alert=False)

    text = (
        f"✅ <b>{pkg['name']}</b> به سبد خرید اضافه شد.\n\n"
        f"📦 تعداد موارد در سبد: <b>{cart_count}</b>"
    )
    try:
        await cb.message.edit_text(
            text, reply_markup=remote_shop_menu(True, cart_count)
        )
    except Exception:
        await cb.message.answer(text, reply_markup=remote_shop_menu(True, cart_count))


@dp.callback_query(F.data == "remote_cart_view")
async def cb_remote_cart_view(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute(
        "SELECT id, plan_id, plan_name, plan_days, plan_price_usdt FROM carts WHERE user_id=? ORDER BY id",
        (uid,),
    )
    rows = db.cur.fetchall()
    items = [
        {
            "id": r[0],
            "plan_id": r[1],
            "plan_name": r[2],
            "plan_days": r[3],
            "plan_price_usdt": r[4],
        }
        for r in rows
    ]

    text = remote_shop.format_cart_table(items)

    try:
        await cb.message.edit_text(text, reply_markup=remote_cart_menu(items))
    except Exception:
        await cb.message.answer(text, reply_markup=remote_cart_menu(items))
    await cb.answer()


@dp.callback_query(F.data.startswith("cart_remove_"))
async def cb_cart_remove(cb: CallbackQuery):
    try:
        cart_id = int(cb.data.replace("cart_remove_", ""))
    except Exception:
        await cb.answer("خطا", show_alert=True)
        return

    uid = cb.from_user.id
    db.cur.execute("DELETE FROM carts WHERE id=? AND user_id=?", (cart_id, uid))
    db.conn.commit()
    await cb.answer("❌ حذف شد")

    # رفرش سبد
    await cb_remote_cart_view(cb)


@dp.callback_query(F.data == "cart_empty")
async def cb_cart_empty(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute("DELETE FROM carts WHERE user_id=?", (uid,))
    db.conn.commit()
    await cb.answer("🗑 سبد خالی شد")
    await cb_remote_cart_view(cb)


@dp.callback_query(F.data == "cart_checkout")
async def cb_cart_checkout(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute(
        "SELECT id, plan_id, plan_name, plan_days, plan_price_usdt FROM carts WHERE user_id=? ORDER BY id",
        (uid,),
    )
    rows = db.cur.fetchall()
    if not rows:
        await cb.answer("🛒 سبد خالیه", show_alert=True)
        return

    items = [
        {
            "id": r[0],
            "plan_id": r[1],
            "plan_name": r[2],
            "plan_days": r[3],
            "plan_price_usdt": r[4],
        }
        for r in rows
    ]
    total_usdt = remote_shop.cart_total_usdt(items)

    # محاسبه TRX لحظه‌ای
    total_trx = await remote_shop.usdt_to_trx(total_usdt)

    # ساخت سفارش
    order_no = remote_shop.make_order_no()
    now = int(time.time())
    expires_at = now + 24 * 3600

    import json as _json

    items_json = _json.dumps(items, ensure_ascii=False)

    db.cur.execute(
        """
        INSERT INTO remote_orders
        (user_id, order_no, items_json, total_usdt, total_trx, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    """,
        (uid, order_no, items_json, total_usdt, total_trx, now, expires_at),
    )
    db.conn.commit()
    order_id = db.cur.lastrowid

    # پاک کردن سبد
    db.cur.execute("DELETE FROM carts WHERE user_id=?", (uid,))
    db.conn.commit()

    # نمایش صفحه پرداخت
    wallet = config.TRON_WALLET
    expires_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(expires_at))

    pay_text = (
        f"📌 <b>لطفاً پیش از واریز، تمامی اطلاعات را با دقت بررسی کنید.</b>\n\n"
        f"💸 <b>مبلغ پرداختی:</b> <code>{total_trx}</code> TRX\n"
        f"💰 معادل: <b>${total_usdt}</b>\n\n"
        f"🏦 <b>آدرس کیف پول مقصد:</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"💱 <b>ارز قابل قبول: فقط TRX (ترون)</b>\n\n"
        f"🆔 <b>شماره سفارش:</b> <code>{order_no}</code>\n"
        f"⏰ <b>مهلت پرداخت:</b> ۲۴ ساعت\n"
        f"📅 <b>تا:</b> {expires_str}\n\n"
        f"🚫 <b>مهم:</b> فقط ارز TRX پذیرفته می‌شود. سایر رمزارزها برگشت‌ناپذیر خواهند بود.\n\n"
        f"⚠️ مسئولیت واریز اشتباه بر عهده شماست؛ لطفاً با دقت واریز را انجام دهید.\n\n"
        f"🛡 تمامی مراحل به‌صورت خودکار انجام می‌شوند."
    )

    try:
        await cb.message.edit_text(
            pay_text,
            reply_markup=remote_payment_menu(order_id, wallet),
            disable_web_page_preview=True,
        )
    except Exception:
        await cb.message.answer(
            pay_text,
            reply_markup=remote_payment_menu(order_id, wallet),
            disable_web_page_preview=True,
        )
    await cb.answer()


@dp.callback_query(F.data.startswith("copy_wallet_"))
async def cb_copy_wallet(cb: CallbackQuery):
    wallet = config.TRON_WALLET
    await cb.answer(f"📍 {wallet}\n\n(برای کپی، دکمه رو نگه دار)", show_alert=True)


@dp.callback_query(F.data.startswith("remote_paid_"))
async def cb_remote_paid(cb: CallbackQuery):
    try:
        order_id = int(cb.data.replace("remote_paid_", ""))
    except Exception:
        await cb.answer("خطا", show_alert=True)
        return

    uid = cb.from_user.id
    db.cur.execute(
        "SELECT * FROM remote_orders WHERE id=? AND user_id=?", (order_id, uid)
    )
    row = db.cur.fetchone()
    if not row:
        await cb.answer("سفارش پیدا نشد", show_alert=True)
        return

    order = dict(zip([d[0] for d in db.cur.description], row))
    if order["status"] != "pending":
        await cb.answer("این سفارش قبلاً بررسی شده", show_alert=True)
        return

    admin_id = config.ADMIN_IDS[0]
    u = db.get_user(uid)

    import json as _json

    try:
        items = _json.loads(order["items_json"])
        items_str = "\n".join(
            [f"• {it['plan_name']} — ${it['plan_price_usdt']}" for it in items]
        )
    except Exception:
        items_str = order["items_json"]

    caption = (
        f"🛒 <b>سفارش جدید #{order['order_no']}</b>\n\n"
        f"👤 {u.get('first_name') or '—'}\n"
        f"🆔 <code>{uid}</code>\n"
        f"🔗 @{cb.from_user.username or '—'}\n\n"
        f"📦 <b>اقلام:</b>\n{items_str}\n\n"
        f"💰 مبلغ: <b>${order['total_usdt']}</b>\n"
        f"💸 معادل: <b>{order['total_trx']} TRX</b>\n\n"
        f"🔗 برای بررسی: هش تراکنش رو کاربر باید بفرسته\n"
        f"📅 {time.strftime('%Y-%m-%d %H:%M', time.localtime(order['created_at']))}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تحویل شد",
                    callback_data=f"remote_deliver_{order_id}",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو سفارش",
                    callback_data=f"remote_cancel_{order_id}",
                    style="danger",
                )
            ],
        ]
    )
    await bot.send_message(admin_id, caption, reply_markup=kb)

    await cb.message.edit_text(
        "✅ <b>درخواست پرداخت شما ثبت شد!</b>\n\n"
        "⏳ منتظر تایید ادمین باش.\n"
        "بعد از تایید، سفارش شما فعال می‌شه و بهت اطلاع می‌دیم.",
        reply_markup=back_button("menu_remote"),
    )
    await cb.answer("✅ ثبت شد")


# ==================== تایید ادمین ====================


@dp.callback_query(F.data.startswith("remote_deliver_"))
async def cb_remote_deliver(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔", show_alert=True)
        return
    try:
        order_id = int(cb.data.replace("remote_deliver_", ""))
    except Exception:
        return

    db.cur.execute("SELECT * FROM remote_orders WHERE id=?", (order_id,))
    row = db.cur.fetchone()
    if not row:
        await cb.answer("پیدا نشد", show_alert=True)
        return
    order = dict(zip([d[0] for d in db.cur.description], row))
    uid = order["user_id"]

    now = int(time.time())
    db.cur.execute(
        "UPDATE remote_orders SET status='delivered', delivered_at=?, paid_at=? WHERE id=?",
        (now, now, order_id),
    )
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"✅ سفارش #{order['order_no']} تحویل شد")

    try:
        await bot.send_message(
            uid,
            f"🎉 <b>سفارش شما تحویل شد!</b>\n\n"
            f"🆔 سفارش: <code>{order['order_no']}</code>\n\n"
            f"جزئیات تحویل به‌زودی ارسال می‌شه.",
        )
    except Exception:
        pass
    await cb.answer("✅")


@dp.callback_query(F.data.startswith("remote_cancel_"))
async def cb_remote_cancel(cb: CallbackQuery):
    if cb.from_user.id not in config.ADMIN_IDS:
        await cb.answer("⛔", show_alert=True)
        return
    try:
        order_id = int(cb.data.replace("remote_cancel_", ""))
    except Exception:
        return

    db.cur.execute("SELECT * FROM remote_orders WHERE id=?", (order_id,))
    row = db.cur.fetchone()
    if not row:
        await cb.answer("پیدا نشد", show_alert=True)
        return
    order = dict(zip([d[0] for d in db.cur.description], row))
    uid = order["user_id"]

    db.cur.execute(
        "UPDATE remote_orders SET status='cancelled' WHERE id=?", (order_id,)
    )
    db.conn.commit()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.reply(f"❌ سفارش #{order['order_no']} لغو شد")

    try:
        await bot.send_message(
            uid,
            f"❌ سفارش <code>{order['order_no']}</code> لغو شد.\n\nبرای اطلاعات بیشتر با پشتیبانی تماس بگیر.",
        )
    except Exception:
        pass
    await cb.answer("❌")


# ==================== حساب من ====================


@dp.callback_query(F.data == "remote_my_account")
async def cb_remote_my_account(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute("SELECT balance_usdt FROM user_balance WHERE user_id=?", (uid,))
    r = db.cur.fetchone()
    balance = r[0] if r else 0.0

    text = f"👤 <b>حساب من</b>\n\n" f"💰 موجودی: <b>${balance}</b>\n"
    try:
        await cb.message.edit_text(text, reply_markup=remote_my_account_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=remote_my_account_menu())
    await cb.answer()


@dp.callback_query(F.data == "remote_charge")
async def cb_remote_charge(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "💰 <b>شارژ حساب</b>\n\nمبلغ مورد نظر رو انتخاب کن:"
    try:
        await cb.message.edit_text(text, reply_markup=remote_charge_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=remote_charge_menu())
    await cb.answer()


@dp.callback_query(F.data.startswith("rcharge_"))
async def cb_rcharge_pick(cb: CallbackQuery):
    uid = cb.from_user.id
    if cb.data == "rcharge_custom":
        await cb.answer("مبلغ دلخواه: به‌زودی", show_alert=True)
        return

    try:
        amount = float(cb.data.replace("rcharge_", ""))
    except Exception:
        await cb.answer("خطا", show_alert=True)
        return

    trx_amount = await remote_shop.usdt_to_trx(amount)
    wallet = config.TRON_WALLET

    text = (
        f"💳 <b>شارژ حساب</b>\n\n"
        f"💰 مبلغ: <b>${amount}</b>\n"
        f"💸 معادل: <b>{trx_amount} TRX</b>\n\n"
        f"🏦 آدرس ولت:\n<code>{wallet}</code>\n\n"
        f"✅ بعد از واریز، رسید/هش رو به پشتیبانی بفرست."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 کپی آدرس", callback_data="copy_wallet_0", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✉️ ارسال رسید به پشتیبانی",
                    url="https://t.me/PV_GaBrieel",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="remote_my_account", style="danger"
                )
            ],
        ]
    )
    try:
        await cb.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        await cb.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await cb.answer()


@dp.callback_query(F.data == "remote_history")
async def cb_remote_history(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute(
        "SELECT amount_usdt, type, status, created_at FROM balance_transactions WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (uid,),
    )
    rows = db.cur.fetchall()
    if not rows:
        text = "📜 <b>تاریخچه</b>\n\nهنوز تراکنشی نداری."
    else:
        text = "📜 <b>تاریخچه تراکنش‌ها</b>\n\n"
        for r in rows:
            text += f"• {r[1]} — ${r[0]} — {r[2]} — {time.strftime('%m/%d', time.localtime(r[3]))}\n"
    try:
        await cb.message.edit_text(text, reply_markup=back_button("remote_my_account"))
    except Exception:
        await cb.message.answer(text, reply_markup=back_button("remote_my_account"))
    await cb.answer()


@dp.callback_query(F.data == "remote_my_subs")
async def cb_remote_my_subs(cb: CallbackQuery):
    uid = cb.from_user.id
    db.cur.execute(
        "SELECT order_no, items_json, status, created_at FROM remote_orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (uid,),
    )
    rows = db.cur.fetchall()
    if not rows:
        text = "📦 <b>اشتراک‌های من</b>\n\nهنوز اشتراکی نداری."
    else:
        text = "📦 <b>اشتراک‌های من</b>\n\n"
        for r in rows:
            status_map = {
                "pending": "⏳ در انتظار",
                "delivered": "✅ فعال",
                "cancelled": "❌ لغو",
            }
            text += f"🆔 <code>{r[0]}</code> — {status_map.get(r[2], r[2])}\n"
    try:
        await cb.message.edit_text(text, reply_markup=remote_my_subs_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=remote_my_subs_menu())
    await cb.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


# ============================================================
# ماشین‌حساب درصدی (گروه + پیوی)
# ============================================================

# تبدیل اعداد فارسی به انگلیسی
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _fa_to_en(text: str) -> str:
    return text.translate(_FA_DIGITS)


# regex برای تشخیص الگو
import re as _re

# واحدهای عددی
_UNITS = {
    "k": 1_000,
    "هزار": 1_000,
    "ه": 1_000,
    "m": 1_000_000,
    "mil": 1_000_000,
    "million": 1_000_000,
    "میل": 1_000_000,
    "ملیون": 1_000_000,
    "میلیون": 1_000_000,
    "b": 1_000_000_000,
    "bil": 1_000_000_000,
    "billion": 1_000_000_000,
    "میلیارد": 1_000_000_000,
}

_PERCENT_WORDS = ["%", "درصد", "percent", "percentage"]


def _parse_amount(text: str):
    """پارس عدد — خروجی: (مقدار، واحد) یا None"""
    # اعداد فارسی به انگلیسی
    text = _fa_to_en(text).strip().lower()
    # حذف جداکننده‌ها
    text = text.replace(",", "").replace("٬", "").replace(".", "")

    # regex: عدد + واحد اختیاری (چسبیده یا جدا)
    m = _re.match(
        r"^([0-9]+(?:\.[0-9]+)?)\s*(k|m|b|هزار|ه|میل|ملیون|میلیون|میلیارد|mil|million|billion|bil)?$",
        text,
    )
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or ""
    mult = _UNITS.get(unit, 1)
    return int(num * mult), unit


def _parse_number_only(text: str):
    """فقط عدد، بدون واحد"""
    text = _fa_to_en(text).strip().lower()
    text = text.replace(",", "").replace("٬", "").replace(".", "")
    m = _re.match(r"^([0-9]+(?:\.[0-9]+)?)$", text)
    if not m:
        return None
    return float(m.group(1))


def _parse_percent(text: str):
    """پارس درصد — خروجی: float یا None"""
    text = _fa_to_en(text).strip().lower()
    # حالت ۱: عدد+% یا عدد+درصد چسبیده
    for w in _PERCENT_WORDS:
        if text.endswith(w) and len(text) > len(w):
            num_part = text[: -len(w)].strip()
            try:
                return float(num_part)
            except Exception:
                pass
    # حالت ۲: فقط علامت درصد بدون عدد
    return None


def _format_num(n: int) -> str:
    """عدد با کاما"""
    return f"{n:,}"


def _is_percent_pattern(text: str):
    """چک می‌کنه آیا متن الگوی «عدد + درصد» رو داره"""
    text = _fa_to_en(text).strip()
    parts = text.split()
    if len(parts) < 2:
        return None

    # ترکیب توکن‌های مجاور: ["10", "میل", "40", "درصد"] → ["10 میل", "40 درصد"]
    combined = []
    i = 0
    while i < len(parts):
        # اگه توکن فعلی عدد خالص و بعدی واحد باشه
        if (
            _parse_number_only(parts[i]) is not None
            and i + 1 < len(parts)
            and parts[i + 1] in _UNITS
        ):
            combined.append(parts[i] + " " + parts[i + 1])
            i += 2
        # اگه توکن فعلی عدد خالص و بعدی کلمه درصد باشه
        elif (
            _parse_number_only(parts[i]) is not None
            and i + 1 < len(parts)
            and parts[i + 1] in _PERCENT_WORDS
        ):
            combined.append(parts[i] + parts[i + 1])
            i += 2
        else:
            combined.append(parts[i])
            i += 1

    # الان combined شامل چیزایی مثل ["10 میل", "40درصد"] یا ["10000000", "40%"] هست
    if len(combined) < 2:
        return None

    # سعی کن مقدار و درصد رو پیدا کنی
    for i in range(len(combined)):
        for j in range(len(combined)):
            if i == j:
                continue
            amt = _parse_amount(combined[i])
            pct = _parse_percent(combined[j])
            if amt and pct is not None and pct > 0 and pct <= 100:
                return (amt[0], pct)
    return None


@dp.message(F.chat.type == "private", F.text.regexp(r"https?://"))
async def on_url_download(m: Message, state: FSMContext):
    logging.info(f"🔗 URL detected from user {m.from_user.id}: {(m.text or '')[:80]}")

    # اگه توی FSM هست، رد کن
    cur = await state.get_state()
    logging.info(f"🔗 FSM state: {cur}")
    if cur is not None:
        logging.info("🔗 in FSM, skipping")
        return

    # چک تایید
    uid = m.from_user.id
    is_verified = await is_user_verified(m, uid)
    logging.info(f"🔗 verified: {is_verified}")
    if not is_verified:
        return

    logging.info("🔗 proceeding to download...")

    # استخراج URL
    urls = downloader.extract_urls(m.text or "")
    if not urls:
        return

    url = urls[0]
    if not downloader.is_supported_url(url):
        return

    # پوشه‌ی کاربر
    user_dir = os.path.join(DOWNLOAD_DIR, str(uid))
    os.makedirs(user_dir, exist_ok=True)

    # پاک کردن پوشه‌ی قبلی
    downloader.cleanup_dir(user_dir)
    os.makedirs(user_dir, exist_ok=True)

    wait = await m.answer("⏳ در حال دانلود...\nلطفاً صبر کن (ممکنه ۳۰ ثانیه طول بکشه)")

    try:
        result = await downloader.download(url, user_dir, max_duration=600)
    except Exception as e:
        logging.error(f"dl err: {e}")
        try:
            await wait.edit_text("❌ خطا در دانلود")
        except Exception:
            pass
        return

    if not result.success:
        try:
            await wait.edit_text(f"❌ {result.error}")
        except Exception:
            pass
        # پاکسازی
        downloader.cleanup_dir(user_dir)
        return

    # ارسال فایل
    try:
        await wait.edit_text("📤 در حال ارسال فایل...")
    except Exception:
        pass

    file_size_mb = result.file_size / (1024 * 1024)
    size_str = f"{file_size_mb:.1f} MB"
    title = (result.title or "Video")[:100]

    try:
        # استفاده از FSInputFile
        input_file = FSInputFile(
            result.file_path, filename=os.path.basename(result.file_path)
        )

        if result.is_video:
            await m.answer_video(
                video=input_file,
                caption=f"✅ <b>{title}</b>\n\n📦 حجم: {size_str}",
                parse_mode="HTML",
                supports_streaming=True,
            )
        else:
            await m.answer_document(
                document=input_file,
                caption=f"✅ <b>{title}</b>\n\n📦 حجم: {size_str}",
                parse_mode="HTML",
            )
    except Exception as e:
        logging.error(f"send err: {e}")
        try:
            await wait.edit_text(f"❌ خطا در ارسال: {e}")
        except Exception:
            pass
        try:
            await wait.edit_text("❌ خطا در ارسال فایل")
        except Exception:
            pass
    finally:
        # پاک کردن بعد از ارسال
        downloader.cleanup_dir(user_dir)
        try:
            await wait.delete()
        except Exception:
            pass


def _is_percent_calc(text: str) -> bool:
    if not text:
        return False
    if len(text) > 100:
        return False
    if text.startswith("/"):
        return False
    return _is_percent_pattern(text) is not None


@dp.message(F.text.func(_is_percent_calc))
async def on_percent_calc(m: Message):
    # فقط متن‌های ساده (نه دستور، نه فوروارد)
    if not m.text or m.text.startswith("/"):
        return
    # محدودیت طول متن (که کل پیام‌های طولانی رو نگیره)
    if len(m.text) > 100:
        return

    result = _is_percent_pattern(m.text)
    if not result:
        return

    amount, percent = result

    # محاسبه نتیجه
    total = amount
    result_amount = int(total * percent / 100)

    # تبدیل به دلار و ترون
    toman_result = result_amount  # تومن
    usd_result = round(toman_result / config.USD_TO_TOMAN, 2)

    # TRX لحظه‌ای
    try:
        trx_result = await remote_shop.usdt_to_trx(usd_result)
    except Exception:
        trx_result = 0

    # ساخت متن خروجی
    text = (
        f"› 😀 <b>معامله شما به شرح زیر میباشد:</b>\n\n"
        f"› 💰 <b>تمام مبلغ:</b> <code>{_format_num(total)}</code>\n"
        f"› 📊 <b>درصد:</b> <code>{percent}%</code>\n\n"
        f"› 💳 <b>اطلاعات پرداختی:</b>\n\n"
        f"› 💎 <b>مبلغ معامله به ترون:</b> <code>{trx_result}</code>\n"
        f"› 💵 <b>مبلغ معامله به دلار:</b> <code>{_format_num(int(usd_result))}</code>\n"
        f"› 💰 <b>مبلغ معامله به تومان:</b> <code>{_format_num(toman_result)}</code>\n\n"
        f"› <b>SHEIKH</b>"
    )

    try:
        await m.reply(text)
    except Exception as e:
        logging.error(f"percent calc err: {e}")


# ============================================================
# قیمت ارزها و تبدیل
# ============================================================

import time as _time_usd

# ═══════════════════════════════════════════════
# گرفتن نرخ لحظه‌ای دلار از TGJU
# ═══════════════════════════════════════════════
import aiohttp as _aiohttp_usd

_USD_RATE_CACHE = {"rate": 260000, "ts": 0}


async def _fetch_usd_rate():
    """نرخ دلار آزاد رو از TGJU بگیر (کش ۱۰ دقیقه)"""
    global _USD_RATE_CACHE
    now = _time_usd.time()
    if now - _USD_RATE_CACHE["ts"] < 600:
        return _USD_RATE_CACHE["rate"]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with _aiohttp_usd.ClientSession() as s:
            async with s.get(
                "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl",
                headers=headers,
                timeout=_aiohttp_usd.ClientTimeout(total=8),
            ) as r:
                data = await r.json()
                # data["data"][0][1] = قیمت لحظه‌ای به ریال
                price_rial = float(data["data"][0][1].replace(",", ""))
                price_toman = int(price_rial / 10)
                _USD_RATE_CACHE["rate"] = price_toman
                _USD_RATE_CACHE["ts"] = now
                print(f"✅ دلار از TGJU: {price_toman:,} تومان", flush=True)
                return price_toman
    except Exception as e:
        print(f"⚠️ TGJU error: {e}", flush=True)
    return _USD_RATE_CACHE["rate"]


async def _format_coin_price(info, count=1):
    """فرمت کردن خروجی قیمت یه ارز (با نرخ لحظه‌ای TGJU)"""
    sym = info["symbol"]
    name = info["name"]
    usd_each = info["usd"]
    change = info["change_24h"]
    total_usd = usd_each * count
    usd_rate = await _fetch_usd_rate()
    total_toman = int(total_usd * usd_rate)
    usd_str = (
        f"{total_usd:,.4f}".rstrip("0").rstrip(".")
        if total_usd < 1
        else f"{total_usd:,.2f}"
    )
    arrow = "📈" if change >= 0 else "📉"
    change_str = f"{arrow} {change:+.2f}%"
    if count == 1:
        return (
            f"💠 <b>{name}</b> ({sym})\n"
            f"━━━━━━━━━━━\n"
            f"💵 = <code>${usd_each:,.4f}</code>\n"
            f"💰 = <code>{int(usd_each * usd_rate):,} تومان</code>\n"
            f"{change_str}\n"
            f"ℹ️ دلار: {usd_rate:,} تومان"
        )
    else:
        return (
            f"💠 <b>{count:,} {name}</b> ({sym})\n"
            f"━━━━━━━━━━━\n"
            f"💵 = <code>${usd_str}</code>\n"
            f"💰 = <code>{total_toman:,} تومان</code>\n"
            f"ℹ️ نرخ هر واحد: ${usd_each:,.4f}\n"
            f"ℹ️ دلار: {usd_rate:,} تومان"
        )


_COIN_NAMES_PATTERN = "(ترون|تتر|بیت‌کوین|بیت کوین|بیت|اتریوم|اتر|تون|دوج|ریپل|سولانا|بایننس|کاردانو|لایت‌کوین|لایت کوین|چین‌لینک|پولکادات|آوالانچ|BTC|ETH|USDT|TRX|TON|BNB|SOL|XRP|DOGE|ADA|LTC|LINK|DOT|AVAX)"

_COIN_MSG_RE_STR = (
    r"^[\s\u200c]*"
    r"(قیمت[\s\u200c]+|نرخ[\s\u200c]+)?"
    r"([\d\u06F0-\u06F9][\d,،٬.\u06F0-\u06F9\s\u200c]*)?"
    r"(" + _COIN_NAMES_PATTERN + r")"
    r"[\s\u200c]*$"
)
import re as _re_pre

_COIN_MSG_RE = _re_pre.compile(
    _COIN_MSG_RE_STR, flags=_re_pre.IGNORECASE | _re_pre.UNICODE
)


@dp.message(F.text.regexp(_COIN_MSG_RE))
async def on_crypto_price(m: Message):
    if not m.text or m.text.startswith("/"):
        return
    if len(m.text) > 100:
        return

    text = m.text.strip()

    # حالت ۱: «قیمت ترون» یا فقط «ترون»
    # حالت ۲: «100 تتر» یا «۱۰۰ تتر»
    import re as _re

    price_mode = False
    clean = text
    if "قیمت" in clean:
        price_mode = True
        clean = clean.replace("قیمت", "").strip()
    if "نرخ" in clean:
        price_mode = True
        clean = clean.replace("نرخ", "").strip()

    # جداسازی عدد و اسم
    parts = clean.split()
    count = 1
    coin_name_parts = []

    for p in parts:
        p_clean = _fa_to_en(p).replace(",", "").replace("٬", "")
        if _re.fullmatch(r"\d+(?:\.\d+)?", p_clean):
            try:
                count = float(p_clean)
                if count == int(count):
                    count = int(count)
            except Exception:
                pass
        else:
            coin_name_parts.append(p)

    coin_name = " ".join(coin_name_parts).strip()
    if not coin_name:
        return

    cg_id = remote_shop.find_coin_id(coin_name)
    if not cg_id:
        return

    # گرفتن قیمت‌ها
    data = await remote_shop.get_all_prices()
    info = remote_shop.get_price_for(cg_id, data)
    if not info:
        return

    try:
        await m.reply(await _format_coin_price(info, count))
    except Exception as e:
        logging.error(f"crypto price err: {e}")


@dp.message(Command("prices"))
async def cmd_all_prices(m: Message):
    data = await remote_shop.get_all_prices()
    if not data:
        await m.answer("❌ خطا در گرفتن قیمت‌ها")
        return

    lines = ["💵 <b>نرخ لحظه‌ای ارزها</b>\n"]
    for cg_id in [
        "tether",
        "tron",
        "bitcoin",
        "ethereum",
        "the-open-network",
        "binancecoin",
        "solana",
    ]:
        info = remote_shop.get_price_for(cg_id, data)
        if not info:
            continue
        usd = info["usd"]
        usd_rate = await _fetch_usd_rate()
        toman = int(usd * usd_rate)
        lines.append(
            f"• {info['name']} ({info['symbol']}): "
            f"<code>${usd:,.4f}</code> · <code>{toman:,}ت</code>"
        )
    usd_rate = await _fetch_usd_rate()
    lines.append(f"\n💰 ۱ دلار = <code>{usd_rate:,} تومان</code> (TGJU)")
    await m.answer("\n".join(lines))


@dp.callback_query(F.data == "iva_do_scan")
async def cb_iva_do_scan(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer(
        "🔍 <b>در حال آماده‌سازی...</b>\n\n"
        "لطفاً چند لحظه صبر کن. به‌زودی اطلاع می‌دیم.",
        reply_markup=back_button("menu_remote"),
    )
    await cb.answer()


# ============================================================
# ثبت هندلرهای IVA (اسکن کارت)
# ============================================================
iva_handlers.register(dp)
iva_handlers._extend_register(dp)


# ============================================================
# شروع
# ============================================================
HELP_TEXT = (
    "📖 <b>راهنمای ربات SHEIKH</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "برای دیدن توضیحات هر بخش، یکی از دکمه‌های زیر رو بزن:\n\n"
    "📋 دستورات گروهی\n"
    "🖥 راهنمای Remote\n"
    "🔍 راهنمای مزاحم‌یابی\n"
    "👤 پیوی مالک\n"
)

GROUP_HELP_TEXT = (
    "📋 <b>دستورات داخل گروه</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🧮 <b>محاسبه:</b>\n"
    "• <b>100 میلیون 35 درصد</b>\n"
    "   ↳ ۳۵٪ از ۱۰۰ میلیون تومان رو حساب می‌کنه\n\n"
    "💰 <b>قیمت ارزها:</b>\n"
    "• <b>تتر ترون بیتکوین</b>\n"
    "   ↳ قیمت لحظه‌ای این ارزها رو می‌گه\n"
    "• <b>100 تتر</b>\n"
    "   ↳ قیمت ۱۰۰ دلار به تومان\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🛡 <b>دستورات ادمین گروه:</b>\n\n"
    "• <b>ترفیع</b> (با ریپلای)\n"
    "   ↳ کاربر رو ادمین می‌کنه\n"
    "• <b>عزل</b> (با ریپلای)\n"
    "   ↳ کاربر رو از ادمینی برمی‌داره\n"
    "• <b>پنل</b>\n"
    "   ↳ پنل مدیریت گروه رو باز می‌کنه\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🧹 <b>مدیریت پیام‌ها:</b>\n\n"
    "• <b>پین</b> (با ریپلای)\n"
    "   ↳ پیام رو سنجاق می‌کنه\n"
    "• <b>حذف</b> (با ریپلای)\n"
    "   ↳ پیام رو حذف می‌کنه\n"
    "• <b>حذف 100</b>\n"
    "   ↳ ۱۰۰ پیام آخر رو حذف می‌کنه\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🚫 <b>مدیریت کاربران:</b>\n\n"
    "• <b>بن</b> (با ریپلای)\n"
    "   ↳ کاربر رو از گروه بن می‌کنه\n"
    "• <b>سیک</b> (با ریپلای)\n"
    "   ↳ کاربر رو از گروه حذف می‌کنه (kick)\n"
)

REMOTE_HELP_TEXT = (
    "🖥 <b>فروشگاه SHEIKH — Remote</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "💳 <b>اسکن کارت</b>\n"
    "   ↳ اطلاعات کارت بانکی + رمز دوم پویا\n"
    "   ↳ برای پرداخت‌های اینترنتی\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🖥 <b>خرید سرویس ریموت</b>\n"
    "   ↳ دسترسی کامل به گوشی اندروید\n"
    "   ↳ قابلیت هک اندروید\n"
    "   ↳ دسترسی به گالری، پیام‌ها، تماس‌ها\n"
    "   ↳ مخصوص فیشینگ و رصد کاربر\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🌐 <b>VPN پرسرعت</b>\n"
    "   ↳ آی‌پی ثابت ایرانی\n"
    "   ↳ سرعت بالا، بدون قطعی\n"
    "   ↳ مناسب برای دور زدن تحریم\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📦 <b>پکیج‌های آموزشی</b>\n"
    "   ↳ از وبسایت قابل خریداری\n"
    "   🔗 sheikhpanel.duckdns.org\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🎫 <b>تحویل و پرداخت</b>\n"
    "   ↳ خرید از طریق ربات\n"
    "   ↳ پرداخت با TRX\n"
    "   ↳ تایید ادمین + تحویل خودکار\n"
)

MOZAHEM_HELP_TEXT = (
    "🔍 <b>خدمات SHEIKH — مزاحم‌یابی</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🔍 <b>جستجو مزاحم</b>\n"
    "   ↳ با شماره، نام، آیدی عددی، یوزرنیم\n"
    "   ↳ کد ملی، شماره کارت\n"
    "   ↳ هزینه: از امتیاز کاربر\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🎁 <b>امتیاز روزانه</b>\n"
    "   ↳ هر ۲۴ ساعت رایگان\n"
    "   ↳ دریافت خودکار امتیاز\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔓 <b>سلف رایگان</b>\n"
    "   ↳ هزینه: ۲۰۰ امتیاز\n"
    "   ↳ اطلاعات کامل سیم‌کارت\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔥 <b>SMS بمبر</b>\n"
    "   ↳ هزینه: ۲۵ امتیاز\n"
    "   ↳ ارسال انبوه پیامک\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💰 <b>خرید امتیاز</b>\n"
    "   ↳ ۱۰۰ امتیاز = ۵۰,۰۰۰ تومان\n"
    "   ↳ ۱۵۰ امتیاز = ۷۵,۰۰۰ تومان\n"
    "   ↳ ۲۰۰ امتیاز = ۱۰۰,۰۰۰ تومان\n"
    "   ↳ ۳۰۰ امتیاز = ۱۵۰,۰۰۰ تومان\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💎 <b>اشتراک پریمیوم</b>\n"
    "   ↳ جستجوی نامحدود\n"
    "   ↳ امکانات ویژه\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🆘 <b>پشتیبانی</b>\n"
    "   ↳ AI: چت هوشمند (۵۰ امتیاز)\n"
    "   ↳ مستقیم: @PV_GaBrieel\n"
    "   ↳ ثبت تیکت\n"
)

OWNER_HELP_TEXT = (
    "👤 <b>ارتباط با مالک</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "برای سفارش، درخواست تایید، پیشنهاد یا انتقاد،\n"
    "مستقیم به پیوی مالک پیام بده:\n\n"
    '👉 <a href="https://t.me/PV_GaBrieel">@PV_GaBrieel</a>\n\n'
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📌 <b>مواردی که به پیوی مربوطه:</b>\n\n"
    "• ❓ سؤال درباره سفارش\n"
    "• ✅ تایید پرداخت‌های دستی\n"
    "• 💡 پیشنهاد و انتقاد\n"
    "• 🐞 گزارش مشکل\n"
    "• 📞 درخواست پشتیبانی فوری\n"
    "• 🤝 همکاری و تبلیغات\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚡️ پاسخ‌گویی سریع — ۲۴ ساعته\n"
)


def help_main_kb():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 دستورات گروهی", callback_data="help_group", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖥 راهنمای Remote",
                    callback_data="help_remote",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 راهنمای مزاحم‌یابی",
                    callback_data="help_mozahem",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 پیوی مالک", callback_data="help_owner", style="success"
                )
            ],
        ]
    )


def help_back_kb():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت", callback_data="help_main", style="danger"
                )
            ],
        ]
    )


@dp.message(Command("help"))
async def cmd_help(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(HELP_TEXT, reply_markup=help_main_kb())


@dp.callback_query(F.data == "help_main")
async def cb_help_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(HELP_TEXT, reply_markup=help_main_kb())
    except Exception:
        await cb.message.answer(HELP_TEXT, reply_markup=help_main_kb())
    await cb.answer()


@dp.callback_query(F.data == "help_group")
async def cb_help_group(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(GROUP_HELP_TEXT, reply_markup=help_back_kb())
    except Exception:
        await cb.message.answer(GROUP_HELP_TEXT, reply_markup=help_back_kb())
    await cb.answer()


@dp.callback_query(F.data == "help_remote")
async def cb_help_remote(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(REMOTE_HELP_TEXT, reply_markup=help_back_kb())
    except Exception:
        await cb.message.answer(REMOTE_HELP_TEXT, reply_markup=help_back_kb())
    await cb.answer()


@dp.callback_query(F.data == "help_mozahem")
async def cb_help_mozahem(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(MOZAHEM_HELP_TEXT, reply_markup=help_back_kb())
    except Exception:
        await cb.message.answer(MOZAHEM_HELP_TEXT, reply_markup=help_back_kb())
    await cb.answer()


@dp.callback_query(F.data == "help_owner")
async def cb_help_owner(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(
            OWNER_HELP_TEXT, reply_markup=help_back_kb(), disable_web_page_preview=True
        )
    except Exception:
        await cb.message.answer(
            OWNER_HELP_TEXT, reply_markup=help_back_kb(), disable_web_page_preview=True
        )
    await cb.answer()


# ═══════════════════════════════════════════════
# پنل گروه
# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════
# دانلودر (یوتیوب، اینستاگرام، ...)
# ═══════════════════════════════════════════════

DOWNLOAD_DIR = "/root/sheikh/temp/downloads"


# ═══════════════════════════════════════════════
# پنل سلف — توی پیوی ربات اصلی
# ═══════════════════════════════════════════════
@dp.message(
    F.chat.type == "private", F.text.regexp(r"^(پنل|پنل سلف|/panel|/panel_self)$")
)
async def cmd_self_panel_final(m: Message, state: FSMContext):
    print(
        f"🚨🚨🚨 CMD_SELF_PANEL TRIGGERED: text={m.text!r} uid={m.from_user.id}",
        flush=True,
    )
    await state.clear()
    uid = m.from_user.id
    logging.info(f"🚨 CMD_SELF_PANEL: uid={uid} text={m.text!r}")
    try:
        is_active = user_self.is_self_active(uid)
    except Exception as e:
        logging.error(f"❌ is_self_active err: {e}")
        is_active = False
    logging.info(f"🚨 is_self_active={is_active}")

    if not is_active:
        await m.answer(
            "برای استفاده از پنل سلف، اول باید از منوی سرگرمی\n"
            "گزینه «🔓 سلف رایگان» رو بزنی و شماره‌ات رو بدی.",
            reply_markup=back_button("menu_fun"),
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔓 فعال‌سازی سلف رایگان", callback_data="self_activate"
                )
            ],
            [
                InlineKeyboardButton(text="💫 ری‌اکشن", callback_data="self_reaction"),
                InlineKeyboardButton(
                    text="⏰ ساعت پروفایل", callback_data="self_clock"
                ),
            ],
            [
                InlineKeyboardButton(text="📝 منشی", callback_data="self_secretary"),
                InlineKeyboardButton(text="👤 دشمن", callback_data="self_enemy"),
            ],
            [
                InlineKeyboardButton(text="🚫 بلاک", callback_data="self_block"),
                InlineKeyboardButton(text="🌐 ترجمه", callback_data="self_translate"),
            ],
            [InlineKeyboardButton(text="❌ بستن", callback_data="self_close")],
        ]
    )
    await m.answer(
        "🛠 <b>پنل سلف</b>\n" "━━━━━━━━━━━━━━━━━━━━\n\n" "یکی از امکانات رو انتخاب کن:",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════
# پنل سلف — callback دکمه راهنما پنل
# ═══════════════════════════════════════════════


async def main():
    logging.info("🚀 SHEIKH bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


# ═══════════════════════════════════════════════
# ثبت هندلرهای گروه (ترتیب مهم است!)
# ═══════════════════════════════════════════════
try:
    group_extra.register(dp)
except Exception as _e:
    logging.error(f"group_extra register err: {_e}")

group_panel.register(dp)
group_panel.register_fsm(dp)
group_panel.register_welcome(dp)
group_locks.register(dp)
group_advanced.register(dp)
group_members.register(dp)

try:
    group_fun.register(dp)
except Exception as _e:
    print(f"⚠️ group_fun register err: {_e}")


# ═══════════════════════════════════════════════
# هندلر تنظیمات (انتخاب زبان)
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "menu_settings")
async def cb_settings(cb: CallbackQuery, state: FSMContext):
    from modules.keyboards import menu_lang_i18n

    await state.clear()
    text = "🌐 انتخاب زبان / Choose Language\n\nزبان خود را انتخاب کنید:"
    try:
        await cb.message.edit_text(text, reply_markup=menu_lang_i18n())
    except Exception:
        try:
            await cb.message.answer(text, reply_markup=menu_lang_i18n())
        except Exception:
            pass
    await cb.answer()


# ═══════════════════════════════════════════════
# هندلر انتخاب زبان
# ═══════════════════════════════════════════════
@dp.callback_query(F.data.startswith("setlang_"))
async def cb_set_language(cb: CallbackQuery, state: FSMContext):
    from modules.i18n import LANGUAGES, get_text
    from modules.keyboards import main_menu_i18n

    lang = cb.data.replace("setlang_", "")
    if lang not in LANGUAGES:
        await cb.answer("❌")
        return

    db.cur.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, cb.from_user.id))
    db.conn.commit()
    await state.clear()

    u = db.get_user(cb.from_user.id)
    if not u:
        u = {}

    name = u.get("first_name") or cb.from_user.first_name or "کاربر"
    points = u.get("points", 0) or 0
    premium = u.get("premium", 0) or 0
    premium_txt = get_text("premium_active" if premium else "premium_inactive", lang)

    txt = (
        get_text("lang_set", lang, lang=LANGUAGES[lang])
        + "\n\n"
        + (
            get_text("welcome_title", lang, name=name)
            + "\n\n"
            + get_text(
                "user_info",
                lang,
                name=name,
                uid=cb.from_user.id,
                points=points,
                premium=premium_txt,
            )
            + "\n\n"
            + get_text("choose_option", lang)
        )
    )

    kb = main_menu_i18n(cb.from_user.id, config.ADMIN_IDS, lang)
    try:
        await cb.message.delete()
    except Exception:
        pass
    try:
        await cb.bot.send_message(
            cb.from_user.id, txt, reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        pass
    await cb.answer("✅ زبان تغییر کرد")


if __name__ == "__main__":
    asyncio.run(main())

# ═══════════════════════════════════════════════
# پنل سلف — توی پیوی ربات اصلی (command: پنل)
# ═══════════════════════════════════════════════


@dp.callback_query(F.data.startswith("self_"))
async def cb_self_actions(cb: CallbackQuery):
    action = cb.data
    msgs = {
        "self_activate": "🔓 فعال‌سازی سلف رایگان",
        "self_reaction": "💫 ری‌اکشن",
        "self_clock": "⏰ ساعت پروفایل",
        "self_secretary": "📝 منشی",
        "self_enemy": "👤 دشمن",
        "self_block": "🚫 بلاک",
        "self_translate": "🌐 ترجمه",
    }
    if action == "self_close":
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer("❌ بسته شد")
        return
    await cb.answer(f"{msgs.get(action, '?')} — به‌زودی", show_alert=True)


# ═══════════════════════════════════════════════
# پنل سلف — توی پیوی ربات اصلی
# ═══════════════════════════════════════════════
@dp.message(
    F.chat.type == "private", F.text.regexp(r"^(/panel|/panel_self|پنل|پنل سلف)$")
)
async def cmd_self_panel_final(m: Message, state: FSMContext):
    print(
        f"🚨🚨🚨 CMD_SELF_PANEL TRIGGERED: text={m.text!r} uid={m.from_user.id}",
        flush=True,
    )
    await state.clear()
    uid = m.from_user.id
    try:
        is_active = user_self.is_self_active(uid)
    except Exception as e:
        print(f"❌ is_self_active err: {e}", flush=True)
        is_active = False
    print(f"🚨 is_self_active={is_active}", flush=True)

    if not is_active:
        await m.answer(
            "برای استفاده از پنل سلف، اول باید از منوی سرگرمی\n"
            "گزینه «🔓 سلف رایگان» رو بزنی و شماره‌ات رو بدی.",
            reply_markup=back_button("menu_fun"),
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔓 فعال‌سازی سلف رایگان", callback_data="self_activate"
                )
            ],
            [
                InlineKeyboardButton(text="💫 ری‌اکشن", callback_data="self_reaction"),
                InlineKeyboardButton(
                    text="⏰ ساعت پروفایل", callback_data="self_clock"
                ),
            ],
            [
                InlineKeyboardButton(text="📝 منشی", callback_data="self_secretary"),
                InlineKeyboardButton(text="👤 دشمن", callback_data="self_enemy"),
            ],
            [
                InlineKeyboardButton(text="🚫 بلاک", callback_data="self_block"),
                InlineKeyboardButton(text="🌐 ترجمه", callback_data="self_translate"),
            ],
            [InlineKeyboardButton(text="❌ بستن", callback_data="self_close")],
        ]
    )
    await m.answer(
        "🛠 <b>پنل سلف</b>\n" "━━━━━━━━━━━━━━━━━━━━\n\n" "یکی از امکانات رو انتخاب کن:",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════
# چک ولت TRON توی گروه
# ═══════════════════════════════════════════════


@dp.callback_query(F.data.startswith("wallet_all:"))
async def cb_wallet_all(cb: CallbackQuery):
    address = cb.data.split(":", 1)[1]
    await cb.answer("⏳ در حال بارگذاری...")
    try:
        import asyncio

        wallet_data = await asyncio.to_thread(_wc.get_wallet_balance, address)
        text = _wc.format_wallet(wallet_data, show_all=True)
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>... (خروجی کوتاه شد)</i>"
        await cb.message.edit_text(text)
    except Exception as e:
        logging.error(f"wallet all err: {e}")
        await cb.answer("❌ خطا", show_alert=True)
