from datetime import datetime
import json
import os
from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from config import settings
from db.finance import (
    get_admin_finance_details,
    get_admin_finance_summary,
    get_admin_traffic_finance_projection,
)

from db.finance import get_admin_traffic_overview
from services.referrer_report_generator import generate_admin_dashboard_text, build_referrer_report
from services.pdf_report_generator import build_admin_pdf_report
from utils.keyboards import (
    get_admin_panel_kb,
    get_admin_dashboard_kb,
    get_admin_finance_kb,
    get_admin_traffic_filter_kb,
    get_admin_reports_kb
)


router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# ==========================
# ADMIN PANEL
# ==========================

@router.callback_query(F.data == "admin:finance")
async def admin_finance_root(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Нет доступа", show_alert=True)

    data = await get_admin_finance_summary()

    if data["total_count"] == 0:
        text = "💰 <b>Финансы</b>\n\nПока нет подтверждённых заявок."
    else:
        text = (
            "💰 <b>Финансы</b>\n\n"
            f"📦 Подтверждённых заявок: <b>{data['total_count']}</b>\n"
            f"💵 Общий доход: <b>{data['total_profit']:,} ₽</b>"
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_finance_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:finance:summary")
async def admin_finance_summary_cb(callback: types.CallbackQuery):
    await callback.answer()

    data = await get_admin_finance_summary()

    text = (
        "📊 <b>Финансовая сводка</b>\n\n"
        f"💳 Подтверждённых заявок: <b>{data['total_count']}</b>\n"
        f"💰 Общая прибыль: <b>{data['total_profit']} ₽</b>\n\n"
        "Выберите действие ниже:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_finance_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:finance:details")
async def admin_finance_details_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    rows = await get_admin_finance_details()
    if not rows:
        return await callback.message.edit_text("📭 Пока нет данных по продуктам")

    text = (
        "📄 <b>Детальный финансовый отчёт</b>\n"
        "<i>Суммы указаны согласно условиям офферов. "
        "Фактическая выплата зависит от банка.</i>\n\n"
    )

    for r in rows[:20]:
        text += (
            f"👤 {r['user_id']} | {r['traffic_source']}\n"
            f"🏦 {r['bank']}\n"
            f"📦 {r['product_name']}\n"
            f"💰 {r['referrer_bonus']:,} ₽\n"
            f"🕒 {r['created_at']}\n\n"
        )

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

    
@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Нет доступа", show_alert=True)

    text = await generate_admin_dashboard_text()

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_dashboard_kb()
    )
    await callback.answer()
    
    
@router.callback_query(F.data == "admin:traffic")
async def admin_traffic_root(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    total_users = sum(r["users"] for r in overview)
    total_products = sum(r["products_selected"] for r in overview)
    total_net = sum(r["net_bonus"] for r in projection)

    text = (
        "📊 <b>Трафик (сводка)</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"📦 Продуктов: <b>{total_products}</b>\n"
        f"💰 Прогноз дохода: <b>{total_net} ₽</b>"
    )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "admin:traffic:all")
async def admin_traffic_all(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    text = "<b>📊 Трафик: все источники</b>\n\n"

    for ov in overview:
        pr = next(
            (p for p in projection if p["traffic_source"] == ov["traffic_source"]),
            None
        )

        text += (
            f"• <b>{ov['traffic_source']}</b>\n"
            f"  👥 Пользователей: {ov['users']}\n"
            f"  📦 Продуктов: {ov['products_selected']}\n"
            f"  💰 Нетто: {pr['net_bonus'] if pr else 0} ₽\n\n"
        )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()


@router.callback_query(
    F.data.startswith("admin:traffic:")
    & ~F.data.in_(["admin:traffic", "admin:traffic:all"])
)
async def admin_traffic_by_source(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    source = cb.data.split(":")[-1]

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    ov = next((r for r in overview if r["traffic_source"] == source), None)
    pr = next((r for r in projection if r["traffic_source"] == source), None)

    text = (
        f"📊 <b>Трафик: {source}</b>\n\n"
        f"👥 Пользователей: <b>{ov['users'] if ov else 0}</b>\n"
        f"📦 Продуктов: <b>{ov['products_selected'] if ov else 0}</b>\n"
        f"💰 Доход (нетто): <b>{pr['net_bonus'] if pr else 0} ₽</b>"
    )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_reports")
async def admin_reports_root(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    await cb.message.edit_text(
        "📑 <b>Отчёты</b>\n\n"
        "Выберите тип отчёта:",
        parse_mode="HTML",
        reply_markup=get_admin_reports_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "admin:report:json")
async def admin_report_json(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    report = await build_referrer_report()

    # пока просто отправляем как файл
    json_bytes = json.dumps(report, indent=2, ensure_ascii=False).encode()

    await cb.message.answer_document(
        types.BufferedInputFile(
            json_bytes,
            filename="admin_report.json"
        )
    )
    await cb.answer()


@router.callback_query(F.data == "admin:report:pdf")
async def admin_report_pdf(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    # ===== Формируем отчёт =====
    report = await build_referrer_report()

    # ===== Папка для архивных еженедельных PDF =====
    output_dir = os.path.join(os.getcwd(), "data", "reports", "weekly")
    os.makedirs(output_dir, exist_ok=True)

    # ===== Генерируем уникальное имя файла =====
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"admin_report_weekly_{timestamp}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    try:
        # ===== Генерация PDF =====
        build_admin_pdf_report(report, pdf_path)

        # ===== Отправка PDF =====
        await cb.message.answer_document(
            types.FSInputFile(pdf_path),
            caption=f"📄 Еженедельный отчёт ({timestamp})"
        )

        await cb.answer()

    except Exception as e:
        await cb.answer(
            f"❌ Ошибка при генерации отчёта:\n{str(e)[:300]}",
            show_alert=True
        )

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        "🛠 <b>Админ-меню</b>",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()