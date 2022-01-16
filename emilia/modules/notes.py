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

import re, ast
from io import BytesIO
import random
from typing import Optional

import emilia.modules.sql.notes_sql as sql
from emilia import LOGGER, JOIN_LOGGER, SUPPORT_CHAT, dispatcher, DRAGONS
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.handlers import MessageHandlerChecker
from emilia.modules.helper_funcs.chat_status import user_admin, connection_status
from emilia.modules.helper_funcs.misc import build_keyboard, revert_buttons
from emilia.modules.helper_funcs.msg_types import get_note_type
from emilia.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
)
from telegram import (
    MAX_MESSAGE_LENGTH,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    InlineKeyboardButton,
)
from telegram.error import BadRequest
from telegram.utils.helpers import escape_markdown, mention_markdown
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    Filters,
    MessageHandler,
)

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}


# Do not async
def get(update, context, notename, show_none=True, no_format=False):
    bot = context.bot
    chat_id = update.effective_message.chat.id
    note_chat_id = update.effective_chat.id
    note = sql.get_note(note_chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        if MessageHandlerChecker.check_user(update.effective_user.id):
            return
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id
        if note.is_reply:
            if JOIN_LOGGER:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=JOIN_LOGGER,
                        message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "Pesan untuk diteruskan tidak ditemukan":
                        message.reply_text(
                            "Pesan ini tampaknya telah hilang - saya akan menghapusnya "
                            "dari daftar catatan Anda..",
                        )
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "Pesan untuk diteruskan tidak ditemukan":
                        message.reply_text(
                            "Sepertinya pengirim asli dari catatan ini telah dihapus "
                            "pesan mereka - maaf! Dapatkan admin bot Anda untuk mulai menggunakan "
                            "pesan dump untuk menghindari ini. Saya akan menghapus catatan ini dari "
                            "catatan tersimpan Anda.",
                        )
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
        else:
            VALID_NOTE_FORMATTERS = [
                "first",
                "last",
                "fullname",
                "username",
                "id",
                "chatname",
                "mention",
            ]
            valid_format = escape_invalid_curly_brackets(
                note.value,
                VALID_NOTE_FORMATTERS,
            )
            if valid_format:
                if not no_format:
                    if "%%%" in valid_format:
                        split = valid_format.split("%%%")
                        if all(split):
                            text = random.choice(split)
                        else:
                            text = valid_format
                    else:
                        text = valid_format
                else:
                    text = valid_format
                text = text.format(
                    first=escape_markdown(message.from_user.first_name),
                    last=escape_markdown(
                        message.from_user.last_name or message.from_user.first_name,
                    ),
                    fullname=escape_markdown(
                        " ".join(
                            [message.from_user.first_name, message.from_user.last_name]
                            if message.from_user.last_name
                            else [message.from_user.first_name],
                        ),
                    ),
                    username="@" + message.from_user.username
                    if message.from_user.username
                    else mention_markdown(
                        message.from_user.id,
                        message.from_user.first_name,
                    ),
                    mention=mention_markdown(
                        message.from_user.id,
                        message.from_user.first_name,
                    ),
                    chatname=escape_markdown(
                        message.chat.title
                        if message.chat.type != "private"
                        else message.from_user.first_name,
                    ),
                    id=message.from_user.id,
                )
            else:
                text = ""

            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(note_chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
                else:
                    ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        caption=text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        reply_markup=keyboard,
                    )

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text(
                        "Sepertinya Anda mencoba menyebutkan seseorang yang belum pernah saya lihat sebelumnya. Jika Anda benar-benar "
                        "ingin menyebutkan mereka, meneruskan salah satu pesan mereka kepada saya, dan saya akan dapat "
                        "untuk menandai mereka!",
                    )
                elif FILE_MATCHER.match(note.value):
                    message.reply_text(
                        "Catatan ini adalah file yang diimpor secara salah dari bot lain - saya tidak dapat menggunakan "
                        "dia. Jika Anda benar-benar membutuhkannya, Anda harus menyimpannya lagi. Di "
                        "sementara itu, saya akan menghapusnya dari daftar catatan Anda.",
                    )
                    sql.rm_note(note_chat_id, notename)
                else:
                    message.reply_text(
                        "Catatan ini tidak dapat dikirim, karena formatnya salah. Tanyakan "
                        f"@{SUPPORT_CHAT} jika Anda tidak tahu mengapa!",
                    )
                    LOGGER.exception(
                        "Tidak dapat mengurai pesan #%s dalam obrolan %s",
                        notename,
                        str(note_chat_id),
                    )
                    LOGGER.warning("Pesan adalah: %s", str(note.value))
        return
    if show_none:
        message.reply_text("Catatan ini tidak ada")


@connection_status
def cmd_get(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(update, context, args[0].lower(), show_none=True, no_format=True)
    elif len(args) >= 1:
        get(update, context, args[0].lower(), show_none=True)
    else:
        update.effective_message.reply_text("Get apa?")


@connection_status
def hash_get(update: Update, context: CallbackContext):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:].lower()
    get(update, context, no_hash, show_none=False)


@connection_status
def slash_get(update: Update, context: CallbackContext):
    message, chat_id = update.effective_message.text, update.effective_chat.id
    no_slash = message[1:]
    note_list = sql.get_all_chat_notes(chat_id)

    try:
        noteid = note_list[int(no_slash) - 1]
        note_name = str(noteid).strip(">").split()[1]
        get(update, context, note_name, show_none=False)
    except IndexError:
        update.effective_message.reply_text("ID Catatan Salah")


@user_admin
@connection_status
def save(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)
    note_name = note_name.lower()
    if data_type is None:
        msg.reply_text("tidak ada catatan")
        return

    sql.add_note_to_db(
        chat_id,
        note_name,
        text,
        data_type,
        buttons=buttons,
        file=content,
    )

    msg.reply_text(
        f"Ok, catatan `{note_name}` disimpan!",
        parse_mode=ParseMode.MARKDOWN,
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text(
                "Sepertinya Anda mencoba menyimpan pesan dari bot. Sayangnya, "
                "bot tidak dapat meneruskan pesan bot, jadi saya tidak dapat menyimpan pesan yang tepat. "
                "\nSaya akan menyimpan semua teks yang saya bisa, tetapi jika Anda ingin lebih, Anda harus "
                "teruskan pesan itu sendiri, lalu simpan.",
            )
        else:
            msg.reply_text(
                "Bot agak cacat oleh telegram, sehingga sulit bagi bot untuk "
                "berinteraksi dengan bot lain, jadi saya tidak dapat menyimpan pesan ini "
                "seperti yang biasanya saya lakukan - apakah Anda keberatan meneruskannya dan "
                "lalu simpan pesan baru itu? Terima kasih!",
            )
        return


@user_admin
@connection_status
def clear(update: Update, context: CallbackContext):
    args = context.args
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0].lower()

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("Berhasil menghapus catatan.")
        else:
            update.effective_message.reply_text("Itu bukan catatan di database saya!")


def clearall(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in DRAGONS:
        update.effective_message.reply_text(
            "Hanya pemilik obrolan yang dapat menghapus semua catatan sekaligus.",
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Hapus semua catatan",
                        callback_data="notes_rmall",
                    ),
                ],
                [InlineKeyboardButton(text="Membatalkan", callback_data="notes_cancel")],
            ],
        )
        update.effective_message.reply_text(
            f"Apakah Anda yakin ingin menghapus SEMUA catatan di {chat.title}? Tindakan ini tidak bisa dibatalkan.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


def clearall_btn(update: Update, context: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == "notes_rmall":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            note_list = sql.get_all_chat_notes(chat.id)
            try:
                for notename in note_list:
                    note = notename.name.lower()
                    sql.rm_note(chat.id, note)
                message.edit_text("Menghapus semua catatan.")
            except BadRequest:
                return

        if member.status == "administrator":
            query.answer("Hanya pemilik obrolan yang dapat melakukan ini.")

        if member.status == "member":
            query.answer("Anda harus menjadi admin untuk melakukan ini.")
    elif query.data == "notes_cancel":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            message.edit_text("Hapus semua catatan telah dibatalkan.")
            return
        if member.status == "administrator":
            query.answer("Hanya pemilik obrolan yang dapat melakukan ini.")
        if member.status == "member":
            query.answer("Anda harus menjadi admin untuk melakukan ini.")


@connection_status
def list_notes(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)
    notes = len(note_list) + 1
    msg = "*ID* *Catatan* \n"
    for note_id, note in zip(range(1, notes), note_list):
        if note_id < 10:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        else:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if not note_list:
        try:
            update.effective_message.reply_text("Tidak ada catatan dalam obrolan ini!")
        except BadRequest:
            update.effective_message.reply_text("Tidak ada catatan dalam obrolan ini!", quote=False)

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)
        matchsticker = STICKER_MATCHER.match(notedata)
        matchbtn = BUTTON_MATCHER.match(notedata)
        matchfile = MYFILE_MATCHER.match(notedata)
        matchphoto = MYPHOTO_MATCHER.match(notedata)
        matchaudio = MYAUDIO_MATCHER.match(notedata)
        matchvoice = MYVOICE_MATCHER.match(notedata)
        matchvideo = MYVIDEO_MATCHER.match(notedata)
        matchvn = MYVIDEONOTE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end() :].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        elif matchsticker:
            content = notedata[matchsticker.end() :].strip()
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.STICKER,
                    file=content,
                )
        elif matchbtn:
            parse = notedata[matchbtn.end() :].strip()
            notedata = parse.split("<###button###>")[0]
            buttons = parse.split("<###button###>")[1]
            buttons = ast.literal_eval(buttons)
            if buttons:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.BUTTON_TEXT,
                    buttons=buttons,
                )
        elif matchfile:
            file = notedata[matchfile.end() :].strip()
            file = file.split("<###TYPESPLIT###>")
            notedata = file[1]
            content = file[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.DOCUMENT,
                    file=content,
                )
        elif matchphoto:
            photo = notedata[matchphoto.end() :].strip()
            photo = photo.split("<###TYPESPLIT###>")
            notedata = photo[1]
            content = photo[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.PHOTO,
                    file=content,
                )
        elif matchaudio:
            audio = notedata[matchaudio.end() :].strip()
            audio = audio.split("<###TYPESPLIT###>")
            notedata = audio[1]
            content = audio[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.AUDIO,
                    file=content,
                )
        elif matchvoice:
            voice = notedata[matchvoice.end() :].strip()
            voice = voice.split("<###TYPESPLIT###>")
            notedata = voice[1]
            content = voice[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VOICE,
                    file=content,
                )
        elif matchvideo:
            video = notedata[matchvideo.end() :].strip()
            video = video.split("<###TYPESPLIT###>")
            notedata = video[1]
            content = video[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO,
                    file=content,
                )
        elif matchvn:
            video_note = notedata[matchvn.end() :].strip()
            video_note = video_note.split("<###TYPESPLIT###>")
            notedata = video_note[1]
            content = video_note[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO_NOTE,
                    file=content,
                )
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="File/foto ini gagal diimpor karena berasal "
                "dari bot lain. Ini adalah pembatasan API telegram, dan tidak bisa "
                "dihindari. Maaf untuk ketidaknyamanannya!",
            )


def __stats__():
    return f"{sql.num_notes()} catatan, pada {sql.num_chats()} obrolan."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"Ada catatan `{len(notes)}` dalam obrolan ini."


__help__ = """
Simpan data untuk pengguna masa depan dengan catatan!
Catatan bagus untuk menyimpan informasi acak; nomor telepon, gif yang bagus, gambar lucu - apa saja!

✦ *Perintah yang tersedia adalah:*
 ✧ /save <nama> <isi>: Simpan konten ke catatan dengan nama "nama". Membalas pesan akan menyimpan pesan itu. Bahkan bekerja di media!
 ✧ /get <nama>: Dapatkan catatan dengan nama "nama".
   #<nama>: sama dengan /get nama
 ✧ /clear <nama>: hapus catatan yang disebut "nama"
 ✧ /notes: Daftar semua catatan dalam obrolan saat ini
 ✧ /saved: sama dengan /notes
 ✧ /removeallnotes: Clean all notes in your group, only use this if you know what you're doing

✦ *Contoh cara menyimpan catatan adalah melalui:*
 /save data Ini adalah beberapa data!
 Sekarang, siapa pun yang menggunakan "/get data", atau "#data" akan dibalas dengan "Ini adalah beberapa data!".
 Jika Anda ingin menyimpan gambar, gif, atau stiker, atau data lainnya, lakukan hal berikut:
 /save kata sambil membalas stiker atau data apa pun yang Anda inginkan. Sekarang, catatan di "#word" berisi stiker yang akan dikirim sebagai balasan.

✦ *Tip:*
untuk mengambil catatan tanpa format, gunakan /get <namacatatan> noformat
Ini akan mengambil catatan dan mengirimkannya tanpa memformatnya; membuat Anda raw markdown, memungkinkan Anda melakukan pengeditan dengan mudah

✦ *Catatan:*
Nama catatan tidak peka huruf besar-kecil, dan secara otomatis diubah menjadi huruf kecil sebelum disimpan.
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, run_async=True)
HASH_GET_HANDLER = MessageHandler(Filters.regex(r"^#[^\s]+"), hash_get, run_async=True)
SLASH_GET_HANDLER = MessageHandler(Filters.regex(r"^/\d+$"), slash_get, run_async=True)
SAVE_HANDLER = CommandHandler("save", save, run_async=True)
DELETE_HANDLER = CommandHandler("clear", clear, run_async=True)
LIST_HANDLER = DisableAbleCommandHandler(
    ["notes", "saved"], list_notes, admin_ok=True, run_async=True
)
CLEARALL = DisableAbleCommandHandler("removeallnotes", clearall, run_async=True)
CLEARALL_BTN = CallbackQueryHandler(clearall_btn, pattern=r"notes_.*", run_async=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
dispatcher.add_handler(SLASH_GET_HANDLER)
dispatcher.add_handler(CLEARALL)
dispatcher.add_handler(CLEARALL_BTN)
