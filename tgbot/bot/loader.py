import os
import json
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties


BOT_TOKEN = os.getenv('API_TOKEN')

ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMINS', '').split(',') if id.strip()]


def _coerce_chat_id(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith('@'):
        return value
    try:
        return int(value)
    except ValueError:
        return value


_raw_group_id = os.getenv('GROUP_ID')
if _raw_group_id and _raw_group_id.strip():
    GROUP_ID = _coerce_chat_id(_raw_group_id)
elif ADMIN_IDS:
    GROUP_ID = ADMIN_IDS[0]
else:
    GROUP_ID = None

ADMIN_CHAT_ID = GROUP_ID

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class LocationManager:

    def __init__(self, json_path='data/locations.json'):
        self.json_path = json_path
        self.data = self._load_data()
        self.regions = self.data.get('regions', [])
        self.districts = self.data.get('districts', [])
        self.streets = self.data.get('quarters', [])

    def _load_data(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Location file {self.json_path} not found!")
            return {'regions': [], 'districts': [], 'streets': []}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.json_path}: {e}")
            return {'regions': [], 'districts': [], 'streets': []}

    def get_all_regions(self):
        return self.regions

    def get_region_by_id(self, region_id):
        for region in self.regions:
            if region['id'] == region_id:
                return region
        return None

    def get_districts_by_region(self, region_id):
        return [d for d in self.districts if d.get('region_id') == region_id]

    def get_district_by_id(self, district_id):
        for district in self.districts:
            if district['id'] == district_id:
                return district
        return None

    def get_streets_by_district(self, district_id):
        return [s for s in self.streets if s.get('district_id') == district_id]

    def get_street_by_id(self, street_id):
        for street in self.streets:
            if street['id'] == street_id:
                return street
        return None

    def get_full_address(self, region_id, district_id, street_id=None):
        parts = []

        region = self.get_region_by_id(region_id)
        if region:
            parts.append(region['name'])

        district = self.get_district_by_id(district_id)
        if district:
            parts.append(district['name'])

        if street_id:
            street = self.get_street_by_id(street_id)
            if street:
                parts.append(street['name'])

        return ', '.join(parts)


location_manager = LocationManager()


TEXTS = {
    'ru': {
        'welcome': (
            "👋 <b>Добро пожаловать в Антикор Бот!</b>\n\n"
            "Здесь вы можете оставить жалобу на коррупционные действия. "
            "Ваша информация будет рассмотрена уполномоченными органами.\n\n"
            "Выберите язык / Tilni tanlang:"
        ),
        'language_selected': "✅ Язык установлен: Русский",
        'main_menu': "📋 <b>Главное меню</b>\n\nВыберите действие:",
        'submit_complaint': "📝 Подать жалобу",
        'info': "ℹ️ Информация",
        'change_language': "🌐 Сменить язык",
        'anonymity_choice': (
            "🔒 <b>Конфиденциальность</b>\n\n"
            "Хотите подать жалобу анонимно или с указанием ваших данных?"
        ),
        'with_data': "С моими данными ✅",
        'anonymous': "Анонимно 🕵️",
        'enter_full_name': "👤 Введите ваше ФИО:",
        'enter_phone': "📱 Отправьте ваш номер телефона:",
        'send_phone': "Отправить номер телефона 📱",
        'select_region': "🗺 Выберите регион:",
        'select_district': "🏘 Выберите район:",
        'select_mahalla': "📍 Выберите махаллю:",
        'enter_target_name': "👨‍💼 Введите ФИО лица, на которое подается жалоба:",
        'enter_target_position': "💼 Введите должность:",
        'enter_target_org': "🏢 Введите организацию/учреждение:",
        'enter_complaint_text': (
            "📝 <b>Опишите суть жалобы</b>\n\n"
            "Укажите подробно:\n"
            "• Что произошло\n"
            "• Когда произошло\n"
            "• Какая сумма или услуга требовалась\n"
            "• Другие важные детали"
        ),
        'attach_media': (
            "📎 <b>Прикрепление файлов</b>\n\n"
            "Вы можете прикрепить фото, видео или документы.\n"
            "Отправьте файлы или нажмите кнопку для завершения."
        ),
        'finish_media': "Завершить загрузку файлов ✅",
        'skip': "Пропустить ⏭",
        'confirmation': "✅ Подтвердите отправку жалобы:",
        'send': "Отправить ✅",
        'cancel': "Отменить ❌",
        'complaint_sent': "✅ <b>Жалоба успешно отправлена!</b>\n\nВаша жалоба №{} принята и будет рассмотрена.",
        'complaint_cancelled': "❌ Подача жалобы отменена.",
        'back': "◀️ Назад",
        'invalid_phone': "❌ Неверный формат номера телефона. Попробуйте еще раз.",
        'error': "❌ Произошла ошибка. Попробуйте позже.",
    },
    'uz': {
        'welcome': (
            "👋 <b>Antikorrupsiya Botga xush kelibsiz!</b>\n\n"
            "Bu yerda siz korrupsiya harakatlari haqida shikoyat qoldirishingiz mumkin. "
            "Sizning ma'lumotingiz vakolatli organlar tomonidan ko'rib chiqiladi.\n\n"
            "Tilni tanlang / Выберите язык:"
        ),
        'language_selected': "✅ Til o'rnatildi: O'zbekcha",
        'main_menu': "📋 <b>Asosiy menyu</b>\n\nAmalni tanlang:",
        'submit_complaint': "📝 Shikoyat yuborish",
        'info': "ℹ️ Ma'lumot",
        'change_language': "🌐 Tilni o'zgartirish",
        'anonymity_choice': (
            "🔒 <b>Maxfiylik</b>\n\n"
            "Shikoyatni anonim yoki ma'lumotlaringiz bilan yuborishni xohlaysizmi?"
        ),
        'with_data': "Mening ma'lumotlarim bilan ✅",
        'anonymous': "Anonim 🕵️",
        'enter_full_name': "👤 F.I.Sh.ni kiriting:",
        'enter_phone': "📱 Telefon raqamingizni yuboring:",
        'send_phone': "Telefon raqamini yuborish 📱",
        'select_region': "🗺 Viloyatni tanlang:",
        'select_district': "🏘 Tumanni tanlang:",
        'select_mahalla': "📍 MFY ni tanlang:",
        'enter_target_name': "👨‍💼 Shikoyat qilinadigan shaxsning F.I.Sh.ni kiriting:",
        'enter_target_position': "💼 Lavozimni kiriting:",
        'enter_target_org': "🏢 Tashkilot/muassasani kiriting:",
        'enter_complaint_text': (
            "📝 <b>Shikoyat mazmunini tasvirlab bering</b>\n\n"
            "Batafsil ko'rsating:\n"
            "• Nima sodir bo'ldi\n"
            "• Qachon sodir bo'ldi\n"
            "• Qanday summa yoki xizmat talab qilindi\n"
            "• Boshqa muhim tafsilotlar"
        ),
        'attach_media': (
            "📎 <b>Fayllarni biriktirish</b>\n\n"
            "Siz rasm, video yoki hujjatlarni biriktirishingiz mumkin.\n"
            "Fayllarni yuboring yoki tugmani bosing."
        ),
        'finish_media': "Fayllarni yuklashni tugatish ✅",
        'skip': "O'tkazib yuborish ⏭",
        'confirmation': "✅ Shikoyatni yuborishni tasdiqlang:",
        'send': "Yuborish ✅",
        'cancel': "Bekor qilish ❌",
        'complaint_sent': "✅ <b>Shikoyat muvaffaqiyatli yuborildi!</b>\n\nSizning {} raqamli shikoyatingiz qabul qilindi va ko'rib chiqiladi.",
        'complaint_cancelled': "❌ Shikoyat yuborish bekor qilindi.",
        'back': "◀️ Orqaga",
        'invalid_phone': "❌ Telefon raqami formati noto'g'ri. Qaytadan urinib ko'ring.",
        'error': "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.",
    }
}

def get_text(lang, key):
    return TEXTS.get(lang, TEXTS['ru']).get(key, TEXTS['ru'].get(key, ''))
