from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from tgbot.models import TelegramUser
from tgbot.bot.keyboards.reply import language_keyboard, main_menu_keyboard
from tgbot.bot.loader import get_text

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""

    # Clear any previous state
    await state.clear()

    # Get or create user in database
    user, created = await sync_to_async(TelegramUser.objects.get_or_create)(
        telegram_id=message.from_user.id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            # 'language': 'ru'  # Default language
        }
    )

    # If user exists, update info
    if not created:
        user.username = message.from_user.username
        user.first_name = message.from_user.first_name
        user.last_name = message.from_user.last_name
        await sync_to_async(user.save)()

    # Get user's language
    lang = user.language

    # If no language set, show language selection
    if not lang:
        welcome_text = "Welcome! Please select your language 👇\nXush kelibsiz! Tilni tanlang 👇"
        await message.answer(
            welcome_text,
            reply_markup=language_keyboard()
        )
    else:
        # Show welcome with selected language
        welcome_text = get_text(lang, 'welcome')
        menu_text = get_text(lang, 'main_menu')

        await message.answer(welcome_text)
        await message.answer(
            menu_text,
            reply_markup=main_menu_keyboard(lang)
        )


@router.message(F.text.in_(["Русский 🇷🇺", "O'zbekcha 🇺🇿"]))
async def select_language(message: Message, state: FSMContext):
    """Handle language selection"""

    # Determine selected language
    lang = 'ru' if message.text == "Русский 🇷🇺" else 'uz'

    # Update user language in database
    user = await sync_to_async(TelegramUser.objects.get)(
        telegram_id=message.from_user.id
    )
    user.language = lang
    await sync_to_async(user.save)()

    # Store language in FSM context
    await state.update_data(language=lang)

    # Confirmation message
    confirm_text = get_text(lang, 'language_selected')
    menu_text = get_text(lang, 'main_menu')

    await message.answer(confirm_text)
    await message.answer(
        menu_text,
        reply_markup=main_menu_keyboard(lang)
    )


@router.message(F.text.in_(["🌐 Сменить язык", "🌐 Tilni o'zgartirish"]))
async def change_language(message: Message, state: FSMContext):
    """Handle language change request"""

    # Get current language
    user = await sync_to_async(TelegramUser.objects.get)(
        telegram_id=message.from_user.id
    )
    lang = user.language

    # Show language selection
    text = get_text(lang, 'welcome')
    await message.answer(
        text,
        reply_markup=language_keyboard()
    )


@router.message(F.text.in_(["ℹ️ Информация", "ℹ️ Ma'lumot"]))
async def show_info(message: Message):
    """Show bot information"""

    # Get user language
    user = await sync_to_async(TelegramUser.objects.get)(
        telegram_id=message.from_user.id
    )
    lang = user.language

    info_text = {
        'ru': (
            "ℹ️ <b>Информация о боте</b>\n\n"
            "Этот бот создан для приема жалоб на коррупционные действия.\n\n"
            "<b>Как подать жалобу:</b>\n"
            "1. Нажмите «Подать жалобу»\n"
            "2. Выберите анонимность\n"
            "3. Заполните все данные\n"
            "4. Подтвердите отправку\n\n"
            "<b>Конфиденциальность:</b>\n"
            "Вы можете подать жалобу анонимно. В этом случае ваши персональные данные "
            "не будут сохранены.\n\n"
            "<b>Что будет с жалобой:</b>\n"
            "Все жалобы поступают в уполномоченный орган и будут рассмотрены в "
            "установленные законом сроки."
        ),
        'uz': (
            "ℹ️ <b>Bot haqida ma'lumot</b>\n\n"
            "Ushbu bot korrupsiya harakatlari bo'yicha shikoyatlarni qabul qilish uchun yaratilgan.\n\n"
            "<b>Shikoyat qanday yuboriladi:</b>\n"
            "1. «Shikoyat yuborish» tugmasini bosing\n"
            "2. Anonimlikni tanlang\n"
            "3. Barcha ma'lumotlarni to'ldiring\n"
            "4. Yuborishni tasdiqlang\n\n"
            "<b>Maxfiylik:</b>\n"
            "Siz shikoyatni anonim yuborishingiz mumkin. Bu holda sizning shaxsiy "
            "ma'lumotlaringiz saqlanmaydi.\n\n"
            "<b>Shikoyat bilan nima qilinadi:</b>\n"
            "Barcha shikoyatlar vakolatli organga yuboriladi va qonun bilan belgilangan "
            "muddatlarda ko'rib chiqiladi."
        )
    }

    await message.answer(
        info_text.get(lang, info_text['ru']),
        reply_markup=main_menu_keyboard(lang)
    )
