from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
import re

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import os
import zipfile
from aiogram.types import FSInputFile

from tgbot.models import TelegramUser, Complaint, ComplaintMedia
from tgbot.bot.states.complaint import ComplaintStates
from tgbot.bot.keyboards.reply import (
    anonymity_keyboard,
    phone_request_keyboard,
    skip_keyboard,
    media_keyboard,
    confirmation_keyboard,
    main_menu_keyboard,
    regions_inline_keyboard,
    districts_inline_keyboard,
    mahallas_inline_keyboard
)
from tgbot.bot.loader import get_text, location_manager, bot, ADMIN_CHAT_ID

router = Router()


@router.message(F.text.in_(["📝 Подать жалобу", "📝 Shikoyat yuborish"]))
async def start_complaint(message: Message, state: FSMContext):
    user = await sync_to_async(TelegramUser.objects.get)(
        telegram_id=message.from_user.id
    )
    lang = user.language
    await state.update_data(language=lang)
    text = get_text(lang, 'anonymity_choice')
    await message.answer(
        text,
        reply_markup=anonymity_keyboard(lang)
    )

    await state.set_state(ComplaintStates.anonymity)


@router.message(ComplaintStates.anonymity)
async def process_anonymity(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get('language', 'ru')
    is_anonymous = message.text in ["Анонимно 🕵️", "Anonim 🕵️"]

    await state.update_data(is_anonymous=is_anonymous)

    if is_anonymous:
        text = get_text(lang, 'select_region')
        regions = location_manager.get_all_regions()

        await message.answer(
            text,
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(
            "Выберите регион / Viloyatni tanlang:",
            reply_markup=regions_inline_keyboard(regions)
        )
        await state.set_state(ComplaintStates.region)
    else:
        text = get_text(lang, 'enter_full_name')
        await message.answer(
            text,
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(ComplaintStates.full_name)


@router.message(ComplaintStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')
    if len(message.text.split()) < 2:
        error_text = "❌ Введите полное ФИО (минимум имя и фамилию)" if lang == 'ru' else "❌ To'liq F.I.Sh kiriting (kamida ism va familiya)"
        await message.answer(error_text)
        return

    await state.update_data(full_name=message.text)
    text = get_text(lang, 'enter_phone')
    await message.answer(
        text,
        reply_markup=phone_request_keyboard(lang)
    )
    await state.set_state(ComplaintStates.phone_number)


@router.message(ComplaintStates.phone_number, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = f'+{phone}'

    await state.update_data(phone_number=phone)
    await ask_for_region(message, state)


@router.message(ComplaintStates.phone_number, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    phone = message.text.strip()

    phone = re.sub(r'[\s\-()]', '', phone)

    if not re.match(r'^\+?998\d{9}$', phone):
        error_text = get_text(lang, 'invalid_phone')
        await message.answer(error_text)
        return

    if not phone.startswith('+'):
        phone = f'+{phone}'

    await state.update_data(phone_number=phone)
    await ask_for_region(message, state)


async def ask_for_region(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    text = get_text(lang, 'select_region')
    regions = location_manager.get_all_regions()

    await message.answer(
        text='.',
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        text,
        reply_markup=regions_inline_keyboard(regions)
    )
    await state.set_state(ComplaintStates.region)


@router.callback_query(ComplaintStates.region, F.data.startswith("region_"))
async def process_region(callback: CallbackQuery, state: FSMContext):

    region_id = int(callback.data.split('_')[1])
    region = location_manager.get_region_by_id(region_id)

    if not region:
        await callback.answer("Ошибка / Xatolik")
        return

    await state.update_data(
        region_id=region_id,
        region_name=region['name']
    )
    districts = location_manager.get_districts_by_region(region_id)

    data = await state.get_data()
    lang = data.get('language', 'ru')
    text = get_text(lang, 'select_district')

    await callback.message.edit_text(
        text,
        reply_markup=districts_inline_keyboard(districts, region_id)
    )

    await state.set_state(ComplaintStates.district)
    await callback.answer()


@router.callback_query(ComplaintStates.region, F.data == "back_to_regions")
@router.callback_query(ComplaintStates.district, F.data == "back_to_regions")
async def back_to_regions(callback: CallbackQuery, state: FSMContext):
    regions = location_manager.get_all_regions()

    await callback.message.edit_text(
        "Выберите регион / Viloyatni tanlang:",
        reply_markup=regions_inline_keyboard(regions)
    )

    await state.set_state(ComplaintStates.region)
    await callback.answer()


@router.callback_query(ComplaintStates.district, F.data.startswith("district_"))
async def process_district(callback: CallbackQuery, state: FSMContext):
    district_id = int(callback.data.split('_')[1])
    district = location_manager.get_district_by_id(district_id)

    if not district:
        await callback.answer("Ошибка / Xatolik")
        return

    await state.update_data(
        district_id=district_id,
        district_name=district['name']
    )
    mahallas = location_manager.get_streets_by_district(district_id)

    data = await state.get_data()
    lang = data.get('language', 'ru')
    text = get_text(lang, 'select_mahalla')

    await callback.message.edit_text(
        text,
        reply_markup=mahallas_inline_keyboard(mahallas, district_id, page=0)
    )

    await state.set_state(ComplaintStates.mahalla)
    await callback.answer()


@router.callback_query(ComplaintStates.district, F.data == "back_to_districts")
@router.callback_query(ComplaintStates.mahalla, F.data == "back_to_districts")
async def back_to_districts(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    region_id = data.get('region_id')

    districts = location_manager.get_districts_by_region(region_id)

    await callback.message.edit_text(
        "Выберите район / Tumanni tanlang:",
        reply_markup=districts_inline_keyboard(districts, region_id)
    )

    await state.set_state(ComplaintStates.district)
    await callback.answer()


@router.callback_query(ComplaintStates.mahalla, F.data.startswith("mahalla_page_"))
async def mahalla_pagination(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    district_id = int(parts[2])
    page = int(parts[3])

    mahallas = location_manager.get_streets_by_district(district_id)

    await callback.message.edit_reply_markup(
        reply_markup=mahallas_inline_keyboard(mahallas, district_id, page=page)
    )

    await callback.answer()


@router.callback_query(ComplaintStates.mahalla, F.data.startswith("mahalla_"))
async def process_mahalla(callback: CallbackQuery, state: FSMContext):
    if '_page_' in callback.data:
        return

    mahalla_id = int(callback.data.split('_')[1])
    mahalla = location_manager.get_street_by_id(mahalla_id)

    if not mahalla:
        await callback.answer("Ошибка / Xatolik")
        return

    await state.update_data(
        street_id=mahalla_id,
        street_name=mahalla['name']
    )
    data = await state.get_data()
    lang = data.get('language', 'ru')
    text = get_text(lang, 'enter_target_name')

    await callback.message.answer(text)
    await callback.message.delete()

    await state.set_state(ComplaintStates.target_full_name)
    await callback.answer()


@router.message(ComplaintStates.target_full_name)
async def process_target_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')
    await state.update_data(target_full_name=message.text)

    text = get_text(lang, 'enter_target_position')
    await message.answer(text)
    await state.set_state(ComplaintStates.target_position)


@router.message(ComplaintStates.target_position)
async def process_target_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    await state.update_data(target_position=message.text)
    text = get_text(lang, 'enter_target_org')
    await message.answer(text)

    await state.set_state(ComplaintStates.target_organization)


@router.message(ComplaintStates.target_organization)
async def process_target_organization(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    await state.update_data(target_organization=message.text)
    text = get_text(lang, 'enter_complaint_text')
    await message.answer(text)

    await state.set_state(ComplaintStates.complaint_text)


@router.message(ComplaintStates.complaint_text)
async def process_complaint_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    if len(message.text) < 20:
        error_text = "❌ Описание слишком короткое. Минимум 20 символов." if lang == 'ru' else "❌ Tavsif juda qisqa. Minimal 20 ta belgi."
        await message.answer(error_text)
        return

    await state.update_data(complaint_text=message.text)
    text = get_text(lang, 'attach_media')
    await message.answer(
        text,
        reply_markup=media_keyboard(lang)
    )

    await state.update_data(media_files=[])
    await state.set_state(ComplaintStates.media_files)


@router.message(ComplaintStates.media_files, F.photo)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    media_files = data.get('media_files', [])
    photo = message.photo[-1]

    media_files.append({
        'file_id': photo.file_id,
        'file_type': 'photo'
    })

    await state.update_data(media_files=media_files)

    lang = data.get('language', 'ru')
    confirm_text = f"✅ Фото получено ({len(media_files)})" if lang == 'ru' else f"✅ Rasm qabul qilindi ({len(media_files)})"
    await message.answer(confirm_text)


@router.message(ComplaintStates.media_files, F.video)
async def process_video(message: Message, state: FSMContext):
    data = await state.get_data()
    media_files = data.get('media_files', [])

    media_files.append({
        'file_id': message.video.file_id,
        'file_type': 'video'
    })

    await state.update_data(media_files=media_files)

    lang = data.get('language', 'ru')
    confirm_text = f"✅ Видео получено ({len(media_files)})" if lang == 'ru' else f"✅ Video qabul qilindi ({len(media_files)})"
    await message.answer(confirm_text)


@router.message(ComplaintStates.media_files, F.document)
async def process_document(message: Message, state: FSMContext):
    data = await state.get_data()
    media_files = data.get('media_files', [])

    media_files.append({
        'file_id': message.document.file_id,
        'file_type': 'document',
        'file_name': message.document.file_name
    })

    await state.update_data(media_files=media_files)

    lang = data.get('language', 'ru')
    confirm_text = f"✅ Документ получен ({len(media_files)})" if lang == 'ru' else f"✅ Hujjat qabul qilindi ({len(media_files)})"
    await message.answer(confirm_text)


@router.message(ComplaintStates.media_files, F.text.in_([
    "✅ Завершить загрузку", "✅ Tugatish",
    "⏭ Пропустить", "⏭ O'tkazib yuborish"
]))
async def finish_media_upload(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get('language', 'ru')
    summary = await create_complaint_summary(data, lang)

    text = get_text(lang, 'confirmation')
    await message.answer(
        f"{text}\n\n{summary}",
        reply_markup=confirmation_keyboard(lang)
    )

    await state.set_state(ComplaintStates.confirmation)


async def create_complaint_summary(data: dict, lang: str) -> str:

    is_anonymous = data.get('is_anonymous', False)

    if lang == 'ru':
        summary = "<b>📋 Резюме жалобы</b>\n\n"

        if not is_anonymous:
            summary += f"<b>Заявитель:</b> {data.get('full_name', 'Не указано')}\n"
            summary += f"<b>Телефон:</b> {data.get('phone_number', 'Не указано')}\n\n"
        else:
            summary += "<b>Тип:</b> Анонимная жалоба\n\n"

        summary += f"<b>📍 Адрес:</b>\n"
        summary += f"{data.get('region_name')}, {data.get('district_name')}"
        if data.get('street_name'):
            summary += f", {data.get('street_name')}"
        summary += "\n\n"

        summary += f"<b>👨‍💼 На кого жалоба:</b>\n"
        summary += f"ФИО: {data.get('target_full_name')}\n"
        summary += f"Должность: {data.get('target_position')}\n"
        summary += f"Организация: {data.get('target_organization')}\n\n"

        summary += f"<b>📝 Суть жалобы:</b>\n{data.get('complaint_text')}\n\n"

        media_count = len(data.get('media_files', []))
        if media_count > 0:
            summary += f"<b>📎 Прикреплено файлов:</b> {media_count}\n"
    else:
        summary = "<b>📋 Shikoyat xulosasi</b>\n\n"

        if not is_anonymous:
            summary += f"<b>Ariza beruvchi:</b> {data.get('full_name', 'Ko`rsatilmagan')}\n"
            summary += f"<b>Telefon:</b> {data.get('phone_number', 'Ko`rsatilmagan')}\n\n"
        else:
            summary += "<b>Turi:</b> Anonim shikoyat\n\n"

        summary += f"<b>📍 Manzil:</b>\n"
        summary += f"{data.get('region_name')}, {data.get('district_name')}"
        if data.get('street_name'):
            summary += f", {data.get('street_name')}"
        summary += "\n\n"

        summary += f"<b>👨‍💼 Kimga shikoyat:</b>\n"
        summary += f"F.I.Sh: {data.get('target_full_name')}\n"
        summary += f"Lavozim: {data.get('target_position')}\n"
        summary += f"Tashkilot: {data.get('target_organization')}\n\n"

        summary += f"<b>📝 Shikoyat matni:</b>\n{data.get('complaint_text')}\n\n"

        media_count = len(data.get('media_files', []))
        if media_count > 0:
            summary += f"<b>📎 Biriktirilgan fayllar:</b> {media_count}\n"

    return summary


@router.message(ComplaintStates.confirmation, F.text.in_([
    "✅ Отправить", "✅ Yuborish"
]))
async def confirm_and_send_complaint(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get('language', 'ru')

    try:
        user = await sync_to_async(TelegramUser.objects.get)(
            telegram_id=message.from_user.id
        )

        complaint = await sync_to_async(Complaint.objects.create)(
            user=user,
            is_anonymous=data.get('is_anonymous', False),
            full_name=data.get('full_name'),
            phone_number=data.get('phone_number'),
            telegram_username=message.from_user.username,
            region_id=data.get('region_id'),
            region_name=data.get('region_name'),
            district_id=data.get('district_id'),
            district_name=data.get('district_name'),
            street_id=data.get('street_id'),
            street_name=data.get('street_name'),
            target_full_name=data.get('target_full_name'),
            target_position=data.get('target_position'),
            target_organization=data.get('target_organization'),
            complaint_text=data.get('complaint_text'),
            status='new'
        )

        media_files = data.get('media_files', [])
        for media in media_files:
            await sync_to_async(ComplaintMedia.objects.create)(
                complaint=complaint,
                file_id=media['file_id'],
                file_type=media['file_type'],
                file_name=media.get('file_name')
            )

        if ADMIN_CHAT_ID:
            await send_complaint_to_admin(complaint, media_files, lang)

        # Confirm to user
        success_text = get_text(lang, 'complaint_sent').format(complaint.id)
        await message.answer(
            success_text,
            reply_markup=main_menu_keyboard(lang)
        )

        await state.clear()

    except Exception as e:
        print(f"Error saving complaint: {e}")
        error_text = get_text(lang, 'error')
        await message.answer(
            error_text,
            reply_markup=main_menu_keyboard(lang)
        )
        await state.clear()


@router.message(ComplaintStates.confirmation, F.text.in_([
    "❌ Отменить", "❌ Bekor qilish"
]))
async def cancel_complaint(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')

    cancel_text = get_text(lang, 'complaint_cancelled')
    await message.answer(
        cancel_text,
        reply_markup=main_menu_keyboard(lang)
    )

    await state.clear()


# async def send_complaint_to_admin(complaint, media_files: list, lang: str):

#     admin_text = f"🚨 <b>Новая жалоба #{complaint.id}</b>\n\n"

#     if complaint.is_anonymous:
#         admin_text += "🕵️ <b>Тип:</b> Анонимная\n\n"
#     else:
#         admin_text += f"👤 <b>От:</b> {complaint.full_name}\n"
#         admin_text += f"📱 <b>Телефон:</b> {complaint.phone_number}\n"
#         if complaint.telegram_username:
#             admin_text += f"💬 <b>Telegram:</b> @{complaint.telegram_username}\n"
#         admin_text += "\n"

#     admin_text += f"📍 <b>Регион:</b> {complaint.region_name}\n"
#     admin_text += f"🏘 <b>Район:</b> {complaint.district_name}\n"
#     if complaint.street_name:
#         admin_text += f"📌 <b>Махалля:</b> {complaint.street_name}\n"
#     admin_text += "\n"

#     admin_text += f"👨‍💼 <b>На кого:</b> {complaint.target_full_name}\n"
#     admin_text += f"💼 <b>Должность:</b> {complaint.target_position}\n"
#     admin_text += f"🏢 <b>Организация:</b> {complaint.target_organization}\n\n"

#     admin_text += f"📝 <b>Текст жалобы:</b>\n{complaint.complaint_text}\n\n"

#     admin_text += f"🕐 <b>Дата:</b> {complaint.created_at.strftime('%d.%m.%Y %H:%M')}"

#     try:

#         await bot.send_message(
#             chat_id=ADMIN_CHAT_ID,
#             text=admin_text
#         )

#         for media in media_files:
#             if media['file_type'] == 'photo':
#                 await bot.send_photo(
#                     chat_id=ADMIN_CHAT_ID,
#                     photo=media['file_id']
#                 )
#             elif media['file_type'] == 'video':
#                 await bot.send_video(
#                     chat_id=ADMIN_CHAT_ID,
#                     video=media['file_id']
#                 )
#             elif media['file_type'] == 'document':
#                 await bot.send_document(
#                     chat_id=ADMIN_CHAT_ID,
#                     document=media['file_id']
#                 )
#     except Exception as e:
#         print(f"Error sending to admin chat: {e}")
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))

GROUP_ID = str(os.getenv('GROUP_ID', ADMIN_CHAT_ID))

async def send_complaint_to_admin(complaint, media_files: list, lang: str):
    # 🧾 Text message for admin
    admin_text = f"🚨 <b>Yangi shikoyat #{complaint.id}</b>\n\n"

    if complaint.is_anonymous:
        admin_text += "🕵️ <b>Turi:</b> Anonim\n\n"
    else:
        admin_text += f"👤 <b>Yuboruvchi:</b> {complaint.full_name}\n"
        admin_text += f"📱 <b>Telefon:</b> {complaint.phone_number}\n"
        if complaint.telegram_username:
            admin_text += f"💬 <b>Telegram:</b> @{complaint.telegram_username}\n"
        admin_text += "\n"

    admin_text += f"📍 <b>Manzil:</b> {complaint.region_name}, {complaint.district_name}\n"
    if complaint.street_name:
        admin_text += f"🏘 <b>Mahalla:</b> {complaint.street_name}\n"
    admin_text += "\n"

    admin_text += f"👨‍💼 <b>Kimga qarshi:</b> {complaint.target_full_name}\n"
    admin_text += f"💼 <b>Lavozimi:</b> {complaint.target_position}\n"
    admin_text += f"🏢 <b>Tashkilot:</b> {complaint.target_organization}\n\n"
    admin_text += f"📝 <b>Shikoyat matni:</b>\n{complaint.complaint_text}\n\n"
    admin_text += f"🕐 <b>Sana:</b> {complaint.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    # 📄 Create summary PDF
    folder_path = f"/tmp/complaint_{complaint.id}"
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, f"complaint_{complaint.id}_summary.pdf")

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = 'DejaVuSans'
    styles["Heading1"].fontName = 'DejaVuSans'

    story = [
        Paragraph(f"<b>Shikoyat №{complaint.id}</b>", styles["Heading1"]),
        Spacer(1, 12),
        Paragraph(admin_text.replace("\n", "<br/>"), styles["Normal"]),
    ]
    doc.build(story)

    with open(pdf_path, "wb") as f:
        f.write(pdf_buffer.getvalue())

    # 📦 Save original media (without converting)
    for media in media_files:
        try:
            file_info = await bot.get_file(media['file_id'])
            file_path = f"{folder_path}/{media.get('file_name', media['file_id'])}"
            await bot.download_file(file_info.file_path, destination=file_path)
        except Exception as e:
            print(f"Error downloading media: {e}")

    # 🔐 Create ZIP (contains PDF + all attachments)
    zip_path = f"{folder_path}.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, folder_path))

    # 📤 Send summary message + ZIP to admin
    try:
        await bot.send_message(chat_id=GROUP_ID, text=admin_text, parse_mode="HTML")

        zip_file = FSInputFile(zip_path, filename=f"complaint_{complaint.id}.zip")
        await bot.send_document(chat_id=GROUP_ID, document=zip_file,
                                caption=f"📦 Shikoyat #{complaint.id} uchun fayllar")

    except Exception as e:
        print(f"Error sending complaint to admin: {e}")