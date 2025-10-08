from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List, Dict


def language_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Русский 🇷🇺")
    builder.button(text="O'zbekcha 🇺🇿")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def main_menu_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    if lang == 'ru':
        builder.button(text="📝 Подать жалобу")
        builder.button(text="ℹ️ Информация")
        builder.button(text="🌐 Сменить язык")
    else:
        builder.button(text="📝 Shikoyat yuborish")
        builder.button(text="ℹ️ Ma'lumot")
        builder.button(text="🌐 Tilni o'zgartirish")

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def anonymity_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    if lang == 'ru':
        builder.button(text="С моими данными ✅")
        builder.button(text="Анонимно 🕵️")
    else:
        builder.button(text="Mening ma'lumotlarim bilan ✅")
        builder.button(text="Anonim 🕵️")

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def phone_request_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    text = "📱 Отправить номер телефона" if lang == 'ru' else "📱 Telefon raqamini yuborish"
    builder.button(text=text, request_contact=True)

    return builder.as_markup(resize_keyboard=True)


def skip_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    text = "⏭ Пропустить" if lang == 'ru' else "⏭ O'tkazib yuborish"
    builder.button(text=text)

    return builder.as_markup(resize_keyboard=True)


def media_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    if lang == 'ru':
        builder.button(text="✅ Завершить загрузку")
        builder.button(text="⏭ Пропустить")
    else:
        builder.button(text="✅ Tugatish")
        builder.button(text="⏭ O'tkazib yuborish")

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def confirmation_keyboard(lang='ru'):
    builder = ReplyKeyboardBuilder()

    if lang == 'ru':
        builder.button(text="✅ Отправить")
        builder.button(text="❌ Отменить")
    else:
        builder.button(text="✅ Yuborish")
        builder.button(text="❌ Bekor qilish")

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def regions_inline_keyboard(regions: List[Dict]):
    builder = InlineKeyboardBuilder()

    for region in regions:
        builder.button(
            text=region['name'],
            callback_data=f"region_{region['id']}"
        )

    builder.adjust(1)
    return builder.as_markup()


def districts_inline_keyboard(districts: List[Dict], region_id: int):
    builder = InlineKeyboardBuilder()

    for district in districts:
        builder.button(
            text=district['name'],
            callback_data=f"district_{district['id']}"
        )

    builder.button(
        text="◀️ Назад / Orqaga",
        callback_data="back_to_regions"
    )

    builder.adjust(1)
    return builder.as_markup()


def mahallas_inline_keyboard(mahallas: List[Dict], district_id: int, page: int = 0, per_page: int = 30):
    builder = InlineKeyboardBuilder()

    total = len(mahallas)
    start = page * per_page
    end = start + per_page
    paginated = mahallas[start:end]

    for mahalla in paginated:
        builder.button(
            text=mahalla['name'],
            callback_data=f"mahalla_{mahalla['id']}"
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"mahalla_page_{district_id}_{page-1}"
        ))

    if end < total:
        nav_buttons.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"mahalla_page_{district_id}_{page+1}"
        ))

    builder.adjust(1)

    if nav_buttons:
        markup = builder.as_markup()
        markup.inline_keyboard.append(nav_buttons)

        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад / Orqaga",
                callback_data="back_to_districts"
            )
        ])
        return markup
    else:
        builder.button(
            text="◀️ Назад / Orqaga",
            callback_data="back_to_districts"
        )
        builder.adjust(1)
        return builder.as_markup()


def admin_keyboard():
    builder = ReplyKeyboardBuilder()

    builder.button(text="📊 Статистика")
    builder.button(text="📥 Экспорт")
    builder.button(text="📢 Рассылка")
    builder.button(text="◀️ Выход")

    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)
