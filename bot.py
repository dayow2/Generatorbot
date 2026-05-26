import os
import requests
from flask import Flask, request
import telebot

# Initialize Flask app
app = Flask(__name__)

# Get tokens from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Safeguard: Fallback to Render's default domain if WEBHOOK_URL is missing
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', RENDER_EXTERNAL_URL)

# Ensure the webhook URL has a trailing slash
if WEBHOOK_URL and not WEBHOOK_URL.endswith('/'):
    WEBHOOK_URL += '/'

bot = telebot.TeleBot(BOT_TOKEN)

# Telegram Bot Command Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🎨 *Welcome to the AI Image Generator Bot!*\n\n"
        "Just send me a descriptive text prompt (e.g., 'a futuristic city at sunset, cyberpunk style'), "
        "and I will generate an AI image for you!"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def generate_image(message):
    prompt = message.text
    chat_id = message.chat.id
    
    # Send a placeholder message so the user knows the AI is working
    status_message = bot.reply_to(message, "🚀 *Generating your image... Please wait.*", parse_mode='Markdown')
    bot.send_chat_action(chat_id, 'upload_photo')
    
    try:
        # Format prompt for the free Pollinations AI Image API
        # Replacing spaces with %20 for URL encoding
        encoded_prompt = requests.utils.quote(prompt)
        image_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed=42"
        
        # Download the generated image from the API
        response = requests.get(image_url, timeout=30)
        
        if response.status_code == 200:
            # Send the image back to the Telegram user
            bot.send_photo(
                chat_id=chat_id, 
                photo=response.content, 
                caption=f"✨ Here is your image for: \n_\"{prompt}\"_",
                reply_to_message_id=message.message_id,
                parse_mode='Markdown'
            )
            # Delete the "Generating..." status message to clean up the chat
            bot.delete_message(chat_id, status_message.message_id)
        else:
            bot.edit_message_text("❌ Failed to generate image from AI engine. Try a different prompt.", chat_id, status_message.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ Something went wrong: {str(e)}", chat_id, status_message.message_id)

# Flask Routes for Webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    if not BOT_TOKEN:
        return "Error: BOT_TOKEN environment variable is missing!", 500
    if not WEBHOOK_URL:
        return "Error: WEBHOOK_URL environment variable is missing!", 500
        
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + BOT_TOKEN)
    return f"AI Image Generator Bot is running. Webhook set to: {WEBHOOK_URL}", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
