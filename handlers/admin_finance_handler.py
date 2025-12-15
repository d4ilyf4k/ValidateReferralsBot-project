import json
import logging
from datetime import datetime
from aiogram import Router, F, types
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import settings
from services.referrer_report_generator import generate_full_json_report
from database.db_manager import (
    get_admin_traffic_overview,
    confirm_user_bonus,
    reject_user_bonus,
    approve_application,
    get_application_by_id,
    reject_application,
)
from utils.keyboards import get_admin_panel_kb
from utils.states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS
    
    
@router.callback_query(F.data == "admin_report")
async def admin_full_report(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await callback.answer("⏳ Формирую отчёт…")

    try:
        json_data = await generate_full_json_report()

        if not json_data:
            await callback.message.answer("📭 Нет данных для отчёта.")
            return

        try:
            parsed = json.loads(json_data)
            users_count = len(parsed.get("users", []))
        except Exception:
            users_count = 0

        filename = f"referrer_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

        await callback.message.answer_document(
            BufferedInputFile(
                json_data.encode("utf-8"),
                filename=filename
            ),
            caption=(
                "📊 <b>Полный отчёт реферора</b>\n\n"
                f"👥 Пользователей: <b>{users_count}</b>\n"
                f"📅 Сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode="HTML"
        )

        logger.info(
            f"Admin {callback.from_user.id} downloaded full report "
            f"({users_count} users)"
        )

    except Exception as e:
        logger.error("Admin report error", exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при генерации отчёта.\n"
            "Проверьте логи сервера."
        )


@router.callback_query(F.data == "admin_traffic_dashboard")
async def admin_traffic_dashboard(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    data = await get_admin_traffic_overview()

    if not data:
        await callback.message.edit_text(
            "📭 Данных по трафику пока нет.",
            reply_markup=get_admin_panel_kb()
        )
        await callback.answer()
        return

    total_users = sum(row["users"] for row in data)

    text = "<b>📊 Источники трафика</b>\n\n"

    for row in data:
        source = row["traffic_source"] or "organic"
        users = row["users"]
        percent = (users / total_users * 100) if total_users else 0

        text += f"• <b>{source}</b>: {users} ({percent:.1f}%)\n"

    text += f"\n<b>Всего пользователей:</b> {total_users}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_panel_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:app:approve:"))
async def admin_approve_application(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    app_id = int(callback.data.split(":")[-1])
    app = await get_application_by_id(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if app["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminStates.waiting_bonus_amount)
    await state.update_data(application_id=app_id)

    await callback.message.answer(
        f"💰 Введите сумму бонуса для пользователя <code>{app['user_id']}</code>:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:app:reject:"))
async def admin_reject_application(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    app_id = int(callback.data.split(":")[-1])
    app = await get_application_by_id(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if app["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    await reject_application(app_id)

    await state.clear()

    await callback.message.edit_text("❌ Заявка отклонена")
    await callback.answer()
