import json
from datetime import datetime
from aiogram import Bot, types
from aiogram.types import BufferedInputFile
from config import settings
from services.report_generator import generate_full_json_report

async def send_weekly_report(bot: Bot):
    try:
        json_data = await generate_full_json_report()
        user_count = 0

        try:
            report_dict = json.loads(json_data)
            user_count = len(report_dict.get('users', []))
        except Exception:
            pass

        document = BufferedInputFile(
            json_data.encode("utf-8"),
            filename=f"weekly_report_{datetime.now().strftime('%Y-%m-%d')}.json"
        )

        caption = (
            f"📆 <b>Еженедельный отчёт</b>\n"
            f"📅 Неделя: {datetime.now().strftime('%d.%m.%Y')}\n"
            f"👥 Рефералов: {user_count}\n"
            f"💡 Отчёт содержит все данные по пользователям и вашему заработку (до/после НПД)."
        )

        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_document(admin_id, document, caption=caption, parse_mode="HTML")
            except Exception as e:
                print(f"❌ Не удалось отправить отчёт админу {admin_id}: {e}")

    except Exception as e:
        print(f"❌ Ошибка генерации еженедельного отчёта: {e}")
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"❌ Ошибка при генерации еженедельного отчёта:\n<code>{str(e)[:200]}</code>",
                    parse_mode="HTML"
                )
            except:
                pass