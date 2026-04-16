import telebot
from PIL import Image
import os
import threading
import time

TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

user_images = {}
user_timers = {}
user_states = {}

def ask_for_name(chat_id):
    if chat_id in user_images and user_images[chat_id]:
        if user_states.get(chat_id) != "waiting_name":
            bot.send_message(chat_id, "✅ Barcha rasmlar qabul qilindi.\n\n📄 Endi PDF nomini yozing:")
            user_states[chat_id] = "waiting_name"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom 👋\n\nMenga rasmlarni yuboring, men ularni bitta PDF qilib beraman.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_path = f"temp_{chat_id}_{message.message_id}.jpg"
        with open(image_path, "wb") as f:
            f.write(downloaded_file)
        user_images.setdefault(chat_id, []).append(image_path)
        if chat_id in user_timers:
            user_timers[chat_id].cancel()
        t = threading.Timer(4.0, ask_for_name, args=[chat_id])
        user_timers[chat_id] = t
        t.start()
    except Exception as e:
        bot.send_message(chat_id, f"❌ Rasm yuklashda xato: {e}")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "waiting_name")
def create_pdf(message):
    chat_id = message.chat.id
    file_name = message.text.strip()
    clean_name = "".join(c for c in file_name if c.isalpha() or c.isdigit() or c in " ._-").rstrip()
    if not clean_name:
        bot.send_message(chat_id, "⚠️ To‘g‘ri nom yuboring.")
        return
    pdf_path = f"{clean_name}.pdf"
    try:
        msg = bot.send_message(chat_id, "⏳ PDF tayyorlanmoqda...")
        img_paths = user_images[chat_id]
        images = [Image.open(p).convert("RGB") for p in img_paths]
        if images:
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
            with open(pdf_path, "rb") as f:
                bot.send_document(chat_id, f, visible_file_name=pdf_path, caption="✅ PDF tayyor bo‘ldi!")
        for p in img_paths:
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        user_images.pop(chat_id, None)
        user_states.pop(chat_id, None)
        user_timers.pop(chat_id, None)
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Xatolik: {e}")

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print("Qayta ulanmoqda:", e)
            time.sleep(5)
