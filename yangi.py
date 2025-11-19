import sqlite3
import telebot
from datetime import datetime, date
import pandas as pd
from io import BytesIO

# ==================== KONFIGURATSIYA ====================
TOKEN = "8467246612:AAG1DqDcuXVmdxx9e4jRl_6oMlZoxrLS0os"  # @BotFather dan oling
ADMINS = [530240189]  # O'zingizning Telegram ID

bot = telebot.TeleBot(TOKEN)

# ==================== DATABASE ====================
def init_database():
    conn = sqlite3.connect('workers.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            full_name TEXT NOT NULL,
            birth_date TEXT,
            work_type TEXT,
            position TEXT,
            photo_file_id TEXT,
            registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_database()

def get_db_connection():
    conn = sqlite3.connect('workers.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== MA'LUMOTLARNI SAQLASH ====================
user_data = {}

# ==================== ASOSIY MENYU ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🚀 Start', '👨‍💼 Admin paneli')
    
    bot.send_message(
        user_id,
        "🤖 *Xush kelibsiz!*\n\n"
        "Ishchi ma'lumotlarini to'plash botiga xush kelibsiz.\n\n"
        "🚀 *Start* - Ro'yxatdan o'tish\n"
        "👨‍💼 *Admin paneli* - Admin tizimi",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '🚀 Start')
def start_registration(message):
    user_id = message.chat.id
    user_data[user_id] = {'step': 'full_name'}
    
    bot.send_message(
        user_id,
        "👋 *Assalomu alaykum hurmatli Mehmon!*\n\n"
        "Xush kelibsiz! Ma'lumotlaringizni to'ldirishni boshlaymiz.",
        parse_mode="Markdown"
    )
    bot.send_message(user_id, "1️⃣ *Familiya Ism Sharifingizni* kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '👨‍💼 Admin paneli')
def admin_panel_access(message):
    user_id = message.chat.id
    
    if user_id not in ADMINS:
        bot.send_message(user_id, "❌ *Siz admin emassiz!*", parse_mode="Markdown")
        return
    
    # Admin bo'lsa
    admin_panel(message)

# ==================== RO'YXATDAN O'TISH ====================
@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'full_name')
def process_full_name(message):
    user_id = message.chat.id
    user_data[user_id]['full_name'] = message.text
    user_data[user_id]['step'] = 'birth_date'
    bot.send_message(user_id, "2️⃣ *Tug'ilgan kun, oy, yilingizni* kiriting (01.01.1990):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'birth_date')
def process_birth_date(message):
    user_id = message.chat.id
    user_data[user_id]['birth_date'] = message.text
    user_data[user_id]['step'] = 'work_type'
    bot.send_message(user_id, "3️⃣ *Qaysi ish turi* bo'yicha kelgansiz?\n(Masalan: Qurilish, IT, Savdo, ...):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'work_type')
def process_work_type(message):
    user_id = message.chat.id
    user_data[user_id]['work_type'] = message.text
    user_data[user_id]['step'] = 'position'
    bot.send_message(user_id, "4️⃣ *Lavozimingizni* kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'position')
def process_position(message):
    user_id = message.chat.id
    user_data[user_id]['position'] = message.text
    user_data[user_id]['step'] = 'photo'
    bot.send_message(user_id, "5️⃣ *O'zingizning selfi suratingizni* yuboring:", parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'photo')
def process_photo(message):
    user_id = message.chat.id
    photo_file_id = message.photo[-1].file_id
    user_data[user_id]['photo_file_id'] = photo_file_id
    
    # Ma'lumotlarni ko'rsatish va tasdiqlash
    confirmation_text = (
        f"✅ *Ma'lumotlaringizni tekshiring:*\n\n"
        f"👤 *FISh:* {user_data[user_id]['full_name']}\n"
        f"📅 *Tug'ilgan sana:* {user_data[user_id]['birth_date']}\n"
        f"🏢 *Ish turi:* {user_data[user_id]['work_type']}\n"
        f"💼 *Lavozim:* {user_data[user_id]['position']}\n\n"
        f"*Barcha ma'lumotlar to'g'rimi?*"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ Ha", callback_data="confirm_yes"),
        telebot.types.InlineKeyboardButton("❌ Yo'q", callback_data="confirm_no")
    )
    
    bot.send_photo(
        user_id, 
        photo_file_id, 
        caption=confirmation_text, 
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== TASDIQLASH ====================
@bot.callback_query_handler(func=lambda call: call.data in ['confirm_yes', 'confirm_no'])
def handle_confirmation(call):
    user_id = call.message.chat.id
    
    if call.data == 'confirm_yes':
        # Ma'lumotlarni bazaga saqlash
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO workers 
                (tg_id, full_name, birth_date, work_type, position, photo_file_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                user_data[user_id]['full_name'],
                user_data[user_id]['birth_date'],
                user_data[user_id]['work_type'],
                user_data[user_id]['position'],
                user_data[user_id]['photo_file_id']
            ))
            conn.commit()
            
            # Foydalanuvchiga xabar
            success_text = (
                f"🎉 *Tabriklaymiz!*\n\n"
                f"Ma'lumotlaringiz muvaffaqiyatli saqlandi.\n"
                f"Ro'yxatdan o'tish yakunlandi!"
            )
            bot.send_message(user_id, success_text, parse_mode="Markdown")
            
            # Adminlarga bildirishnoma
            for admin_id in ADMINS:
                try:
                    bot.send_photo(
                        admin_id, 
                        user_data[user_id]['photo_file_id'],
                        caption=(
                            f"🆕 *Yangi ro'yxatdan o'tgan!*\n\n"
                            f"👤 {user_data[user_id]['full_name']}\n"
                            f"📅 {user_data[user_id]['birth_date']}\n"
                            f"🏢 {user_data[user_id]['work_type']}\n"
                            f"💼 {user_data[user_id]['position']}\n"
                            f"🆔 {user_id}"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"Admin xabari: {e}")
                    
        except Exception as e:
            bot.send_message(user_id, "❌ Ma'lumotlarni saqlashda xatolik!")
            print(f"Database xatosi: {e}")
        finally:
            conn.close()
            
    else:  # confirm_no
        bot.send_message(user_id, "🔄 Ma'lumotlarni qayta kiritish boshlandi.")
        user_data[user_id] = {'step': 'full_name'}
        bot.send_message(user_id, "1️⃣ *Familiya Ism Sharifingizni* qayta kiriting:", parse_mode="Markdown")
    
    # Callback query ni javobsiz qoldirmaslik
    bot.answer_callback_query(call.id)

# ==================== ADMIN PANELI ====================
def admin_panel(message):
    user_id = message.chat.id
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('👥 Ishchilar Ro\'yxati', '🔍 Qidiruv')
    markup.row('📊 Kunlik Hisobot', '📈 Oylik Hisobot')
    markup.row('🔙 Asosiy menyu')
    
    bot.send_message(
        user_id,
        "👨‍💼 *Admin Panel*\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '🔙 Asosiy menyu')
def back_to_main(message):
    start(message)

@bot.message_handler(func=lambda message: message.text == '👥 Ishchilar Ro\'yxati')
def workers_list(message):
    if message.chat.id not in ADMINS:
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers ORDER BY id DESC")
        workers = cursor.fetchall()
        
        if not workers:
            bot.send_message(message.chat.id, "📭 Hozircha hech qanday ishchi ro'yxatdan o'tmagan")
            return
        
        bot.send_message(message.chat.id, f"👥 *Jami ishchilar: {len(workers)} ta*\n\n", parse_mode="Markdown")
        
        for worker in workers:
            worker_info = (
                f"👤 *{worker['full_name']}*\n"
                f"📅 {worker['birth_date']}\n"
                f"🏢 {worker['work_type']}\n"
                f"💼 {worker['position']}\n"
                f"📅 Ro'yxatdan o'tgan: {worker['registered_date'][:10]}\n"
                f"─" * 20
            )
            
            if worker['photo_file_id']:
                try:
                    bot.send_photo(message.chat.id, worker['photo_file_id'], caption=worker_info, parse_mode="Markdown")
                except:
                    bot.send_message(message.chat.id, worker_info, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, worker_info, parse_mode="Markdown")
                
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")
    finally:
        conn.close()

@bot.message_handler(func=lambda message: message.text == '🔍 Qidiruv')
def search_workers(message):
    if message.chat.id not in ADMINS:
        return
    
    msg = bot.send_message(message.chat.id, "🔍 *Qidirish uchun ism, familiya yoki lavozim kiriting:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    if not message.text:
        bot.send_message(message.chat.id, "❌ Iltimos, qidiruv so'zini kiriting!")
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        search_term = f"%{message.text}%"
        cursor.execute(
            "SELECT * FROM workers WHERE full_name LIKE ? OR work_type LIKE ? OR position LIKE ?",
            (search_term, search_term, search_term)
        )
        results = cursor.fetchall()
        
        if not results:
            bot.send_message(message.chat.id, f"❌ '{message.text}' bo'yicha hech narsa topilmadi")
            return
        
        bot.send_message(message.chat.id, f"🔍 *'{message.text}' bo'yicha {len(results)} ta natija topildi:*\n", parse_mode="Markdown")
        
        for worker in results:
            worker_info = (
                f"👤 *{worker['full_name']}*\n"
                f"📅 {worker['birth_date']}\n"
                f"🏢 {worker['work_type']}\n"
                f"💼 {worker['position']}"
            )
            
            if worker['photo_file_id']:
                try:
                    bot.send_photo(message.chat.id, worker['photo_file_id'], caption=worker_info, parse_mode="Markdown")
                except:
                    bot.send_message(message.chat.id, worker_info, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, worker_info, parse_mode="Markdown")
                
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Qidiruvda xatolik: {e}")
    finally:
        conn.close()

@bot.message_handler(func=lambda message: message.text == '📊 Kunlik Hisobot')
def daily_report(message):
    if message.chat.id not in ADMINS:
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        today = date.today().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM workers WHERE DATE(registered_date) = ?", (today,))
        daily_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM workers")
        total_count = cursor.fetchone()[0]
        
        report_text = (
            f"📊 *Kunlik Hisobot - {today}*\n\n"
            f"📈 Bugun ro'yxatdan o'tganlar: *{daily_count} ta*\n"
            f"📊 Jami ro'yxatdan o'tganlar: *{total_count} ta*\n\n"
            f"🕐 Hisobot vaqti: {datetime.now().strftime('%H:%M')}"
        )
        
        bot.send_message(message.chat.id, report_text, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Hisobotda xatolik: {e}")
    finally:
        conn.close()

@bot.message_handler(func=lambda message: message.text == '📈 Oylik Hisobot')
def monthly_report(message):
    if message.chat.id not in ADMINS:
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        current_month = date.today().strftime('%Y-%m')
        cursor.execute("SELECT * FROM workers WHERE strftime('%Y-%m', registered_date) = ?", (current_month,))
        monthly_workers = cursor.fetchall()
        
        if not monthly_workers:
            bot.send_message(message.chat.id, f"📭 *{current_month}* oyi uchun hech qanday ma'lumot topilmadi")
            return
        
        # Excel fayl yaratish
        df = pd.DataFrame(monthly_workers, columns=['ID', 'TG ID', 'FISh', 'Tugilgan sana', 'Ish turi', 'Lavozim', 'Rasm ID', 'Roʻyxatdan oʻtgan sana'])
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        report_text = (
            f"📈 *Oylik Hisobot - {current_month}*\n\n"
            f"📊 Jami ro'yxatdan o'tganlar: *{len(monthly_workers)} ta*\n"
            f"📥 Excel fayl tayyorlandi"
        )
        
        bot.send_message(message.chat.id, report_text, parse_mode="Markdown")
        bot.send_document(message.chat.id, excel_buffer, visible_file_name=f'hisobot_{current_month}.xlsx')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Oylik hisobotda xatolik: {e}")
    finally:
        conn.close()

# ==================== BOTNI ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    print("🤖 Bot ishga tushmoqda...")
    bot.polling(none_stop=True)
