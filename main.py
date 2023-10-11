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
import recognizer as Recognizer

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
    chat_id = update.effective_chat.id
    if chat_id not in users:
        add_user_to_database(chat_id)
    await context.bot.send_message(chat_id, 
"""
I can help you find any song from the web!
you can search for songs, artists and albums just by sending me a the title of the song/album or the name of the artist or even
part of the lyrics!
in groups you can use the inline mode by typing a @ and selecting me from the list and typing the name of the song after a space.
you can also find songs that you don't know with a 10-second voice sample.
""")

async def released_charts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    songs = search.get_new_released_songs()
    buttons = [[InlineKeyboardButton(title , callback_data= data)] for (title, data) in songs]
    await context.bot.send_message(update.effective_chat.id, text='Realesed Songs' ,reply_markup= InlineKeyboardMarkup(buttons))

async def recieve_message(update: Update, context):
    """asking user what to search for"""
    if update.effective_chat.type != 'private': # there's the inline mode for groups
        await context.bot.send_message(chat_id = update.message.chat_id, text= update.message.chat_id)
        return
    message = 'q_' + update.message.text
    buttons = [[InlineKeyboardButton('🎧 Songs', callback_data=message + ':songs'),
                InlineKeyboardButton('🎼 Albums', callback_data=message + ':albums')],
               [InlineKeyboardButton('🎤 Artists', callback_data=message + ':artists')]
               ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text='search for?', reply_to_message_id=update.message.message_id, reply_markup=reply_markup, parse_mode="HTML")

async def get_keyboad_reply(update: Update, context, optional_pram = None):
    """recieves the inline keyboards callback data"""
    chat_id = update.effective_chat.id
    message = update.callback_query.data
    if optional_pram is not None:
        message = optional_pram
    if message.startswith('q_'):
        # searching
        message_to_delete = await context.bot.send_message(chat_id=chat_id, text='Searching...')
        message, search_filter = message[2:message.rindex(':')], message[message.rindex(':') + 1:]
        results = search.query(message, search_filter)
        buttons = [[InlineKeyboardButton(title , callback_data= data)] for (title, data) in results]
        await context.bot.send_message(chat_id=chat_id, text='results', reply_markup=InlineKeyboardMarkup(buttons))
        await context.bot.delete_message(chat_id, message_to_delete.message_id)
    if chat_id in users_to_limit:
		# abuse-proof
        await context.bot.answer_callback_query(update.callback_query.id, 'wait till your last request is finished', show_alert=True)
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
        print(type(songs[0]))
        buttons = [[InlineKeyboardButton(title , callback_data= data)] for (title, data) in songs]
        await context.bot.send_photo(chat_id, cover_art, caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        return
    elif message.startswith('artist_'):
        artist_browse_id = message[7:]
        about, artist_profile, name = search.get_artist(artist_browse_id)
        buttons = []
        buttons = [
            [InlineKeyboardButton('🎧 Singles' , callback_data= str('a_' + artist_browse_id + ':singles')),
			InlineKeyboardButton('🎼 Albums' , callback_data= str('a_' + artist_browse_id + ':albums'))]
						]
        if about:
            buttons.append([InlineKeyboardButton(str('About') , callback_data= 'a_' + artist_browse_id + ':description')])
        await context.bot.send_photo(chat_id, artist_profile, caption=name, reply_markup=InlineKeyboardMarkup(buttons))
        return
    elif message.startswith('a_'):
        message, info_filter = message[2:message.rindex(':')], message[message.rindex(':') + 1:]
        text, results = search.get_artist(message, info_filter)
        buttons = [[InlineKeyboardButton(title , callback_data= data)] for (title, data) in results]
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def get_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """recives voice messages and tries to recognize it"""
    audio_file = await context.bot.get_file(update.message.voice.file_id)
    await audio_file.download_to_drive(update.message.voice.file_id + '.ogg')
    await context.bot.send_message(update.effective_chat.id, 'listening...')
    try:
        with open(update.message.voice.file_id + '.ogg', mode='rb') as excerpt_data:
            song = Recognizer.recognize_API(excerpt_data.read())
            _, id = search.query(song.title + '-' + song.author, 'songs')[0]
            button = [[InlineKeyboardButton('Download', None, id)]]
            if song is not None:
                await context.bot.send_photo(update.effective_chat.id, song.thumbnail_url, '{} - {}'.format(song.title, song.author)
                                                    , reply_markup=InlineKeyboardMarkup(button))
            else:
                await context.bot.send_message(update.effective_chat.id, 'No Match Found')
            os.remove(update.message.voice.file_id + '.ogg')
    except Exception as exception:
        logging.error(exception)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """inline search mode for groups"""
    query = update.inline_query.query

    if query == '':
        return

    search_results = search.query(str(query), 'songs')
    print(search_results)
    results = [
        InlineQueryResultArticle
               (
        id= str(uuid4()),
        title=title,
        input_message_content= InputTextMessageContent('/id ' + id[3:])
               ) for (title, id) in search_results
               ]
    await update.inline_query.answer(results)

async def inline_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """for downloading songs in groups with the inline search mode"""
    # downloading
    users_to_limit.append(update.effective_chat.id)
    message_to_delete = await update.message.reply_text(text='Downloading...', reply_to_message_id=update.message.message_id)
    music_file = await search.get_song(update.message.text[1:])
    if music_file == 'File Too Large':
        await context.bot.send_message(update.effective_chat.id, music_file)
        return
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(music_file, 'rb'),
        caption="<a href='t.me/musicscrappybot'>Download Music🎧</a>", parse_mode='HTML')
    await context.bot.delete_message(update.effective_chat.id, message_to_delete.message_id)
    os.remove(music_file)
    users_to_limit.remove(update.effective_chat.id)

if __name__ == '__main__':
    application = ApplicationBuilder().token(
        '5786788456:AAEEDtaXpker8TaTmqZaSJkcKw5WHs3TSo4').build()
    application.add_handler(CallbackQueryHandler(get_keyboad_reply, block=False))
    application.add_handler(CommandHandler(['start', 'help'], start, block=False))
    application.add_handler(CommandHandler('released', released_charts, block=False))
    application.add_handler(CommandHandler('id', inline_download, block=False))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), recieve_message, block=False))
    application.add_handler(MessageHandler(filters.VOICE , get_voice))
    application.add_handler(InlineQueryHandler(inline_query))

    application.run_polling()
