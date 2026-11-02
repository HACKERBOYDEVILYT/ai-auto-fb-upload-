import os, requests, random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_TOKEN = os.getenv("FB_ACCESS_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- FB Functions ---
def fb_text_post(msg):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    return requests.post(url, data={"message": msg, "access_token": FB_TOKEN}).json()

def fb_video_post(file_path, caption):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/videos"
    with open(file_path, 'rb') as f:
        return requests.post(url, files={'source': f}, data={'description': caption, 'access_token': FB_TOKEN}).json()

def gen_ai():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    prompt = "একটি ভাইরাল বাংলা ফেসবুক পোস্ট লিখো, 2-3 লাইন, emoji সহ, মোটিভেশন/ফানি/লাইফ হ্যাক টপিক।"
    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
    try:
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "✨ আজকের দিনটা তোমার, চালিয়ে যাও! 💪 #motivation"

# --- Telegram Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 FB Control Bot Ready!\n\n"
        "/post <লেখা> - সাথে সাথে পোস্ট\n"
        "/ai - AI দিয়ে পোস্ট\n"
        "/status - বট Active\n"
        "ভিডিও পাঠালে সরাসরি FB তে আপলোড হবে"
    )

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text: return await update.message.reply_text("লিখুন: /post আজকের মোটিভেশন")
    res = fb_text_post(text)
    await update.message.reply_text(f"✅ Posted!\nID: {res.get('id')}")

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ AI লিখছে...")
    content = gen_ai()
    res = fb_text_post(content)
    await update.message.reply_text(f"✅ AI Posted:\n\n{content}\n\n{res}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 ভিডিও পাচ্ছি, FB তে আপলোড দিচ্ছি...")
    file = await context.bot.get_file(update.message.video.file_id)
    await file.download_to_drive("temp_video.mp4")
    caption = update.message.caption or gen_ai()
    res = fb_video_post("temp_video.mp4", caption)
    await update.message.reply_text(f"✅ Video Posted!\n\n{caption}\n\n{res}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot Running\nFB Page ID: "+FB_PAGE_ID+"\nReady to control!")

# --- Run ---
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("post", post_cmd))
app.add_handler(CommandHandler("ai", ai_cmd))
app.add_handler(CommandHandler("status", status_cmd))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

print("Bot Started...")
app.run_polling()
