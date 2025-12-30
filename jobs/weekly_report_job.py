import json
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import BufferedInputFile
from config import settings
from .weekly_aggregator import generate_weekly_snapshot

async def send_weekly_report(bot: Bot):
    try:
        # ===== SNAPSHOT =====
        snapshot_json = await generate_weekly_snapshot()
        snapshot = json.loads(snapshot_json)

        summary = snapshot.get("summary", {})
        banks = snapshot.get("banks", [])

        # ===== FILE =====
        # Используем МСК для имени файла
        now_msk = datetime.utcnow() + timedelta(hours=3)
        filename = f"weekly_report_{now_msk.strftime('%Y-%m-%d')}.json"
        document = BufferedInputFile(
            snapshot_json.encode("utf-8"),
            filename=filename
        )

        # ===== TOP BANKS =====
        top_banks = sorted(
            banks,
            key=lambda x: x.get("applications", 0),
            reverse=True
        )[:5]

        banks_text = (
            "\n".join(
                f"• <b>{r['bank_key']}</b>: "
                f"{r['applications']} заявок, "
                f"{r['users']} пользователей, "
                f"{r['products']} продуктов"
                for r in top_banks
            ) if top_banks else "—"
        )

        # ===== CAPTION =====
        # Принудительно формируем строку времени МСК
        generated_at_str = now_msk.strftime("%d.%m.%Y %H:%M:%S") + " МСК"
        period_str = f"{snapshot['meta']['period_start']} — {snapshot['meta']['period_end']}"

        caption = (
            "📆 <b>Еженедельный аналитический отчёт</b>\n"
            f"<i>{generated_at_str}</i>\n"
            f"<i>Период: {period_str}</i>\n\n"
            f"📝 Заявок: <b>{summary.get('applications', 0)}</b>\n"
            f"👥 Пользователей: <b>{summary.get('users', 0)}</b>\n\n"
            "🏦 <b>Топ банков по активности:</b>\n"
            f"{banks_text}\n\n"
            "<i>Отчёт основан на пользовательской активности и выборе продуктов.</i>"
        )

        # ===== SEND =====
        for admin_id in settings.ADMIN_IDS:
            await bot.send_document(
                chat_id=admin_id,
                document=document,
                caption=caption,
                parse_mode="HTML"
            )

    except Exception as e:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "❌ Ошибка weekly-отчёта:\n"
                        f"<code>{str(e)[:300]}</code>"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass
