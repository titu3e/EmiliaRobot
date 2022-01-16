# Copyright (C) 2022 Zenitsu-Project.
#
# Emilia is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Emilia is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# translate to Indonesian by @ZenitsuPrjkt

import time
import os
import re
import codecs
from typing import List
from random import randint
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.disable import DisableAbleCommandHandler
from emilia import (
    dispatcher,
    WALL_API,
)
import requests as r
import wikipedia
from requests import get, post
from telegram import (
    Chat,
    ChatAction,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Message,
    MessageEntity,
    TelegramError,
)
from telegram.error import BadRequest
from telegram.ext.dispatcher import run_async
from telegram.ext import CallbackContext, Filters, CommandHandler
from emilia import StartTime
from emilia.modules.helper_funcs.chat_status import sudo_plus
from emilia.modules.helper_funcs.alternate import send_action, typing_action

MARKDOWN_HELP = f"""
Markdown adalah alat pemformatan yang sangat kuat yang didukung oleh telegram. {dispatcher.bot.first_name} memiliki beberapa peningkatan, untuk memastikan bahwa \
pesan yang disimpan diuraikan dengan benar, dan untuk memungkinkan Anda membuat tombol.

- <code>_italic_</code>: membungkus teks dengan '_' akan menghasilkan italic teks
- <code>*bold*</code>: membungkus teks dengan '*' akan menghasilkan bold teks
- <code>`code`</code>: membungkus teks dengan '`' akan menghasilkan monospaced teks, juga dikenal sebagai 'code'
- <code>[sometext](someURL)</code>: ini akan membuat tautan - pesan hanya akan ditampilkan <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
<b>Contoh:</b><code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: ini adalah peningkatan khusus untuk memungkinkan pengguna memiliki telegram \
tombol markdown. <code>buttontext</code> akan menjadi apa yang ditampilkan pada tombol, dan <code>someurl</code> \
will be the url which is opened.
<b>Contoh:</b> <code>[Ini adalah tombol](buttonurl:example.com)</code>

Jika Anda ingin beberapa tombol pada baris yang sama, gunakan :same, Dengan demikian:
<code>[satu](buttonurl://example.com)
[dua](buttonurl://google.com:same)</code>
Ini akan membuat dua tombol pada satu baris, alih-alih satu tombol per baris.
Ingatlah bahwa pesan Anda <b>HARUS</b> berisi beberapa teks selain hanya sebuah tombol!
"""


@user_admin
def echo(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if message.reply_to_message:
        message.reply_to_message.reply_text(
            args[1], parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    else:
        message.reply_text(
            args[1], quote=False, parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    message.delete()


def markdown_help_sender(update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "Coba teruskan pesan berikut kepada saya, dan Anda akan melihat, dan Gunakan #test!"
    )
    update.effective_message.reply_text(
        "/save tes Ini adalah markdown test. _italics_, *bold*, code, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)"
    )


def markdown_help(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        update.effective_message.reply_text(
            "Hubungi saya di pm",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Bantuan Markdown",
                            url=f"t.me/{context.bot.username}?start=markdownhelp",
                        )
                    ]
                ]
            ),
        )
        return
    markdown_help_sender(update)


def wiki(update: Update, context: CallbackContext):
    kueri = re.split(pattern="wiki", string=update.effective_message.text)
    wikipedia.set_lang("en")
    if len(str(kueri[1])) == 0:
        update.effective_message.reply_text("Enter keywords!")
    else:
        try:
            pertama = update.effective_message.reply_text("Memuat...")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Info lebih lanjut...",
                            url=wikipedia.page(kueri).url,
                        )
                    ]
                ]
            )
            context.bot.editMessageText(
                chat_id=update.effective_chat.id,
                message_id=pertama.message_id,
                text=wikipedia.summary(kueri, sentences=10),
                reply_markup=keyboard,
            )
        except wikipedia.PageError as e:
            update.effective_message.reply_text(f"Error: {e}")
        except BadRequest as et:
            update.effective_message.reply_text(f"Error: {et}")
        except wikipedia.exceptions.DisambiguationError as eet:
            update.effective_message.reply_text(
                f"⚠ Error\n Ada terlalu banyak permintaan!! Ekspresikan lebih banyak!\nKemungkinan hasil kueri:\n{eet}"
            )


@send_action(ChatAction.UPLOAD_PHOTO)
def wall(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    msg_id = update.effective_message.message_id
    args = context.args
    query = " ".join(args)
    if not query:
        msg.reply_text("Silakan masukkan kueri!")
        return
    caption = query
    term = query.replace(" ", "%20")
    json_rep = r.get(
        f"https://wall.alphacoders.com/api2.0/get.php?auth={WALL_API}&method=search&term={term}"
    ).json()
    if not json_rep.get("success"):
        msg.reply_text("An error occurred!")

    else:
        wallpapers = json_rep.get("wallpapers")
        if not wallpapers:
            msg.reply_text("No results found! Refine your search.")
            return
        index = randint(0, len(wallpapers) - 1)  # Choose random index
        wallpaper = wallpapers[index]
        wallpaper = wallpaper.get("url_image")
        wallpaper = wallpaper.replace("\\", "")
        context.bot.send_photo(
            chat_id,
            photo=wallpaper,
            caption="Preview",
            reply_to_message_id=msg_id,
            timeout=60,
        )
        context.bot.send_document(
            chat_id,
            document=wallpaper,
            filename="wallpaper",
            caption=caption,
            reply_to_message_id=msg_id,
            timeout=60,
        )


ECHO_HANDLER = DisableAbleCommandHandler(
    "echo", echo, filters=Filters.chat_type.groups, run_async=True)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, run_async=True)
WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
WALLPAPER_HANDLER = DisableAbleCommandHandler("wall", wall, run_async=True)

dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(WIKI_HANDLER)
dispatcher.add_handler(WALLPAPER_HANDLER)

__mod_name__ = "Extras"
__command_list__ = ["id", "echo", "wiki", "wall"]
__handlers__ = [
    ECHO_HANDLER,
    MD_HELP_HANDLER,
    WIKI_HANDLER,
    WALLPAPER_HANDLER,
]
