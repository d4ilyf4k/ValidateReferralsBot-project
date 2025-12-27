from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from utils.back_routes import BACK_ROUTES
from utils.keyboards import add_back_button, get_admin_panel_kb
import inspect
router = Router()

@router.callback_query(F.data == "admin:back")
async def admin_back(call: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state and current_state.startswith("OfferFSM"):
        await state.clear()
        await call.message.edit_text(
            "🔐 Админ-панель",
            reply_markup=add_back_button(get_admin_panel_kb())
        )
        await call.answer()
        return

    data = await state.get_data()
    route = BACK_ROUTES.get(current_state)

    if route:
        next_state = route.get("state")
        if next_state:
            await state.set_state(next_state)

        try:
            text = route["text"].format(**data)
        except Exception:
            text = route["text"]

        keyboard_factory = route.get("keyboard")
        markup = None
        if keyboard_factory:
            result = keyboard_factory(data)

            if inspect.isawaitable(result):
                markup = await result
            else:
                markup = result

        if route.get("with_back", True) and markup:
            markup = add_back_button(markup)

        await call.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode=route.get("parse_mode")
        )
        await call.answer()
        return

    await state.clear()
    await call.message.edit_text(
        "🔐 Админ-панель",
        reply_markup=add_back_button(get_admin_panel_kb())
    )
    await call.answer()
