# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask",
#     "line-bot-sdk",
#     "deepl",
#     "OpenCC",
#     "waitress"
# ]
# ///
import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import deepl
import opencc
from waitress import serve

app = Flask(__name__)

channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
deepl_auth_key = os.getenv("DEEPL_AUTH_KEY")

if not all([channel_secret, channel_access_token, deepl_auth_key]):
    print("Missing required environment variables.")
    sys.exit(1)

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

translator = deepl.Translator(deepl_auth_key)
# Ensures translation targets Traditional Chinese
converter = opencc.OpenCC("s2t.json")

def translate(text):
    en_text = translator.translate_text(text, target_lang="EN-US")
    result = en_text.text + "\n\n"

    if en_text.detected_source_lang in ("ZH", "EN"):
        app.logger.info("Detected Chinese or English text")
        id_text = translator.translate_text(text, target_lang="ID")
        result += id_text.text
    else:
        app.logger.info("Detected Indonesian text")
        zh_text = translator.translate_text(text, target_lang="ZH")
        result += converter.convert(zh_text.text)

    return result

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature.")
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        translated_message = translate(event.message.text)
        
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=translated_message)],
            )
        )

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("LINE Translate Bot: Webhook server for translating LINE messages via DeepL.")
        sys.exit(0)
        
    print("Starting LINE Translate Bot server...")
    serve(app, host="0.0.0.0", port=8000, threads=8)

