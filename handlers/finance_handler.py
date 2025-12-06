from aiogram import Router, F, types
from aiogram.types import BufferedInputFile
from database.db_manager import get_user_full_data
from services.report_generator import generate_referral_json, generate_referral_text_report_with_conditions

router = Router()

@router.message(F.text == "💰 Финансовый отчёт")
async def show_finance_report(message: types.Message):
    user_data = await get_user_full_data(message.from_user.id)
    if not user_data or "bank" not in user_data:
        await message.answer("Сначала завершите регистрацию.")
        return

    report = generate_referral_text_report_with_conditions(user_data)
    await message.answer(report, parse_mode="HTML")

@router.callback_query(F.data == "📤 Экспорт в JSON")
async def export_json(callback: types.CallbackQuery):
    user_data = await get_user_full_data(callback.from_user.id)
    if not user_data:
        await callback.answer("Сначала завершите регистрацию с помощью /start.")
        return

    try:
        json_str = generate_referral_json(user_data)
        
        await callback.answer_document(
            BufferedInputFile(
                json_str.encode("utf-8"), 
                filename="referral_report.json"
            ),
            caption="📄 Ваши данные в формате JSON."
        )
    except Exception as e:
        print(f"Ошибка при экспорте JSON для user_id={callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка при генерации отчёта.")
    
