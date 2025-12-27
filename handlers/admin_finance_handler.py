import json
import logging
from aiogram import Router, F, types
from aiogram.types import BufferedInputFile
from config import settings
from datetime import datetime
from db.finance import get_admin_traffic_overview
from services.referrer_report_generator import build_referrer_json_report
from utils.keyboards import get_admin_panel_kb

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
        json_data = await build_referrer_json_report()

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


# ❗ временная заглушка
OFFERS = [
    {
        "id": 1,
        "product_name": "Black",
        "title": "50% кэшбек в супермаркетах",
        "conditions": "Кэшбек 50% на покупки в супермаркетах",
        "is_active": True
    },
    {
        "id": 2,
        "product_name": "Black",
        "title": "Золотой билет",
        "conditions": "Бонус 500₽ после выполнения условий",
        "is_active": False
    }
]


