from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.admin_users import get_admin_users_list, get_admin_users_page
from db.users import get_user_full_data
from utils.keyboards import get_admin_users_list_kb, get_admin_user_card_kb, get_user_apps_kb
from db.admin_applications import get_user_applications_page

router = Router()


@router.callback_query(F.data == "admin_users")
async def admin_users_list_handler(call: CallbackQuery):
    users = await get_admin_users_list()

    if not users:
        await call.message.edit_text(
            "👥 <b>Пользователи</b>\n\n"
            "Пока нет ни одного пользователя."
        )
        return

    await call.message.edit_text(
        "👥 <b>Пользователи</b>\n\n"
        "Выберите пользователя:",
        reply_markup=get_admin_users_list_kb(users)
    )

@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_card_handler(call: CallbackQuery):
    user_id = int(call.data.split(":")[2])

    data = await get_user_full_data(user_id)

    if not data:
        await call.message.edit_text(
            "❌ Пользователь не найден.",
            reply_markup=get_admin_user_card_kb(user_id)
        )
        return

    text = (
        f"👤 <b>Пользователь</b>\n\n"
        f"ID: <code>{data['user_id']}</code>\n"
        f"Username: @{data['username'] or '—'}\n"
        f"Имя: {data['first_name'] or '—'}\n\n"
        f"📊 <b>Статистика</b>\n"
        f"Заявок: {data['applications_total']}\n"
        f"Одобрено: {data['approved_count']}\n"
        f"Отклонено: {data['rejected_count']}\n"
        f"В ожидании: {data['pending_count']}\n\n"
        f"💰 Подтверждённый доход: {data['approved_bonus']} ₽"
    )

    await call.message.edit_text(
        text,
        reply_markup=get_admin_user_card_kb(user_id)
    )

@router.callback_query(F.data.startswith("admin:user:") & F.data.endswith(":apps"))
async def admin_user_apps(call: CallbackQuery):
    parts = call.data.split(":")
    user_id = int(parts[2])
    page = int(parts[4]) if len(parts) > 4 else 0

    limit = 5
    offset = page * limit

    apps = await get_user_applications_page(user_id, limit, offset)

    lines = [f"📄 <b>Заявки пользователя {user_id}</b>\n"]

    for a in apps:
        lines.append(
            f"🏦 {a['bank']} / {a['product_key']}\n"
            f"Статус: {a['status']}\n"
            f"Бонус: {a['gross_bonus']} ₽\n"
            f"{a['created_at']}\n"
        )

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=get_user_apps_kb(user_id, page, len(apps))
    )

@router.callback_query(F.data.startswith("admin:users"))
async def admin_users_paged(call: CallbackQuery):
    page = int(call.data.split(":")[-1]) if ":" in call.data else 0

    limit = 10
    offset = page * limit

    users = await get_admin_users_page(limit, offset)

    await call.message.edit_text(
        f"👥 <b>Пользователи</b>\n\n"
        f"Страница {page + 1}",
        reply_markup=get_admin_users_list_kb(users, page)
    )