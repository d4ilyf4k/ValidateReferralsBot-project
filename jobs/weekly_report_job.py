import json
from datetime import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import settings
from jobs.weekly_aggregator import (
    get_weekly_traffic_stats,
    get_weekly_finance_stats
)


async def send_weekly_report(bot: Bot):
    """
    Еженедельный отчёт для администратора.
    Аналитика трафика + оценка дохода (gross).
    """

    try:
        # --- данные ---
        traffic = await get_weekly_traffic_stats(days=7)
        finance = await get_weekly_finance_stats(days=7)

        total_users = sum(row["users"] for row in traffic)
        total_products = finance.get("products", 0)
        gross_income = finance.get("gross_income", 0)

        # --- JSON snapshot ---
        report = {
            "period_days": 7,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "users": total_users,
                "products": total_products,
                "gross_income": gross_income
            },
            "traffic_sources": traffic
        }

        json_data = json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        )

        document = BufferedInputFile(
            json_data.encode("utf-8"),
            filename=f"weekly_report_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        )

        # --- текстовая сводка ---
        top_sources = sorted(
            traffic,
            key=lambda x: x["users"],
            reverse=True
        )[:5]

        sources_text = "\n".join(
            f"• <b>{row['traffic_source'] or 'unknown'}</b>: {row['users']} юзеров, {row['products']} оформлений"
            for row in top_sources
        ) or "—"

        caption = (
            "📆 <b>Еженедельный отчёт</b>\n\n"
            f"👥 Пользователей: <b>{total_users}</b>\n"
            f"📝 Оформлений: <b>{total_products}</b>\n"
            f"💰 Оценка дохода (gross): <b>{gross_income} ₽</b>\n\n"
            "📊 <b>Трафик по источникам:</b>\n"
            f"{sources_text}\n\n"
            "<i>Доход рассчитан ориентировочно на основе офферов. "
            "Фактические выплаты определяются банком.</i>"
        )

        # --- отправка ---
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_document(
                    admin_id,
                    document,
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
                    admin_id,
                    f"❌ Ошибка генерации weekly-отчёта:\n<code>{str(e)[:300]}</code>",
                    parse_mode="HTML"
                )
            except:
                pass