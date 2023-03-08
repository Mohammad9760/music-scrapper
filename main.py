import os
import json
import logging
from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import search

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

users_to_limit = []  # users that already have a request pending
users = []
with open('users.json', 'r+', encoding='utf-8') as users_database:
    try:
        users = json.load(users_database)
        users_database.close()
    except FileNotFoundError:
        pass

def add_user_to_database(user_id):
    """adds user id to the users.json"""
    with open('users.json', 'w', encoding='utf-8') as users_database:
        users.append(user_id)
        json.dump(users, users_database)
        users_database.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adds new users to users database"""
    await context.bot.send_message(update.effective_chat.id,
     "you can use me to donwload any song from the web!")
    chat_id = update.effective_chat.id
    if chat_id not in users:
        add_user_to_database(chat_id)

async def recieve_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """asking user what to search for"""
    message = 's_' + update.message.text
    buttons = [[InlineKeyboardButton('🎧 Songs', callback_data=message + ':songs'),
                InlineKeyboardButton('🎼 Albums', callback_data=message + ':albums')],
               [InlineKeyboardButton('🎤 Artists', callback_data=message + ':artists')]
               ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text='search for?', reply_to_message_id=update.message.message_id, reply_markup=reply_markup, parse_mode="HTML")

async def get_keyboad_reply(update: Update, context):
    """recieves the inline keyboards callback data"""
    chat_id = update.effective_chat.id
    message = update.callback_query.data
    if message.startswith('s_'):
        # searching
        message_to_delete = await context.bot.send_message(chat_id=chat_id, text='Searching...')
        message, search_filter = message[2:message.rindex(':')], message[message.rindex(':') + 1:]
        results = search.query(message, search_filter)
        buttons = []
        for title in results:
            buttons.append([InlineKeyboardButton(title , callback_data=results.get(title))])
        await context.bot.send_message(chat_id=chat_id, text='results', reply_markup=InlineKeyboardMarkup(buttons))
        await context.bot.delete_message(chat_id, message_to_delete.message_id)
    if chat_id in users_to_limit:
		# abuse-proof
        await context.bot.send_message(chat_id, 'wait till your last request is finished')
        return
    elif message.startswith('dl_'):
        # downloading
        users_to_limit.append(chat_id)
        message_to_delete = await context.bot.send_message(chat_id, 'Downloading...')
        music_file = await search.get_song(message)
        if music_file == 'File Too Large':
            await context.bot.send_message(chat_id, music_file)
            return
        await context.bot.send_audio(chat_id=chat_id, audio=open(music_file, 'rb'),
         caption="<a href='t.me/musicscrappybot'>Download Music🎧</a>", parse_mode='HTML')
        await context.bot.delete_message(chat_id, message_to_delete.message_id)
        os.remove(music_file)
        users_to_limit.remove(chat_id)
        return
    elif message.startswith('album_'):
        cover_art, songs ,caption= search.get_album(message)
        buttons = []
        for title in songs:
            buttons.append([InlineKeyboardButton(title , callback_data=songs.get(title))])
        await context.bot.send_photo(chat_id, cover_art, caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        #os.remove(cover_art)
        return
    elif message.startswith('artist_'):
        about, artist_profile = search.get_artist(message[7:])
        buttons = []
        buttons = [
            [InlineKeyboardButton('🎧 Singles' , callback_data= str('a_' + artist_browse_id + ':singles')),
			InlineKeyboardButton('🎼 Albums' , callback_data= str('a_' + artist_browse_id + ':albums'))]
						]
        if about:
            buttons.append([InlineKeyboardButton(str('About') , callback_data= 'a_' + artist_browse_id + ':description')])
        await context.bot.send_photo(chat_id, artist_profile, reply_markup=InlineKeyboardMarkup(buttons))
        return
    elif message.startswith('a_'):
        message, info_filter = message[2:message.rindex(':')], message[message.rindex(':') + 1:]
        text, results = search.get_artist(message, info_filter)
        buttons = []
        for title in results:
            buttons.append([InlineKeyboardButton(title , callback_data=results.get(title))])
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def get_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """recives voice messages and tries to recognize it"""
    audio_file = await context.bot.get_file(update.message.voice.file_id)
    await audio_file.download_to_drive(update.message.voice.file_id + '.ogg')
    await context.bot.send_message(update.effective_chat.id, 'No Match Found :(')

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    if query == '':
        return

    results = [
        InlineQueryResultArticle
               (
        id= str(uuid4()),
        title='not implemented search feature haha',
        input_message_content= InputTextMessageContent('some callback data...')
               )
               ]
    await update.inline_query.answer(results)

if __name__ == '__main__':
    application = ApplicationBuilder().token('TOKEN'
        ).build()
    application.add_handler(CallbackQueryHandler(get_keyboad_reply, block=False))
    application.add_handler(CommandHandler(['start', 'help'], start, block=False))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), recieve_message, block=False))
    application.add_handler(MessageHandler(filters.VOICE , get_voice))
    application.add_handler(InlineQueryHandler(inline_query))

    application.run_polling()
