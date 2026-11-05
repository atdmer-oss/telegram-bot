import telebot
from telebot import types
import json
import os
import time

TOKEN = "9008137062:AAFl94aQDnbbJsKY9ZSaGoqvYJugD6kdgCc"
ADMINS = [8012898014, 8276762624]
DATA_FILE = "subjects_data.json"

bot = telebot.TeleBot(TOKEN, threaded=False)

DEFAULT_SUBJECTS = [
    "📅 جدول الامتحانات والتبليغات",
    "عربي", "إنجليزي", "علم التفكير", "حاسوب",
    "نظرية الزمر", "جرائم حزب البعث", "التفاضل والتكامل المتقدم",
    "المعادلات التفاضلية", "الهندسة", "القيادة والادارة التربوية",
    "المناهج والكتب المدرسية"
]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                formatted_data = {}
                for sub, content in data.items():
                    if isinstance(content, list):
                        formatted_data[sub] = {"files": content, "exams": []}
                    elif isinstance(content, dict):
                        formatted_data[sub] = {"files": content.get("files", []), "exams": content.get("exams", [])}
                return formatted_data
        except Exception as e:
            print(f"Load Error: {e}")
    return {sub: {"files": [], "exams": []} for sub in DEFAULT_SUBJECTS}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()
user_states = {}

def get_subjects_list():
    return list(db.keys())

def get_main_keyboard(user_id):
    subjects = get_subjects_list()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(sub, callback_data=f"sub_{i}") for i, sub in enumerate(subjects)]
    markup.add(*buttons)
    if user_id in ADMINS:
        markup.add(types.InlineKeyboardButton("⚙️ إدارة الخانات (إضافة / حذف)", callback_data="manage_subjects"))
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    try:
        bot.send_message(
            message.chat.id,
            "📚 **مرحباً بك في بوت المكتبة الدراسية**\nاختر الخانة أو المادة لتصفح المحتوى:",
            reply_markup=get_main_keyboard(message.from_user.id),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error: {e}")

# واجهة إدارة الخانات للمشرفين
@bot.callback_query_handler(func=lambda call: call.data == "manage_subjects")
def manage_subjects_menu(call):
    if call.from_user.id not in ADMINS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ إضافة خانة جديدة", callback_data="admin_add_sub"))
    markup.add(types.InlineKeyboardButton("❌ حذف خانة حالية", callback_data="admin_del_sub_menu"))
    markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu"))

    bot.edit_message_text("⚙️ **قائمة إدارة الخانات والمواد:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# أمر إضافة خانة جديدة
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_sub")
def start_add_subject(call):
    if call.from_user.id not in ADMINS:
        return
    user_states[call.from_user.id] = {"step": "wait_new_sub_name"}
    bot.send_message(call.message.chat.id, "✏️ اكتب الآن **اسم الخانة الجديدة** التي تريد إضافتها:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("step") == "wait_new_sub_name")
def receive_new_subject_name(message):
    if message.from_user.id not in ADMINS:
        return
    user_states.pop(message.from_user.id, None)
    new_sub = message.text.strip()
    if new_sub in db:
        bot.reply_to(message, "⚠️ هذه الخانة موجودة بالفعل!")
        return
    db[new_sub] = {"files": [], "exams": []}
    save_data(db)
    bot.reply_to(message, f"✅ تم إضافة خانة **[{new_sub}]** بنجاح!", parse_mode="Markdown")

# أمر حذف خانة
@bot.callback_query_handler(func=lambda call: call.data == "admin_del_sub_menu")
def delete_subject_menu(call):
    if call.from_user.id not in ADMINS:
        return
    subjects = get_subjects_list()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, sub in enumerate(subjects):
        markup.add(types.InlineKeyboardButton(f"❌ حذف خانة: {sub}", callback_data=f"confirm_del_sub_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع لإدارة الخانات", callback_data="manage_subjects"))
    bot.edit_message_text("⚠️ **اختر الخانة التي ترغب بحذفها:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_sub_"))
def confirm_delete_subject(call):
    if call.from_user.id not in ADMINS:
        return
    sub_idx = int(call.data.split("_")[3])
    subjects = get_subjects_list()
    if sub_idx < len(subjects):
        sub_name = subjects[sub_idx]
        del db[sub_name]
        save_data(db)
        bot.answer_callback_query(call.id, f"تم حذف خانة {sub_name}")
    delete_subject_menu(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def show_subject_sections(call):
    try:
        sub_index = int(call.data.split("_")[1])
        subjects = get_subjects_list()
        if sub_index >= len(subjects):
            bot.answer_callback_query(call.id, "الخانة غير موجودة.")
            return
        sub_name = subjects[sub_index]

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📂 الملخصات والملازم / التبليغات", callback_data=f"sec_{sub_index}_files"))
        markup.add(types.InlineKeyboardButton("📝 الامتحانات والأسئلة", callback_data=f"sec_{sub_index}_exams"))
        markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu"))

        msg_text = f"📖 **الخانة: {sub_name}**\nاختر القسم المطلوب:"
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sec_"))
def show_section_files(call):
    try:
        _, sub_idx, category = call.data.split("_")
        sub_index = int(sub_idx)
        subjects = get_subjects_list()
        if sub_index >= len(subjects):
            return
        sub_name = subjects[sub_index]
        is_admin = call.from_user.id in ADMINS

        sec_title = "📂 الملخصات والملازم / التبليغات" if category == "files" else "📝 الامتحانات والأسئلة"
        items = db.get(sub_name, {}).get(category, [])

        markup = types.InlineKeyboardMarkup(row_width=1)

        if items:
            for item_idx, item_info in enumerate(items):
                btn_icon = "📄" if category == "files" else "❓"
                markup.add(types.InlineKeyboardButton(f"{btn_icon} {item_info['name']}", callback_data=f"get_{sub_index}_{category}_{item_idx}"))
                if is_admin:
                    markup.add(types.InlineKeyboardButton(f"❌ حذف: {item_info['name']}", callback_data=f"del_{sub_index}_{category}_{item_idx}"))

        if is_admin:
            markup.add(types.InlineKeyboardButton("➕ إضافة ملف/جدول لهذا القسم", callback_data=f"add_{sub_index}_{category}"))

        markup.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data=f"sub_{sub_index}"))

        msg_text = f"📖 **الخانة: {sub_name}**\n📌 **قسم: {sec_title}**\nعدد المحتويات المتاحة: {len(items)}"
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main(call):
    try:
        bot.edit_message_text(
            "📚 **اختر الخانة أو المادة:**",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_keyboard(call.from_user.id),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def send_file(call):
    try:
        _, sub_idx, category, item_idx = call.data.split("_")
        subjects = get_subjects_list()
        sub_name = subjects[int(sub_idx)]
        file_info = db[sub_name][category][int(item_idx)]
        bot.send_document(call.message.chat.id, file_info['file_id'], caption=f"📌 **{file_info['name']}**")
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_file(call):
    try:
        if call.from_user.id not in ADMINS:
            return
        _, sub_idx, category, item_idx = call.data.split("_")
        subjects = get_subjects_list()
        sub_name = subjects[int(sub_idx)]
        removed = db[sub_name][category].pop(int(item_idx))
        save_data(db)
        bot.answer_callback_query(call.id, f"تم حذف: {removed['name']}")
        show_section_files(call)
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def start_add_file(call):
    try:
        if call.from_user.id not in ADMINS:
            return
        _, sub_idx, category = call.data.split("_")
        sub_index = int(sub_idx)
        subjects = get_subjects_list()
        user_states[call.from_user.id] = {"step": "wait_file", "sub_index": sub_index, "category": category}
        sec_name = "الملازم/التبليغات" if category == "files" else "الامتحانات والأسئلة"
        bot.send_message(call.message.chat.id, f"📥 أرسل الآن الملف أو صورة الجدول لإضافته إلى قسم **{sec_name}** في **{subjects[sub_index]}**:")
    except Exception as e:
        print(f"Error: {e}")

@bot.message_handler(content_types=['document', 'audio', 'video', 'photo'], func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("step") == "wait_file")
def receive_file(message):
    try:
        file_id = message.document.file_id if message.document else (message.photo[-1].file_id if message.photo else message.audio.file_id)
        user_states[message.from_user.id]["file_id"] = file_id
        user_states[message.from_user.id]["step"] = "wait_name"
        bot.reply_to(message, "✏️ اكتب الآن **عنوان أو اسم** هذا المحتوى/الجدول:")
    except Exception as e:
        print(f"Error: {e}")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("step") == "wait_name")
def receive_name(message):
    try:
        state = user_states.pop(message.from_user.id)
        subjects = get_subjects_list()
        sub_name = subjects[state["sub_index"]]
        category = state["category"]

        db[sub_name][category].append({"name": message.text, "file_id": state["file_id"]})
        save_data(db)

        sec_name = "الملازم/التبليغات" if category == "files" else "الامتحانات والأسئلة"
        bot.reply_to(message, f"✅ تم حفظ المحتوى باسم **[{message.text}]** بنجاح في قسم **{sec_name}** داخل **{sub_name}**!", parse_mode="Markdown")
    except Exception as e:
        print(f"Error: {e}")

print("🚀 البوت شغال مع خانة الجداول وإدارة الخانات الكلية...")
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"حدث انقطاع مؤقت، جاري إعادة الاتصال... الأخطاء: {e}")
        time.sleep(3)
هذا؟
