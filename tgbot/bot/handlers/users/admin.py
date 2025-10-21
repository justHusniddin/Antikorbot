from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta
import csv
import io

from tgbot.models import TelegramUser, Complaint, BroadcastMessage
from tgbot.bot.states.complaint import AdminStates
from tgbot.bot.keyboards.reply import admin_keyboard, main_menu_keyboard
from tgbot.bot.loader import ADMIN_IDS, bot

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Open admin panel"""

    if not is_admin(message.from_user.id):
        await message.answer(f"❌ У вас нет доступа к админ-панели.  ADMIN {ADMIN_IDS} MESSAGE {message.from_user.id}")
        return

    await state.clear()

    await message.answer(
        "🔐 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_keyboard()
    )


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Show complaints statistics"""

    if not is_admin(message.from_user.id):
        return

    # Get statistics
    total_complaints = await sync_to_async(Complaint.objects.count)()
    new_complaints = await sync_to_async(
        Complaint.objects.filter(status='new').count
    )()
    in_progress = await sync_to_async(
        Complaint.objects.filter(status='in_progress').count
    )()
    resolved = await sync_to_async(
        Complaint.objects.filter(status='resolved').count
    )()
    rejected = await sync_to_async(
        Complaint.objects.filter(status='rejected').count
    )()

    # Today's complaints
    today = datetime.now().date()
    today_complaints = await sync_to_async(
        Complaint.objects.filter(created_at__date=today).count
    )()

    # This week's complaints
    week_ago = datetime.now() - timedelta(days=7)
    week_complaints = await sync_to_async(
        Complaint.objects.filter(created_at__gte=week_ago).count
    )()

    # This month's complaints
    month_ago = datetime.now() - timedelta(days=30)
    month_complaints = await sync_to_async(
        Complaint.objects.filter(created_at__gte=month_ago).count
    )()

    # Total users
    total_users = await sync_to_async(TelegramUser.objects.count)()

    # Anonymous vs non-anonymous
    anonymous_count = await sync_to_async(
        Complaint.objects.filter(is_anonymous=True).count
    )()

    stats_text = (
        "📊 <b>Статистика жалоб</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {total_users}\n\n"
        f"📝 <b>Всего жалоб:</b> {total_complaints}\n"
        f"├ 🆕 Новые: {new_complaints}\n"
        f"├ ⏳ В работе: {in_progress}\n"
        f"├ ✅ Решены: {resolved}\n"
        f"└ ❌ Отклонены: {rejected}\n\n"
        f"📅 <b>По периодам:</b>\n"
        f"├ Сегодня: {today_complaints}\n"
        f"├ За неделю: {week_complaints}\n"
        f"└ За месяц: {month_complaints}\n\n"
        f"🕵️ <b>Анонимных:</b> {anonymous_count}\n"
        f"👤 <b>С данными:</b> {total_complaints - anonymous_count}"
    )

    await message.answer(stats_text)


@router.message(F.text == "📥 Экспорт")
async def export_complaints(message: Message):
    """Export complaints to CSV"""

    if not is_admin(message.from_user.id):
        return

    await message.answer("⏳ Генерация CSV файла...")

    try:
        # Get all complaints
        complaints = await sync_to_async(
            lambda: list(Complaint.objects.all().order_by('-created_at'))
        )()

        # Create CSV in memory
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(output)

        # Headers
        writer.writerow([
            'ID',
            'Дата создания',
            'Статус',
            'Анонимно',
            'ФИО заявителя',
            'Телефон',
            'Telegram',
            'Регион',
            'Район',
            'Махалля',
            'ФИО обвиняемого',
            'Должность',
            'Организация',
            'Текст жалобы',
            'Дата решения'
        ])

        # Data rows
        for complaint in complaints:
            writer.writerow([
                complaint.id,
                complaint.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                complaint.get_status_display(),
                'Да' if complaint.is_anonymous else 'Нет',
                complaint.full_name or '-',
                complaint.phone_number or '-',
                f"@{complaint.telegram_username}" if complaint.telegram_username else '-',
                complaint.region_name,
                complaint.district_name,
                complaint.street_name or '-',
                complaint.target_full_name,
                complaint.target_position,
                complaint.target_organization,
                complaint.complaint_text,
                complaint.resolved_at.strftime('%d.%m.%Y %H:%M:%S') if complaint.resolved_at else '-'
            ])

        # Convert to bytes
        output.seek(0)
        file_content = output.getvalue().encode('utf-8')

        # Send file
        from aiogram.types import BufferedInputFile

        filename = f"complaints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file = BufferedInputFile(file_content, filename=filename)

        await message.answer_document(
            document=file,
            caption=f"✅ Экспорт завершен\n\n📊 Всего жалоб: {len(complaints)}"
        )

    except Exception as e:
        print(f"Export error: {e}")
        await message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    """Start broadcast message"""

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n\n"
        "Отправьте /cancel для отмены."
    )

    await state.set_state(AdminStates.broadcast_text)


@router.message(AdminStates.broadcast_text, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    """Cancel broadcast"""

    await message.answer(
        "❌ Рассылка отменена",
        reply_markup=admin_keyboard()
    )
    await state.clear()


@router.message(AdminStates.broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    """Process and send broadcast message"""

    if not is_admin(message.from_user.id):
        return

    broadcast_text = message.text

    await message.answer("⏳ Начинаю рассылку...")

    # Get all users
    users = await sync_to_async(
        lambda: list(TelegramUser.objects.filter(is_blocked=False))
    )()

    sent_count = 0
    failed_count = 0

    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=broadcast_text
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send to {user.telegram_id}: {e}")
            failed_count += 1

            # Mark user as blocked if error is about blocking
            if "blocked" in str(e).lower():
                user.is_blocked = True
                await sync_to_async(user.save)()

    # Save broadcast record
    await sync_to_async(BroadcastMessage.objects.create)(
        text=broadcast_text,
        sent_count=sent_count,
        failed_count=failed_count,
        created_by=message.from_user.username or str(message.from_user.id),
        completed_at=datetime.now()
    )

    # Send result
    result_text = (
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📊 Отправлено: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}\n"
        f"👥 Всего пользователей: {len(users)}"
    )

    await message.answer(
        result_text,
        reply_markup=admin_keyboard()
    )

    await state.clear()


@router.message(F.text == "◀️ Выход")
async def exit_admin_panel(message: Message, state: FSMContext):
    """Exit admin panel"""

    if not is_admin(message.from_user.id):
        return

    await state.clear()

    # Get user language
    user = await sync_to_async(TelegramUser.objects.get)(
        telegram_id=message.from_user.id
    )

    await message.answer(
        "👋 Вы вышли из админ-панели",
        reply_markup=main_menu_keyboard(user.language)
    )
