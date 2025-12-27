import json
from datetime import datetime

from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import settings
from jobs.weekly_aggregator import generate_weekly_snapshot


async def send_weekly_report(bot: Bot):
    """
    Еженедельный отчёт для администратора.

    • Источник данных: applications
    • Source of truth: weekly_aggregator.generate_weekly_snapshot
    • Основной формат: JSON
    • Telegram — только краткая сводка
    """

    try:
        # === Генерация weekly JSON ===
        snapshot_json = await generate_weekly_snapshot()
        snapshot = json.loads(snapshot_json)

        summary = snapshot.get("summary", {})
        by_bank = snapshot.get("by_bank", [])

        # === Агрегаты ===
        total_applications = summary.get("applications", 0)
        approved = summary.get("approved", 0)
        pending = summary.get("pending", 0)
        rejected = summary.get("rejected", 0)
        gross_income = summary.get("gross_income", 0)

        # === JSON-файл ===
        document = BufferedInputFile(
            snapshot_json.encode("utf-8"),
            filename=f"weekly_report_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        )

        # === Топ банков ===
        top_banks = sorted(
            by_bank,
            key=lambda x: x.get("applications", 0),
            reverse=True
        )[:5]

        banks_text = "\n".join(
            f"• <b>{row['bank']}</b>: "
            f"{row['applications']} заявок, "
            f"{row['approved']} подтверждено, "
            f"{row['gross_income']} ₽"
            for row in top_banks
        ) or "—"

        # === Текстовая сводка ===
        caption = (
            "📆 <b>Еженедельный отчёт</b>\n"
            f"<i>{snapshot.get('period')}</i>\n\n"
            f"📝 Заявок: <b>{total_applications}</b>\n"
            f"✅ Подтверждено: <b>{approved}</b>\n"
            f"⏳ В ожидании: <b>{pending}</b>\n"
            f"❌ Отклонено: <b>{rejected}</b>\n"
            f"💰 Gross доход: <b>{gross_income} ₽</b>\n\n"
            "🏦 <b>Топ банков:</b>\n"
            f"{banks_text}\n\n"
            "<i>Отчёт сформирован на основе заявок. "
            "Фактические выплаты определяются банками.</i>"
        )

        # === Отправка админам ===
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=document,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"❌ Не удалось отправить отчёт админу {admin_id}: {e}")

    except Exception as e:
        print(f"❌ Ошибка weekly_report_job: {e}")

        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "❌ Ошибка генерации weekly-отчёта:\n"
                        f"<code>{str(e)[:300]}</code>"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
