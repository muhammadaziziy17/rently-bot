from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm
import asyncio
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime
import random
import re
import os
from aiogram.types import Message
from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8235995735:AAGiRw-gULwQzluwKvGYq1e32I1BSg1aCOc"
bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
BOT_USERNAME = "RentlyUzBot"

CHANNEL_ID = "@RentlyUzItems"

# Google Sheets sozlash
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    
    sheet_file = client.open("Rently_Data")
    
    # Users sheet
    try:
        users_sheet = sheet_file.worksheet("Users")
        headers = users_sheet.row_values(1)
        if 'Registered At' not in headers:
            users_sheet.update('A1:F1', [['User ID', 'Full Name', 'Phone', 'Verification Photo', 'Verified', 'Registered At']])
    except:
        users_sheet = sheet_file.add_worksheet("Users", 100, 6)
        users_sheet.update('A1:F1', [['User ID', 'Full Name', 'Phone', 'Verification Photo', 'Verified', 'Registered At']])
    
    # Items sheet
    try:
        items_sheet = sheet_file.worksheet("Items")
        items_sheet.update('A1:K1', [[
            'Item ID', 'User ID', 'Category', 'Item Name', 'Description', 
            'Hourly Price', 'Daily Price', 'Can Take Outside', 'Photos', 'Status', 'Created At'
        ]])
    except:
        items_sheet = sheet_file.add_worksheet("Items", 100, 11)
        items_sheet.update('A1:K1', [[
            'Item ID', 'User ID', 'Category', 'Item Name', 'Description', 
            'Hourly Price', 'Daily Price', 'Can Take Outside', 'Photos', 'Status', 'Created At'
        ]])
    
    return users_sheet, items_sheet

users_sheet, items_sheet = setup_google_sheets()

# Holatlar
class RegisterUser(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_verification_photo = State()
    waiting_for_terms_agreement = State()

class AddItem(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_hourly_price = State()
    waiting_for_daily_price = State()
    waiting_for_can_take_outside = State()
    waiting_for_photos = State()

# Buyum tahrirlash holatlari
class EditItem(StatesGroup):
    choosing_field = State()
    editing_name = State()
    editing_description = State()
    editing_hourly_price = State()
    editing_daily_price = State()
    editing_can_take_outside = State()

# Kategoriyalar
CATEGORIES = [
    "📷 Kamera va Aksessuarlar",
    "🎤 Mikrofon va Audio",
    "🚁 Dronlar",
    "💻 Kompyuter va Texnika",
    "🎮 O'yin Uskunalari",
    "🏠 Uy Jihozlari",
    "🎉 Tadbir Uskunalari",
    "🚗 Transport",
    "📱 Telefon va Planshet",
    "⚡️ Boshqa"
]

# user ni tekshirish verified+registered
def can_user_interact(user_id: str) -> (bool, str):
    """
    Foydalanuvchi bot bilan ishlay oladimi, tekshiradi.
    Returns:
        (True, "") -> foydalanuvchi tasdiqlangan va ishlay oladi
        (False, message) -> foydalanuvchi ishlay olmaydi, message bilan xabar berish
    """
    if not check_user_exists(user_id):
        return False, "❌ Siz hali ro'yxatdan o'tmagansiz. /start orqali ro'yxatdan o'ting."
    
    if not is_user_verified(user_id):
        return False, "⏳ Akkauntingiz hali tasdiqlanmagan. Administratorlar tasdiqlashini kuting."
    
    return True, ""

# Buyumni o'chirish
def delete_item(item_id):
    all_values = items_sheet.get_all_records()

    for i, row in enumerate(all_values, start=2):  # 2-qator = 1-chi data
        if row["Item ID"] == int(item_id):
            items_sheet.delete_rows(i)  # <-- to‘g‘risi shu
            return True

    return False


# Yordamchi funksiyalar
def generate_id():
    return str(random.randint(100000, 999999))

def format_price(price):
    try:
        return "{:,}".format(int(price)).replace(',', '.')
    except:
        return price

def check_user_exists(user_id):
    try:
        all_data = users_sheet.get_all_values()
        for row in all_data[1:]:
            if row and str(row[0]) == str(user_id):
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking user: {e}")
        return False

def is_user_verified(user_id):
    try:
        all_data = users_sheet.get_all_values()
        for row in all_data[1:]:
            if row and str(row[0]) == str(user_id):
                return row[4] == 'TRUE' if len(row) > 4 else False
        return False
    except Exception as e:
        logger.error(f"Error checking verification: {e}")
        return False

def save_user(user_id, full_name, phone, verification_photo):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users_sheet.append_row([
            str(user_id), 
            full_name, 
            phone, 
            verification_photo, 
            "FALSE",
            current_time
        ])
        return True
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        return False

def save_item(item_data):
    try:
        items_sheet.append_row([
            item_data['id'],
            item_data['user_id'],
            item_data['category'],
            item_data['name'],
            item_data['description'],
            item_data['hourly_price'],
            item_data['daily_price'],
            item_data['can_take_outside'],
            ','.join(item_data['photos']),
            'active',
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        return True
    except Exception as e:
        logger.error(f"Error saving item: {e}")
        return False

def get_user_items(user_id):
    """Foydalanuvchi buyumlarini olish"""
    try:
        all_data = items_sheet.get_all_values()
        user_items = []
        for row in all_data[1:]:
            if row and str(row[1]) == str(user_id) and row[9] == 'active':
                user_items.append({
                    'id': row[0],
                    'name': row[3],
                    'category': row[2],
                    'description': row[4],
                    'hourly_price': row[5],
                    'daily_price': row[6],
                    'can_take_outside': row[7],
                    'photos': row[8].split(',') if row[8] else []
                })
        return user_items
    except Exception as e:
        logger.error(f"Error getting user items: {e}")
        return []


def get_item_by_id(item_id: str):
    try:
        all_data = items_sheet.get_all_values()
        for row in all_data[1:]:
            if row and str(row[0]) == str(item_id):
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'category': row[2],
                    'name': row[3],
                    'description': row[4],
                    'hourly_price': row[5],
                    'daily_price': row[6],
                    'can_take_outside': row[7],
                    'photos': row[8].split(',') if row[8] else []
                }
        return None
    except Exception as e:
        logger.error(f"Error getting item by ID: {e}")
        return None

def get_user_by_id(user_id: str):
    try:
        all_data = users_sheet.get_all_values()
        for row in all_data[1:]:
            if row and str(row[0]) == str(user_id):
                return {'full_name': row[1], 'phone': row[2] if len(row) > 2 else ''}
        return {}
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return {}

async def send_to_channel(item_data, user_data):
    try:
        # Caption tayyorlash
        caption = (
            f"#{item_data['category'].replace(' ', '')}\n"  # Kategoriyani hashtag bilan
            f"[ID: {item_data['id']}](https://t.me/{BOT_USERNAME}?start=item_{item_data['id']})\n\n"  # ID link
            f"🏷️ Nomi: {item_data['name']}\n"
            f"📝 Tavsif: {item_data['description']}\n"
            f"💰 Soatlik: {format_price(item_data['hourly_price'])} so'm\n"
            f"💰 Kunlik: {format_price(item_data['daily_price'])} so'm\n"
            f"🏠 Chetga olish: {'✅ Ha' if item_data['can_take_outside'] == 'ha' else '❌ Yo\'q'}\n"
            f"👤 Egasi: {user_data['full_name']}\n"
            f"📞 Telefon: {user_data.get('phone', '')}\n"
        )
        
        # Media yuborish
        if item_data['photos']:
            media = []
            for i, photo in enumerate(item_data['photos']):
                if i == 0:
                    media.append(types.InputMediaPhoto(media=photo, caption=caption, parse_mode="Markdown"))
                else:
                    media.append(types.InputMediaPhoto(media=photo))
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")

# PDF Yaratish funksiyalari
def create_terms_pdf(user_full_name):
    """Foydalanish shartlari PDF yaratish"""
    try:
        filename = f"terms_{user_full_name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.pdf"
        
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4
        
        # Sarlavha
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height - 3*cm, "📝 Rently - Foydalanish Shartlari")
        
        # Foydalanuvchi ma'lumotlari
        c.setFont("Helvetica", 12)
        c.drawString(2*cm, height - 4.5*cm, f"Foydalanuvchi: {user_full_name}")
        c.drawString(2*cm, height - 5*cm, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Kontent
        y_position = height - 7*cm
        content = [
            "1. UMUMIY QOIDALAR",
            "Rently platformasi orqali foydalanuvchilar turli buyumlarni ijaraga olish",
            "va ijaraga berish imkoniyatiga ega. Platformadan foydalanish quyidagi",
            "shartlarga bo'ysunadi.",
            "",
            "2. FOYDALANUVCHI MAJBURIYATLARI",
            "• To'g'ri va aniq ma'lumotlarni taqdim etish",
            "• Faqat qonuniy buyumlarni ijaraga qo'yish", 
            "• Buyumlarni to'g'ri tavsiflash va rasmlash",
            "• Vaqtida to'lovlarni amalga oshirish",
            "• Buyumlarni belgilangan muddatda qaytarish",
            "",
            "3. MAXFIYLIK SIYOSATI",
            "• Shaxsiy ma'lumotlaringiz himoya qilinadi",
            "• Telefon raqamingiz faqat aloqa uchun ishlatiladi",
            "• Ma'lumotlaringiz uchinji shaxslarga sotilmaydi",
            "• Faqat zarur ma'lumotlar so'raladi",
            "",
            "4. TO'LOVLAR",
            "• Platforma har bir tranzaksiyadan 5% komissiya oladi",
            "• To'lovlar xavfsiz holda amalga oshiriladi",
            "• Naqd va onlayn to'lov qabul qilinadi",
            "",
            "5. JAVOBGARLIK", 
            "• Foydalanuvchi o'z buyumlari uchun javobgar",
            "• Platforma faqat vositachi vazifasini bajaradi",
            "• Noto'g'ri ma'lumot berish akkaunt blokirovkasi bilan yakunlanadi",
            "",
            "6. ALOQA",
            "• Muammo bo'lsa: @rently_support",
            "• Shikoyatlar: @rently_admin",
            "• Takliflar: @rently_feedback"
        ]
        
        c.setFont("Helvetica", 10)
        for line in content:
            if y_position < 2*cm:
                c.showPage()
                y_position = height - 3*cm
                c.setFont("Helvetica", 10)
            
            if line.startswith(tuple("123456")) and not line.startswith("•"):
                c.setFont("Helvetica-Bold", 11)
                c.drawString(2*cm, y_position, line)
                c.setFont("Helvetica", 10)
            else:
                c.drawString(2.5*cm, y_position, line)
            
            y_position -= 0.5*cm
        
        # Rozilik qismi
        y_position -= 0.5*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2*cm, y_position, "ROZILIK:")
        y_position -= 0.5*cm
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, y_position, f"Men, {user_full_name}, yuqoridagi barcha shart va")
        y_position -= 0.5*cm
        c.drawString(2*cm, y_position, "sharoitlarga to'liq rozilik bildiraman.")
        
        # Imzo
        y_position -= 1.5*cm
        c.drawString(2*cm, y_position, "Imzo: ___________________")
        y_position -= 0.5*cm
        c.drawString(2*cm, y_position, "Sana: ___________________")
        
        c.save()
        return filename
        
    except Exception as e:
        logger.error(f"PDF yaratishda xatolik: {e}")
        return None

# Asosiy menyu ko'rsatish
async def show_main_menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📦 Buyum qo'shish"), types.KeyboardButton(text="📋 Mening buyumlarim")],
            [types.KeyboardButton(text="🔍 Buyum qidirish"), types.KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👋 Xush kelibsiz, {message.from_user.full_name}!\n\n"
        "Quyidagi menyudan kerakli amalni tanlang:",
        reply_markup=keyboard
    )

# Buyum qo'shish boshlash
@dp.message(F.text == "📦 Buyum qo'shish")
async def add_item_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if not is_user_verified(user_id):
        await message.answer("❌ Buyum qo'shish uchun akkauntingiz tasdiqlangan bo'lishi kerak!")
        return
    
    # Kategoriyalar keyboard
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=CATEGORIES[0]), types.KeyboardButton(text=CATEGORIES[1])],
            [types.KeyboardButton(text=CATEGORIES[2]), types.KeyboardButton(text=CATEGORIES[3])],
            [types.KeyboardButton(text=CATEGORIES[4]), types.KeyboardButton(text=CATEGORIES[5])],
            [types.KeyboardButton(text=CATEGORIES[6]), types.KeyboardButton(text=CATEGORIES[7])],
            [types.KeyboardButton(text=CATEGORIES[8]), types.KeyboardButton(text=CATEGORIES[9])]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "📦 Buyum qo'shish boshlandi!\n\n"
        "Avval kategoriyani tanlang:",
        reply_markup=keyboard
    )
    
    await state.set_state(AddItem.waiting_for_category)
# bron qlish
@dp.callback_query(F.data.startswith("book_"))
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("book_", "")
    item = get_item_by_id(item_id)
    if not item:
        await callback.message.answer("❌ Bu buyum topilmadi")
        return
    
    await callback.message.answer(f"🟢 {item['name']} buyumini bron qilishni boshlaymiz...")
    # Bu yerda bron jarayonini boshlash mumkin


# Mening buyumlarim

# Mening buyumlarimda inline tugmalar bilan tanlash
@dp.message(F.text == "📋 Mening buyumlarim")
async def show_my_items(message: types.Message):
    user_id = str(message.from_user.id)
    items = get_user_items(user_id)

    if not items:
        await message.answer("📭 Siz hali hech qanday buyum qo'shmagansiz")
        return

    for item in items:
        caption = (
            f"🏷️ Nomi: {item['name']}\n"
            f"📂 Kategoriya: {item['category']}\n"
            f"📝 Tavsif: {item['description']}\n"
            f"💰 Soatlik: {format_price(item['hourly_price'])} so'm\n"
            f"💰 Kunlik: {format_price(item['daily_price'])} so'm\n"
            f"🏠 Chetga olish: {'✅ Ha' if item['can_take_outside'] == 'ha' else '❌ Yo\'q'}\n"
            f"🆔 ID: {item['id']}"
        )

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text="❌ O'chirish", callback_data=f"delete_{item['id']}")]
        ])

        await message.answer(caption, reply_markup=keyboard)

# Callback: o'chirish
@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_item_callback(callback: types.CallbackQuery):
    item_id = callback.data.replace("delete_", "")
    item = get_item_by_id(item_id)
    user_id = str(callback.from_user.id)

    if not item or item['user_id'] != user_id:
        await callback.message.answer("❌ Bu buyumni o'chirish mumkin emas!")
        return

    # Buyumni o'chirish
    delete_item(item_id)  # Bu funksiya bazadan o'chiradi
    await callback.message.edit_text("✅ Buyum muvaffaqiyatli o'chirildi!")

# Callback: tahrirlash
@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_item_callback(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("edit_", "")
    item = get_item_by_id(item_id)
    user_id = str(callback.from_user.id)

    if not item or item['user_id'] != user_id:
        await callback.message.answer("❌ Bu buyumni tahrirlash mumkin emas!")
        return

    await state.update_data(item_id=item_id)
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Nomi", callback_data="field_name")],
        [types.InlineKeyboardButton(text="Tavsif", callback_data="field_description")],
        [types.InlineKeyboardButton(text="Soatlik narx", callback_data="field_hourly")],
        [types.InlineKeyboardButton(text="Kunlik narx", callback_data="field_daily")],
        [types.InlineKeyboardButton(text="Chetga olish", callback_data="field_can_take_outside")]
    ])
    await callback.message.answer("✏️ Qaysi maydonni tahrirlashni xohlaysiz?", reply_markup=keyboard)
    await state.set_state(EditItem.choosing_field)

# Callback: qaysi maydon tahrir qilinadi
@dp.callback_query(EditItem.choosing_field)
async def choose_field(callback: types.CallbackQuery, state: FSMContext):
    field_map = {
        "field_name": EditItem.editing_name,
        "field_description": EditItem.editing_description,
        "field_hourly": EditItem.editing_hourly_price,
        "field_daily": EditItem.editing_daily_price,
        "field_can_take_outside": EditItem.editing_can_take_outside
    }

    field_state = field_map.get(callback.data)
    if not field_state:
        await callback.message.answer("❌ Noma'lum maydon!")
        return

    await callback.message.answer("✏️ Yangi qiymatni kiriting:")
    await state.set_state(field_state)

# Text handlerlar har bir maydon uchun
@dp.message(EditItem.editing_name)
async def edit_name(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    item_id = data.get('item_id')

    update_item_field(item_id, 'name', new_value)  # Bazaga yangilash
    await message.answer("✅ Buyum nomi yangilandi!")
    await state.clear()

@dp.message(EditItem.editing_description)
async def edit_description(message: types.Message, state: FSMContext):
    new_value = message.text.strip()
    data = await state.get_data()
    item_id = data.get('item_id')

    update_item_field(item_id, 'description', new_value)
    await message.answer("✅ Tavsif yangilandi!")
    await state.clear()

@dp.message(EditItem.editing_hourly_price)
async def edit_hourly_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ To'g'ri raqam kiriting!")
        return

    data = await state.get_data()
    item_id = data.get('item_id')
    update_item_field(item_id, 'hourly_price', message.text)
    await message.answer("✅ Soatlik narx yangilandi!")
    await state.clear()

@dp.message(EditItem.editing_daily_price)
async def edit_daily_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ To'g'ri raqam kiriting!")
        return

    data = await state.get_data()
    item_id = data.get('item_id')
    update_item_field(item_id, 'daily_price', message.text)
    await message.answer("✅ Kunlik narx yangilandi!")
    await state.clear()

@dp.message(EditItem.editing_can_take_outside)
async def edit_can_take_outside(message: types.Message, state: FSMContext):
    if message.text.lower() not in ["ha", "yo'q"]:
        await message.answer("❌ Faqat 'Ha' yoki 'Yo'q' kiriting!")
        return

    data = await state.get_data()
    item_id = data.get('item_id')
    update_item_field(item_id, 'can_take_outside', message.text.lower())
    await message.answer("✅ Chetga olish maydoni yangilandi!")
    await state.clear()

# Qidirish boshlash
@dp.message(F.text == "🔍 Buyum qidirish")
async def search_items_start(message: types.Message):
    await message.answer(
        "🔍 Qidirish bo'limi tez orada ishga tushadi...\n"
        "Hozircha 'Mening buyumlarim' bo'limidan foydalaning"
    )

# Yordam
@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    await message.answer(
        "🤖 Rently Bot - Buyumlar ijara platformasi\n\n"
        "📦 Buyum qo'shish - Yangi buyum qo'shing\n"
        "📋 Mening buyumlarim - Sizning buyumlaringiz ro'yxati\n"
        "🔍 Buyum qidirish - Boshqa foydalanuvchilar buyumlarini qidirish\n\n"
        "Botdan foydalanish uchun:\n"
        "1. Ro'yxatdan o'ting va tasdiqlanishni kuting\n"
        "2. 'Buyum qo'shish' tugmasini bosing\n"
        "3. Kategoriya, nom, tavsif, narx va rasmlarni kiriting\n"
        "4. Buyum kanalga joylanadi!\n\n"
        "Aloqa: @rently_support"
    )

# Asosiy handerlar
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext, command: Command):
    await state.clear()
    user_id = str(message.from_user.id)
    args = command.args  # /start item_<ID>

    # Agar /start item_<ID> bo'lsa
    if args and args.startswith("item_"):
        # Avvalo foydalanuvchi ro'yxatdan o'tganmi va tasdiqlanganmi tekshirish
        can_interact, reason = can_user_interact(user_id)
        if not can_interact:
            await message.answer(reason)  # "❌ Siz hali ro'yxatdan o'tmagansiz. /start orqali ro'yxatdan o'ting."
            return

        item_id = args.replace("item_", "")
        item = get_item_by_id(item_id)
        if item:
            if item['user_id'] == user_id:
                await message.answer("⚠️ Bu sizning buyumingiz. O'z buyumingizni bron qila olmaysiz!")
            else:
                user_data = get_user_by_id(item['user_id'])
                caption = (
                    f"🏷️ Nomi: {item['name']}\n"
                    f"📂 Kategoriya: {item['category']}\n"
                    f"📝 Tavsif: {item['description']}\n"
                    f"💰 Soatlik: {format_price(item['hourly_price'])} so'm\n"
                    f"💰 Kunlik: {format_price(item['daily_price'])} so'm\n"
                    f"🏠 Chetga olish: {'✅ Ha' if item['can_take_outside']=='ha' else '❌ Yo\'q'}\n"
                    f"👤 Egasi: {user_data.get('full_name','')}\n"
                    f"📞 Telefon: {user_data.get('phone','')}"
                )
                await message.answer(caption)
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="🟢 Bron qilish", callback_data=f"book_{item_id}")]
                ])
                await message.answer("Buyumni bron qilish uchun:", reply_markup=keyboard)
        else:
            await message.answer("❌ Bunday buyum topilmadi!")
        return

    # Agar /start faqat oddiy start bo'lsa -> register jarayonini boshlash
    if check_user_exists(user_id):
        if is_user_verified(user_id):
            await show_main_menu(message)
        else:
            await message.answer("⏳ Akkauntingiz hali tasdiqlanmagan. Administratorlar tasdiqlashini kuting.")
    else:
        await message.answer(
            "👋 Assalomu alaykum! Rently botiga xush kelibsiz!\n\n"
            "Iltimos, ism va familiyangizni kiriting:"
        )
        await state.set_state(RegisterUser.waiting_for_full_name)


    # Odatiy ish: yangi foydalanuvchi yoki asosiy menyu
    if check_user_exists(user_id):
        if is_user_verified(user_id):
            await show_main_menu(message)
        else:
            await message.answer("⏳ Akkauntingiz hali tasdiqlanmagan. Administratorlar tasdiqlashini kuting.")
    else:
        await message.answer(
            "👋 Assalomu alaykum! Rently botiga xush kelibsiz!\n\n"
            "Iltimos, ism va familiyangizni kiriting:"
        )
        await state.set_state(RegisterUser.waiting_for_full_name)


@dp.message(RegisterUser.waiting_for_full_name, F.text)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("❌ Iltimos, to'liq ism va familiyangizni kiriting:")
        return
    
    await state.update_data(full_name=full_name)
    await message.answer(
        "📞 Iltimos, telefon raqamingizni kiriting:\n"
        "Masalan: +998901234567"
    )
    await state.set_state(RegisterUser.waiting_for_phone)

@dp.message(RegisterUser.waiting_for_phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    if not re.match(r'^\+998\d{9}$', phone):
        await message.answer("❌ Iltimos, to'g'ri telefon raqamini kiriting:\nMasalan: +998901234567")
        return
    
    await state.update_data(phone=phone)
    await message.answer(
        "🆔 Akkauntni tasdiqlash uchun pasport yoki ID karta rasmini yuboring:"
    )
    await state.set_state(RegisterUser.waiting_for_verification_photo)

@dp.message(RegisterUser.waiting_for_verification_photo, F.photo)
async def process_verification_photo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    photo_id = message.photo[-1].file_id
    
    data = await state.get_data()
    phone = data.get('phone', '')
    full_name = data.get('full_name', '')
    
    if save_user(user_id, full_name, phone, photo_id):
        await message.answer("📄 Foydalanish shartlari tayyorlanmoqda...")
        
        try:
            terms_pdf = create_terms_pdf(full_name)
            
            if terms_pdf:
                with open(terms_pdf, 'rb') as terms_file:
                    await message.answer_document(
                        document=types.FSInputFile(terms_pdf),
                        caption="📝 Foydalanish shartlari - Iltimos, o'qib chiqing"
                    )
                
                os.remove(terms_pdf)
                
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="✅ Barcha shartlarga roziman", callback_data="agree_terms"),
                    types.InlineKeyboardButton(text="❌ Rad etaman", callback_data="reject_terms")
                ]])
                
                await message.answer(
                    "📋 Yuqoridagi hujjatlarni o'qib chiqdingizmi va ularga rozimisiz?\n\n"
                    "Rozilik bildirish uchun quyidagi tugmalardan foydalaning:",
                    reply_markup=keyboard
                )
                
                await state.set_state(RegisterUser.waiting_for_terms_agreement)
                
            else:
                await message.answer("❌ Hujjatlar yaratishda xatolik. Iltimos, qayta urinib ko'ring.")
                await state.clear()
                
        except Exception as e:
            logger.error(f"PDF yuborishda xatolik: {e}")
            await message.answer("❌ Hujjatlar yuborishda xatolik. Iltimos, qayta urinib ko'ring.")
            await state.clear()
            
    else:
        await message.answer("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()

@dp.callback_query(RegisterUser.waiting_for_terms_agreement, F.data == "agree_terms")
async def process_terms_agreement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz va shartlarga rozilik bildirdingiz!\n\n"
        "⏳ Akkauntingiz administrator tomonidan tekshirilmoqda. "
        "Tasdiqlangandan so'ng sizga xabar beramiz.\n\n"
        "Tasdiqlash odatda 24 soat ichida amalga oshiriladi."
    )
    await state.clear()

@dp.callback_query(RegisterUser.waiting_for_terms_agreement, F.data == "reject_terms")
async def process_terms_rejection(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Foydalanish shartlariga rozilik bildirmaganingiz uchun botdan foydalana olmaysiz.\n\n"
        "Agar fikringiz o'zgarsa, /start buyrug'ini bosing."
    )
    await state.clear()

# Buyum qo'shish handerlar
@dp.message(AddItem.waiting_for_category, F.text)
async def process_category(message: types.Message, state: FSMContext):
    if message.text not in CATEGORIES:
        await message.answer("❌ Iltimos, ro'yxatdagi kategoriyalardan birini tanlang:")
        return
    
    await state.update_data(category=message.text)
    
    # Keyboardni olib tashlash
    remove_keyboard = types.ReplyKeyboardRemove()
    
    await message.answer(
        "✏️ Endi buyum nomini kiriting:\n"
        "Masalan: Canon EOS 5D Mark IV, PlayStation 5, Samsung Galaxy S23",
        reply_markup=remove_keyboard
    )
    await state.set_state(AddItem.waiting_for_name)

@dp.message(AddItem.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Iltimos, buyum nomini kiriting (kamida 2 belgi):")
        return
    
    await state.update_data(name=message.text.strip())
    await message.answer(
        "📝 Buyum haqida batafsil ma'lumot kiriting:\n"
        "Masalan: Holati a'lo, barcha aksessuarlari bor, 6 oy ishlatilgan, quti va qo'llanma bor"
    )
    await state.set_state(AddItem.waiting_for_description)

@dp.message(AddItem.waiting_for_description, F.text)
async def process_description(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 10:
        await message.answer("❌ Iltimos, kamida 10 ta belgidan iborat tavsif kiriting:")
        return
    
    await state.update_data(description=message.text.strip())
    await message.answer(
        "💰 Soatlik narxni kiriting (so'mda):\n"
        "Masalan: 50000, 100000, 25000"
    )
    await state.set_state(AddItem.waiting_for_hourly_price)

@dp.message(AddItem.waiting_for_hourly_price, F.text)
async def process_hourly_price(message: types.Message, state: FSMContext):
    price = message.text.strip()
    if not price.isdigit() or int(price) <= 0:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting (faqat sonlar):")
        return
    
    await state.update_data(hourly_price=price)
    await message.answer(
        "💰 Kunlik narxni kiriting (so'mda):\n"
        "Masalan: 200000, 500000, 100000"
    )
    await state.set_state(AddItem.waiting_for_daily_price)

@dp.message(AddItem.waiting_for_daily_price, F.text)
async def process_daily_price(message: types.Message, state: FSMContext):
    price = message.text.strip()
    if not price.isdigit() or int(price) <= 0:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting (faqat sonlar):")
        return
    
    await state.update_data(daily_price=price)
    
    # Chetga olish mumkinmi?
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Ha"), types.KeyboardButton(text="Yo'q")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "🏠 Buyumni chetga (uyingizdan tashqariga) olib chiqib ketish mumkinmi?",
        reply_markup=keyboard
    )
    await state.set_state(AddItem.waiting_for_can_take_outside)

@dp.message(AddItem.waiting_for_can_take_outside, F.text)
async def process_can_take_outside(message: types.Message, state: FSMContext):
    if message.text not in ["Ha", "Yo'q"]:
        await message.answer("❌ Iltimos, 'Ha' yoki 'Yo'q' tugmalaridan birini bosing:")
        return
    
    await state.update_data(can_take_outside=message.text.lower())
    
    # Keyboardni olib tashlash
    remove_keyboard = types.ReplyKeyboardRemove()
    
    await message.answer(
        "🖼️ Endi buyum rasmlarini yuboring (1-3 ta rasm):\n\n"
        "📎 Rasm yuborish uchun: Paperclip (📎) tugmasini bosing va rasm tanlang\n"
        "✅ Kamida 1 ta, ko'pi bilan 3 ta rasm yuborishingiz mumkin\n"
        "🔚 Rasmlarni yuborib bo'lgach, /done deb yozing",
        reply_markup=remove_keyboard
    )
    await state.set_state(AddItem.waiting_for_photos)

@dp.message(AddItem.waiting_for_photos, F.photo)
async def process_photos(message: types.Message, state: FSMContext):
    # Hozirgi ma'lumotlarni olish
    data = await state.get_data()
    photos = data.get('photos', [])
    
    # Yangi rasmni qo'shish
    photo_id = message.photo[-1].file_id
    photos.append(photo_id)
    
    # Ma'lumotlarni yangilash
    await state.update_data(photos=photos)
    
    photos_count = len(photos)
    
    if photos_count >= 3:
        # 3 ta rasm yetdi, avtomatik yakunlash
        await finish_adding_item(message, state)
    else:
        await message.answer(f"✅ Rasm qo'shildi ({photos_count}/3)\nYana rasm yuboring yoki /done deb yozing")

@dp.message(AddItem.waiting_for_photos, Command("done"))
async def process_done_command(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    
    if len(photos) == 0:
        await message.answer("❌ Kamida 1 ta rasm yuborishingiz kerak!")
        return
    
    await finish_adding_item(message, state)

async def finish_adding_item(message: types.Message, state: FSMContext):
    # Barcha ma'lumotlarni olish
    data = await state.get_data()
    user_id = str(message.from_user.id)
    
    # User ma'lumotlarini olish
    user_info = users_sheet.get_all_values()
    user_data = {}
    for row in user_info[1:]:
        if row and str(row[0]) == user_id:
            user_data = {
                'full_name': row[1],
                'phone': row[2] if len(row) > 2 else ""
            }
            break
    
    # Buyum ma'lumotlarini tayyorlash
    item_data = {
        'id': generate_id(),
        'user_id': user_id,
        'category': data['category'],
        'name': data['name'],
        'description': data['description'],
        'hourly_price': data['hourly_price'],
        'daily_price': data['daily_price'],
        'can_take_outside': data['can_take_outside'],
        'photos': data.get('photos', [])
    }
    
    # Bazaga saqlash
    if save_item(item_data):
        # Kanalga yuborish
        await send_to_channel(item_data, user_data)
        
        # Foydalanuvchaga tasdiqlash
        photos_count = len(data.get('photos', []))
        await message.answer(
            f"✅ Buyum muvaffaqiyatli qo'shildi!\n\n"
            f"🏷️ Nomi: {data['name']}\n"
            f"📂 Kategoriya: {data['category']}\n"
            f"💰 Soatlik: {format_price(data['hourly_price'])} so'm\n"
            f"💰 Kunlik: {format_price(data['daily_price'])} so'm\n"
            f"🏠 Chetga olish: {'✅ Ha' if data['can_take_outside'] == 'ha' else '❌ Yo\'q'}\n"
            f"🖼️ Rasmlar: {photos_count} ta\n\n"
            f"📢 Buyum kanalga joylandi: {CHANNEL_ID}\n\n"
            f"📋 Boshqa buyum qo'shish uchun '📦 Buyum qo'shish' tugmasini bosing"
        )
    else:
        await message.answer("❌ Buyum saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    
    await state.clear()
    await show_main_menu(message)

# Boshqa xabarlar
@dp.message(F.text == "Asosiy menyu")
async def handle_main_menu_text(message: types.Message):
    await show_main_menu(message)

@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Iltimos, menyudan kerakli amalni tanlang!")
    await show_main_menu(message)

# Botni ishga tushirish
async def main():
    print("✅ Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())