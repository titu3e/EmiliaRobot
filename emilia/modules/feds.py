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

import ast
import csv
import json
import os
import re
import time
import uuid
from io import BytesIO

import emilia.modules.sql.feds_sql as sql
from emilia import (
    EVENT_LOGS,
    LOGGER,
    SUPPORT_CHAT,
    OWNER_ID,
    DRAGONS,
    TIGERS,
    WOLVES,
    dispatcher,
)
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.alternate import send_message
from emilia.modules.helper_funcs.chat_status import is_user_admin
from emilia.modules.helper_funcs.extraction import (
    extract_unt_fedban,
    extract_user,
    extract_user_fban,
)
from emilia.modules.helper_funcs.string_handling import markdown_parser
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    Update,
)
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    run_async,
)
from telegram.utils.helpers import mention_html, mention_markdown

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan pembatasan anggota obrolan",
    "User_not_participant",
    "Peer_id_invalid",
    "Obrolan grup dinonaktifkan",
    "Perlu mengundang pengguna untuk menendangnya dari grup dasar",
    "Chat_admin_required",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Channel_private",
    "Tidak di obrolan",
    "Tidak memiliki hak untuk mengirim pesan",
}

UNFBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan pembatasan anggota obrolan",
    "User_not_participant",
    "Metode ini hanya tersedia untuk obrolan supergrup dan saluran",
    "Tidak di obrolan",
    "Channel_private",
    "Chat_admin_required",
    "Tidak memiliki hak untuk mengirim pesan",
}


def new_fed(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text(
            "Federasi hanya dapat dibuat dengan mengirimi saya pesan pribadi..",
        )
        return
    if len(message.text) == 1:
        send_message(
            update.effective_message,
            "Tolong tulis nama federasi!",
        )
        return
    fednam = message.text.split(None, 1)[1]
    if not fednam == "":
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        # Currently only for creator
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text(
                f"Gagal bergabung dengan federasi! Tolong hubungi pembuat saya jika masalah ini masih berlanjut.",
            )
            return

        update.effective_message.reply_text(
            "*Anda telah berhasil membuat federasi baru!*"
            "\nNama: `{}`"
            "\nID: `{}`"
            "\n\nGunakan perintah di bawah ini untuk bergabung dengan federasi:"
            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            bot.send_message(
                EVENT_LOGS,
                "Federasi <b>{}</b> telah di buat dengan ID: <pre>{}</pre>".format(fed_name, fed_id),
                parse_mode=ParseMode.HTML,
            )
        except:
            LOGGER.warning("Tidak dapat mengirim pesan ke EVENT_LOGS")
    else:
        update.effective_message.reply_text(
            "Tolong tulis nama federasinya",
        )


def del_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        update.effective_message.reply_text(
            "Hapus federasi Anda di PM saya, bukan dalam grup.",
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo is False:
            update.effective_message.reply_text("Federasi ini tidak ada.")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
            return
    else:
        update.effective_message.reply_text("Apa yang harus saya hapus?")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    update.effective_message.reply_text(
        "Anda yakin ingin menghapus federasi Anda? Tindakan ini tidak bisa dibatalkan, Anda akan kehilangan seluruh daftar larangan Anda, dan '{}' akan hilang secara permanen.".format(
            getinfo["fname"],
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Hapus Federasi",
                        callback_data="rmfed_{}".format(fed_id),
                    ),
                ],
                [InlineKeyboardButton(text="Batalkan", callback_data="rmfed_cancel")],
            ],
        ),
    )


def rename_fed(update, context):
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 2)

    if len(args) < 3:
        return msg.reply_text("penggunaan: /renamefed <fed_id> <newname>")

    fed_id, newname = args[1], args[2]
    verify_fed = sql.get_fed_info(fed_id)

    if not verify_fed:
        return msg.reply_text("Umpan ini tidak ada di database saya!")

    if is_user_fed_owner(fed_id, user.id):
        sql.rename_fed(fed_id, user.id, newname)
        msg.reply_text(f"Berhasil mengganti nama feed Anda menjadi {newname}!")
    else:
        msg.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")


def fed_chat(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text(
            "Anda harus menjadi admin untuk menjalankan perintah ini",
        )
        return

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak dalam federasi apa pun!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "Obrolan ini adalah bagian dari federasi berikut:"
    text += "\n{} (ID: <code>{}</code>)".format(info["fname"], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in DRAGONS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text(
                        "Hanya pembuat grup yang dapat melakukannya!",
                    )
                    return
    if fed_id:
        message.reply_text("Anda tidak bisa bergabung dua federasi dalam satu obrolan")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            message.reply_text("Silakan masukkan id federasi yang valid")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            message.reply_text(
                f"Gagal bergabung dengan federasi! Tolong hubungi pembuat saya jika masalah ini masih berlanjut",
            )
            return

        get_fedlog = sql.get_fed_log(args[0])
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "Obrolan *{}* telah bergabung ke federasi *{}*".format(
                        chat.title,
                        getfed["fname"],
                    ),
                    parse_mode="markdown",
                )

        message.reply_text(
            "Obrolan ini telah bergabung dengan federasi {}!".format(getfed["fname"]),
        )


def leave_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in "creator" or user.id in DRAGONS:
        if sql.chat_leave_fed(chat.id) is True:
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    bot.send_message(
                        get_fedlog,
                        "Obrolan *{}* telah keluar ke federasi *{}*".format(
                            chat.title,
                            fed_info["fname"],
                        ),
                        parse_mode="markdown",
                    )
            send_message(
                update.effective_message,
                "Obrolan ini telah keluar dari federasi {}!".format(fed_info["fname"]),
            )
        else:
            update.effective_message.reply_text(
                "Mengapa Anda meninggalkan federasi ketika Anda belum bergabung?",
            )
    else:
        update.effective_message.reply_text("Hanya pembuat grup yang dapat melakukannya!")


def user_join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in DRAGONS:
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari ini")
            return
        else:
            LOGGER.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = ast.literal_eval(info["fusers"])["owner"]
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text(
                "Mengapa Anda mencoba mempromosikan pemilik federasi!?",
            )
            return
        if getuser:
            update.effective_message.reply_text(
                "Saya tidak dapat mempromosikan pengguna yang sudah menjadi admin federasi! Tapi saya bisa menurunkannya!",
            )
            return
        if user_id == bot.id:
            update.effective_message.reply_text(
                "Saya sudah menjadi admin federasi dan yang mengelolanya!",
            )
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("Berhasil dinaikan jabatannya!")
        else:
            update.effective_message.reply_text("Gagal dipromosikan!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")


def user_demote_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari pesan ini")
            return
        else:
            LOGGER.warning("error")

        if user_id == bot.id:
            update.effective_message.reply_text(
                "Hal yang Anda coba turunkan dari saya akan gagal bekerja tanpa saya! Hanya mengatakan.",
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) is False:
            update.effective_message.reply_text(
                "Saya tidak dapat menurunkan orang yang bukan admin federasi!",
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res is True:
            update.effective_message.reply_text("Diturunkan dari Admin Fed!")
        else:
            update.effective_message.reply_text("Gagal diturunkan!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return


def fed_info(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if args:
        fed_id = args[0]
        info = sql.get_fed_info(fed_id)
    else:
        if chat.type == "private":
            send_message(
                update.effective_message,
                "Anda perlu memberi saya fedid untuk memeriksa fedinfo di pm saya.",
            )
            return
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            send_message(
                update.effective_message,
                "Grup ini tidak tergabung dalam federasi manapun!",
            )
            return
        info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ Info federasi:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nNama: {}".format(info["fname"])
    text += "\nPembuat: {}".format(mention_html(owner.id, owner_name))
    text += "\nSeluruh admin: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal yang di banned: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nTotal grup yang terkoneksi: <code>{}</code>".format(
        len(getfchat),
    )

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_admin(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak dalam federasi apa pun!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>Admin Federasi {}:</b>\n\n".format(info["fname"])
    text += "👑 Owner:\n"
    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 Tidak ada admin di federasi ini"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = bot.get_chat(x)
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_ban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini tidak dalam federasi apa pun!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    message = update.effective_message

    user_id, reason = extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna")
        return

    if user_id == bot.id:
        message.reply_text(
            "Apa yang lebih lucu dari menendang creator grup? Fban diri saya sendiri.",
        )
        return

    if is_user_fed_owner(fed_id, user_id) is True:
        message.reply_text("Mengapa Anda mencoba fban pemilik federasi?")
        return

    if is_user_fed_admin(fed_id, user_id) is True:
        message.reply_text("Dia adalah admin dari federasi, saya tidak bisa fban dia.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Aku tidak ingin memblokir tuanku, itu ide yang sangat bodoh!")
        return

    if int(user_id) in DRAGONS:
        message.reply_text("Saya tidak akan fban pengguna Dragons!")
        return

    if int(user_id) in TIGERS:
        message.reply_text("Saya tidak akan fban pengguna Tigers!")
        return

    if int(user_id) in WOLVES:
        message.reply_text("Saya tidak akan fban pengguna Wolves!")
        return

    if user_id in [777000, 1087968824]:
        message.reply_text("Bodoh! Anda tidak dapat menyerang teknologi asli Telegram!")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        if len(str(user_id)) != 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        send_message(update.effective_message, "Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    if fban:
        fed_name = info["fname"]
        # https://t.me/OnePunchSupport/41606 // https://t.me/OnePunchSupport/41619
        # starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
        # send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

        # if reason == "":
        #    reason = "No reason given."

        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            message.reply_text("Gagal mengupdate alasan fedban!")
            return
        x = sql.fban_user(
            fed_id,
            fban_user_id,
            fban_user_name,
            fban_user_lname,
            fban_user_uname,
            reason,
            int(time.time()),
        )
        if not x:
            message.reply_text(
                f"Gagal melarangan federasi! Jika masalah ini terus terjadi, hubungi pembuat saya.",
            )
            return

        fed_chats = sql.all_fed_chats(fed_id)
        # Will send to current chat
        bot.send_message(
            chat.id,
            "<b>Alasan FedBan Diperbarui</b>" \
            "\n<b>Federasi:</b> {}" \
            "\n<b>Federasi Admin:</b> {}" \
            "\n<b>Pengguna:</b> {}" \
            "\n<b>Pengguna ID:</b> <code>{}</code>" \
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
        # Send message to owner if fednotif is enabled
        if getfednotif:
            bot.send_message(
                info["owner"],
                "<b>Alasan FedBan Diperbarui</b>" \
                "\n<b>Federasi:</b> {}" \
                "\n<b>Federasi Admin:</b> {}" \
                "\n<b>Pengguna:</b> {}" \
                "\n<b>Pengguna ID:</b> <code>{}</code>" \
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
        # If fedlog is set, then send message, except fedlog is current chat
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if int(get_fedlog) != int(chat.id):
                bot.send_message(
                    get_fedlog,
                    "<b>Alasan FedBan Diperbarui</b>" \
                    "\n<b>Federasi:</b> {}" \
                    "\n<b>Federasi Admin:</b> {}" \
                    "\n<b>Pengguna:</b> {}" \
                    "\n<b>Pengguna ID:</b> <code>{}</code>" \
                    "\n<b>Alasan:</b> {}".format(
                        fed_name,
                        mention_html(user.id, user.first_name),
                        user_target,
                        fban_user_id,
                        reason,
                    ),
                    parse_mode="HTML",
                )
        for fedschat in fed_chats:
            try:
                # Do not spam all fed chats
                """
				bot.send_message(chat, "<b>Alasan FedBan Diperbarui</b>" \
							 "\n<b>Federasi:</b> {}" \
							 "\n<b>Federasi Admin:</b> {}" \
							 "\n<b>Pengguna:</b> {}" \
							 "\n<b>Pengguna ID:</b> <code>{}</code>" \
							 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
                bot.kick_chat_member(fedschat, fban_user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    try:
                        dispatcher.bot.getChat(fedschat)
                    except Unauthorized:
                        sql.chat_leave_fed(fedschat)
                        LOGGER.info(
                            "Obrolan {} telah meninggalkan fed {} karena aku ditendang".format(
                                fedschat,
                                info["fname"],
                            ),
                        )
                        continue
                elif excp.message == "User_id_invalid":
                    break
                else:
                    LOGGER.warning(
                        "Tidak dapat fban di {} karena: {}".format(chat, excp.message),
                    )
            except TelegramError:
                pass
        # Also do not spam all fed admins
        """
		send_to_list(bot, FEDADMIN,
          "<b>Alasan FedBan Diperbarui</b>" \
          "\n<b>Federasi:</b> {}" \
          "\n<b>Federasi Admin:</b> {}" \
          "\n<b>Pengguna:</b> {}" \
          "\n<b>Pengguna ID:</b> <code>{}</code>" \
          "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
          html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Obrolan {} telah meninggalkan fed {} karena aku ditendang".format(
                                        fedschat,
                                        info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Tidak dapat fban di {} karena: {}".format(
                                    fedschat,
                                    excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
        # send_message(update.effective_message, "Alasan Fedban telah diperbarui.")
        return

    fed_name = info["fname"]

    # starting = "Memulai larangan federasi untuk {} di Federasi <b>{}</b>.".format(
    #    user_target, fed_name)
    # update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    # if reason == "":
    #    reason = "Tidak ada alasan yang diberikan."

    x = sql.fban_user(
        fed_id,
        fban_user_id,
        fban_user_name,
        fban_user_lname,
        fban_user_uname,
        reason,
        int(time.time()),
    )
    if not x:
        message.reply_text(
            f"Tidak dapat membuat federasi! Tolong hubungi pembuat saya jika masalah masih berlanjut.",
        )
        return

    fed_chats = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>FedBan baru</b>"
        "\n<b>Federasi:</b> {}" \
        "\n<b>Federasi Admin:</b> {}" \
        "\n<b>Pengguna:</b> {}" \
        "\n<b>Pengguna ID:</b> <code>{}</code>" \
        "\n<b>Alasan:</b> {}".format(
            fed_name,
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
            reason,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>FedBan baru</b>"
            "\n<b>Federasi:</b> {}" \
            "\n<b>Federasi Admin:</b> {}" \
            "\n<b>Pengguna:</b> {}" \
            "\n<b>Pengguna ID:</b> <code>{}</code>" \
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>FedBan baru</b>"
                "\n<b>Federasi:</b> {}" \
                "\n<b>Federasi Admin:</b> {}" \
                "\n<b>Pengguna:</b> {}" \
                "\n<b>Pengguna ID:</b> <code>{}</code>" \
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
    chats_in_fed = 0
    for fedschat in fed_chats:
        chats_in_fed += 1
        try:
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Alasan FedBan Diperbarui</b>" \
							"\n<b>Federasi:</b> {}" \
                            "\n<b>Federasi Admin:</b> {}" \
                            "\n<b>Pengguna:</b> {}" \
                            "\n<b>Pengguna ID:</b> <code>{}</code>" \
							"\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
            bot.kick_chat_member(fedschat, fban_user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Tidak dapat mem-fban {} karena: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

        # Also do not spamming all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>Alasan FedBan Diperbarui</b>" \
   			     "\n<b>Federasi:</b> {}" \
                 "\n<b>Federasi Admin:</b> {}" \
                 "\n<b>Pengguna:</b> {}" \
                 "\n<b>Pengguna ID:</b> <code>{}</code>" \
				 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Obrolan {} telah meninggalkan fed {} karena aku ditendang".format(
                                        fedschat,
                                        info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Tidak dapat mem-fban {} karena: {}".format(
                                    fedschat,
                                    excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
    # if chats_in_fed == 0:
    #    send_message(update.effective_message, "Fedban affected 0 chats. ")
    # elif chats_in_fed > 0:
    #    send_message(update.effective_message,
    #                 "Fedban affected {} chats. ".format(chats_in_fed))


def unfban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Obrolan ini tidak ada di federasi apa pun!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user_id = extract_user_fban(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna.")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        if len(str(user_id)) != 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
    if fban is False:
        message.reply_text("Pengguna ini tidak di fbanned!")
        return

    banner = update.effective_user

    # message.reply_text("I'll give {} another chance in this federation".format(user_chat.first_name))

    chat_list = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>Un-FedBan</b>"
        "\n<b>Federasi:</b> {}" \
        "\n<b>Federasi Admin:</b> {}" \
        "\n<b>Pengguna:</b> {}" \
        "\n<b>Pengguna ID:</b> <code>{}</code>".format(
            info["fname"],
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>Un-FedBan</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Federasi Admin:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>Pengguna ID:</b> <code>{}</code>".format(
                info["fname"],
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>Un-FedBan</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Federasi Admin:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>Pengguna ID:</b> <code>{}</code>".format(
                    info["fname"],
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                ),
                parse_mode="HTML",
            )
    unfbanned_in_chats = 0
    for fedchats in chat_list:
        unfbanned_in_chats += 1
        try:
            member = bot.get_chat_member(fedchats, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(fedchats, user_id)
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Tidak dapat fban di {} karena: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

    try:
        x = sql.un_fban_user(fed_id, user_id)
        if not x:
            send_message(
                update.effective_message,
                "Gagal fban, Pengguna ini mungkin sudah di un-fedbanned!",
            )
            return
    except:
        pass

    # UnFban for fed subscriber
    subscriber = list(sql.get_subscriber(fed_id))
    if len(subscriber) != 0:
        for fedsid in subscriber:
            all_fedschat = sql.all_fed_chats(fedsid)
            for fedschat in all_fedschat:
                try:
                    bot.unban_chat_member(fedchats, user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.getChat(fedschat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedschat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            LOGGER.info(
                                "Obrolan {} telah meninggalkan fed {} karena aku ditendang".format(
                                    fedschat,
                                    info["fname"],
                                ),
                            )
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        LOGGER.warning(
                            "Tidak dapat fban di {} karena: {}".format(
                                fedschat,
                                excp.message,
                            ),
                        )
                except TelegramError:
                    pass

    if unfbanned_in_chats == 0:
        send_message(
            update.effective_message,
            "Orang ini telah dihapus fbannya di 0 obrolan.",
        )
    if unfbanned_in_chats > 0:
        send_message(
            update.effective_message,
            "Orang ini telah dihapus fbannya di {} obrolan.".format(unfbanned_in_chats),
        )
    # Also do not spamming all fed admins
    """
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport is False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Un-FedBan</b>" \
			 "\n<b>Federasi:</b> {}" \
			 "\n<b>Federasi Admin:</b> {}" \
			 "\n<b>Pengguna:</b> {}" \
			 "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												 mention_html(user_chat.id, user_chat.first_name),
															  user_chat.id),
			html=True)
	"""


def set_frules(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Obrolan ini tidak ada di federasi apa pun!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    if len(args) >= 1:
        msg = update.effective_message
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(
                txt,
                entities=msg.parse_entities(),
                offset=offset,
            )
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text(
                f"Ada kesalahan saat menetapkan aturan federasi! Jika Anda bertanya-tanya mengapa, silakan tanyakan di grup pendukung!",
            )
            return

        rules = sql.get_fed_info(fed_id)["frules"]
        getfed = sql.get_fed_info(fed_id)
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "*{}* telah mengganti aturan federasi *{}*".format(
                        user.first_name,
                        getfed["fname"],
                    ),
                    parse_mode="markdown",
                )
        update.effective_message.reply_text(f"Aturan telah diubah menjadi :\n{rules}!")
    else:
        update.effective_message.reply_text("Silakan tulis aturan untuk mengaturnya!")


def get_frules(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak dalam federasi apa pun!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Peraturan di fed ini:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def fed_broadcast(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    if args:
        chat = update.effective_chat
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        if is_user_fed_owner(fed_id, user.id) is False:
            update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
            return
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text = text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            title = "*Siaran baru dari Federasi {}*\n".format(fedinfo["fname"])
            try:
                bot.sendMessage(chat, title + text, parse_mode="markdown")
            except TelegramError:
                try:
                    dispatcher.bot.getChat(chat)
                except Unauthorized:
                    failed += 1
                    sql.chat_leave_fed(chat)
                    LOGGER.info(
                        "Obrolan {} telah meninggalkan fed {} karena aku ditendang".format(
                            chat,
                            fedinfo["fname"],
                        ),
                    )
                    continue
                failed += 1
                LOGGER.warning("Tidak dapat mengirim siaran ke {}".format(str(chat)))

        send_text = "Siaran Federasi selesai"
        if failed >= 1:
            send_text += "{} grup gagal menerima pesan, mungkin karena meninggalkan federasi.".format(
                failed,
            )
        update.effective_message.reply_text(send_text)


def fed_ban_list(update: Update, context: CallbackContext):
    bot, args, chat_data = context.bot, context.args, context.chat_data
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini tidak dalam federasi apa pun!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    user = update.effective_user
    chat = update.effective_chat
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang di fban di federasi {}".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    if args:
        if args[0] == "json":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y",
                        time.localtime(cek.get("value")),
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`".format(
                            waktu,
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {
                    "user_id": users,
                    "first_name": getuserinfo["first_name"],
                    "last_name": getuserinfo["last_name"],
                    "user_name": getuserinfo["user_name"],
                    "reason": getuserinfo["reason"],
                }
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "emilia_fbanned_users.json"
                update.effective_message.reply_document(
                    document=output,
                    filename="emilia_fbanned_users.json",
                    caption="Total {} pengguna terkena blokir federasi {}.".format(
                        len(getfban),
                        info["fname"],
                    ),
                )
            return
        if args[0] == "csv":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y",
                        time.localtime(cek.get("value")),
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`".format(
                            waktu,
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += (
                    "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                        user_id=users,
                        first_name=getuserinfo["first_name"],
                        last_name=getuserinfo["last_name"],
                        user_name=getuserinfo["user_name"],
                        reason=getuserinfo["reason"],
                    )
                )
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "emilia_fbanned_users.csv"
                update.effective_message.reply_document(
                    document=output,
                    filename="emilia_fbanned_users.csv",
                    caption="Total {} pengguna terkena blokir federasi {}.".format(
                        len(getfban),
                        info["fname"],
                    ),
                )
            return

    text = "<b>Ada {} pengguna yang di fban pada federasi {}:</b>\n".format(
        len(getfban),
        info["fname"],
    )
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo is False:
            text = "Tidak ada pengguna yang di fban di federasi {}".format(
                info["fname"],
            )
            break
        user_name = getuserinfo["first_name"]
        if getuserinfo["last_name"]:
            user_name += " " + getuserinfo["last_name"]
        text += " • {} (<code>{}</code>)\n".format(
            mention_html(users, user_name),
            users,
        )

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y",
                    time.localtime(cek.get("value")),
                )
                update.effective_message.reply_text(
                    "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`".format(
                        waktu,
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fbanlist.txt",
                caption="Berikut adalah daftar pengguna yang saat ini difban pada federasi {}.".format(
                    info["fname"],
                ),
            )


def fed_notif(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini tidak dalam federasi apa pun!",
        )
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            msg.reply_text(
                "Pelaporan federasi hidup! Setiap ada pengguna yang di fban/unfban anda akan di beritahu via PM.",
            )
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            msg.reply_text(
                "Pelaporan federasi mati! Setiap ada pengguna yang di fban/unfban anda tidak akan di beritahu via PM.",
            )
        else:
            msg.reply_text("Tolong masukan `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        msg.reply_text(
            "Preferensi laporan federasi anda saat ini: `{}`".format(getreport),
            parse_mode="markdown",
        )


def fed_chats(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini tidak dalam federasi apa pun!",
        )
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        update.effective_message.reply_text(
            "Tidak ada obrolan yang bergabung pada federasi {}".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    text = "<b>Obrolan yang bergabung pada federasi {}:</b>\n".format(info["fname"])
    for chats in getlist:
        try:
            chat_name = dispatcher.bot.getChat(chats).title
        except Unauthorized:
            sql.chat_leave_fed(chats)
            LOGGER.info(
                "Obrolan {} telah meninggalkan federasi {} karena aku ditendang".format(
                    chats,
                    info["fname"],
                ),
            )
            continue
        text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fedchats.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fedchats.txt",
                caption="Berikut adalah daftar obrolan yang bergabung federasi {}.".format(
                    info["fname"],
                ),
            )


def fed_import_bans(update: Update, context: CallbackContext):
    bot, chat_data = context.bot, context.chat_data
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)
    getfed = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini tidak dalam federasi apa pun!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y",
                    time.localtime(cek.get("value")),
                )
                update.effective_message.reply_text(
                    "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`".format(
                        waktu,
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        # if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
        # 	msg.reply_text("This file is too big!")
        # 	return
        success = 0
        failed = 0
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text(
                "Coba unduh dan unggah ulang filenya, yang ini sepertinya rusak!",
            )
            return
        fileformat = msg.reply_to_message.document.file_name.split(".")[-1]
        if fileformat == "json":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError as err:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data["user_id"])  # Make sure it int
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in DRAGONS:
                        failed += 1
                        continue
                    if int(import_userid) in TIGERS:
                        failed += 1
                        continue
                    if int(import_userid) in WOLVES:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            text = "Berkas blokir berhasil diimpor. {} orang diblokir.".format(
                success,
            )
            if failed >= 1:
                text += " {} Gagal mengimpor.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Federasi *{}* telah berhasil mengimpor data. {} di blokir.".format(
                        getfed["fname"],
                        success,
                    )
                    if failed >= 1:
                        teks += " {} gagal di impor.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        elif fileformat == "csv":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            file_info.download(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
            )
            with open(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
                "r",
                encoding="utf8",
            ) as csvFile:
                reader = csv.reader(csvFile)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in DRAGONS:
                        failed += 1
                        continue
                    if int(import_userid) in TIGERS:
                        failed += 1
                        continue
                    if int(import_userid) in WOLVES:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                    # t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
                    # t.start()
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            csvFile.close()
            os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
            text = "Berkas blokir berhasil diimpor. {} orang diblokir.".format(success)
            if failed >= 1:
                text += " {} gagal di impor.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Federasi *{}* telah berhasil mengimpor data. {} di blokir.".format(
                        getfed["fname"],
                        success,
                    )
                    if failed >= 1:
                        teks += " {} gagal di impor.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        else:
            send_message(update.effective_message, "File tidak di dukung.")
            return
        send_message(update.effective_message, text)


def del_fed_button(update: Update, context: CallbackContext):
    query = update.callback_query
    userid = query.message.chat.id
    fed_id = query.data.split("_")[1]

    if fed_id == "cancel":
        query.message.edit_text("Penghapusan federasi dibatalkan")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
        delete = sql.del_fed(fed_id)
        if delete:
            query.message.edit_text(
                "Anda telah menghapus federasi Anda! Sekarang semua Grup yang terhubung dengan `{}` sekarang tidak memiliki federasi.".format(
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )


def fed_stat_user(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args:
        if args[0].isdigit():
            user_id = args[0]
        else:
            user_id = extract_user(msg, args)
    else:
        user_id = extract_user(msg, args)

    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
            if fbantime:
                fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
            else:
                fbantime = "Unavaiable"
            if user_name is False:
                send_message(
                    update.effective_message,
                    "Federasi {} tidak di temukan!".format(fed_id),
                    parse_mode="markdown",
                )
                return
            if user_name == "" or user_name is None:
                user_name = "Dia"
            if not reason:
                send_message(
                    update.effective_message,
                    "{} belum di larang di federasi ini!".format(user_name),
                )
            else:
                teks = "{} di larang di federasi ini karena:\n`{}`\n*Di banned pada:* `{}`".format(
                    user_name,
                    reason,
                    fbantime,
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
            return
        user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
        if user_name == "":
            try:
                user_name = bot.get_chat(user_id).first_name
            except BadRequest:
                user_name = "dia"
            if user_name == "" or user_name is None:
                user_name = "dia"
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} belum di larang di federasi mana pun!".format(user_name),
            )
            return
        teks = "{} sudah di larang di federasi ini:\n".format(user_name)
        for x in fbanlist:
            teks += "- `{}`: {}\n".format(x[0], x[1][:20])
        teks += "\nJika anda ingin mengetahui lebih lanjut tentang alasan fedban dengan spesifik, gunakan /fbanstat <FedID>"
        send_message(update.effective_message, teks, parse_mode="markdown")

    elif not msg.reply_to_message and not args:
        user_id = msg.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = msg.from_user.first_name
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} belum di larang di federasi mana pun!".format(user_name),
            )
        else:
            teks = "{} sudah di larang di federasi ini:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nJika anda ingin mengetahui lebih lanjut tentang alasan fedban dengan spesifik, gunakan /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            send_message(update.effective_message, "Federasi {} tidak di temukan!".format(fed_id))
            return
        name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
        if fbantime:
            fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
        else:
            fbantime = "Unavaiable"
        if not name:
            name = msg.from_user.first_name
        if not reason:
            send_message(
                update.effective_message,
                "{} tidak di larang di federasi ini".format(name),
            )
            return
        send_message(
            update.effective_message,
            "{} di larang di federasi ini karena:\n`{}`\n*Di banned pada:* `{}`".format(
                name,
                reason,
                fbantime,
            ),
            parse_mode="markdown",
        )


def set_fed_log(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pencipta federasi yang bisa menetapkan log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], chat.id)
        if setlog:
            send_message(
                update.effective_message,
                "Log federasi `{}` telah di setel pada {}".format(
                    fedinfo["fname"],
                    chat.title,
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasinya!",
        )


def unset_fed_log(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pencipta federasi yang bisa menetapkan log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], None)
        if setlog:
            send_message(
                update.effective_message,
                "Log federasi `{}` telah di cabut pada {}".format(
                    fedinfo["fname"],
                    chat.title,
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasinya!",
        )


def subs_feds(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak dalam federasi apa pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message,
                "Silakan masukkan id federasi yang valid.",
            )
            return
        subfed = sql.subs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federasi `{}` telah mengikuti federasi `{}`. Setiap ada fedban dari federasi tersebut, federasi ini juga akan banned pengguna tsb.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federasi `{}` telah mengikuti federasi `{}`".format(
                            fedinfo["fname"],
                            getfed["fname"],
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federasi `{}` telah mengikuti federasi `{}`.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasinya!",
        )


def unsubs_feds(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak dalam federasi apa pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message,
                "Silakan masukkan id federasi yang valid.",
            )
            return
        subfed = sql.unsubs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federasi `{}` sudah tidak mengikuti `{}` lagi.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federasi `{}` sudah tidak mengikuti `{}` lagi.".format(
                            fedinfo["fname"],
                            getfed["fname"],
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federasi `{}` sudah tidak mengikuti `{}` lagi.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasinya!",
        )


def get_myfedsubs(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini di khususkan untuk grup, bukan pada PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Grup ini tidak dalam federasi apa pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!")
        return

    try:
        getmy = sql.get_mysubs(fed_id)
    except:
        getmy = []

    if len(getmy) == 0:
        send_message(
            update.effective_message,
            "Federasi `{}` tidak mengikuti federasi apapun.".format(
                fedinfo["fname"],
            ),
            parse_mode="markdown",
        )
        return
    listfed = "Federasi `{}` mengikuti federasi berikut ini:\n".format(
        fedinfo["fname"],
    )
    for x in getmy:
        listfed += "- `{}`\n".format(x)
    listfed += (
        "\nUntuk info federasi, ketik `/fedinfo <fedid>`. Untuk berhenti berlangganan ketik `/unsubfed <fedid>`."
    )
    send_message(update.effective_message, listfed, parse_mode="markdown")


def get_myfeds_list(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    fedowner = sql.get_user_owner_fed_full(user.id)
    if fedowner:
        text = "*Ini adalah federasi milik anda:\n*"
        for f in fedowner:
            text += "- `{}`: *{}*\n".format(f["fed_id"], f["fed"]["fname"])
    else:
        text = "*Anda tidak mempunyai federasi!*"
    send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins is False:
        return False
    return bool(int(user_id) in fed_admins or int(user_id) == OWNER_ID)


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql is False:
        return False
    getfedowner = ast.literal_eval(getsql["fusers"])
    if getfedowner is None or getfedowner is False:
        return False
    getfedowner = getfedowner["owner"]
    return bool(str(user_id) == getfedowner or int(user_id) == OWNER_ID)


# There's no handler for this yet, but updating for v12 in case its used
def welcome_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text(
            "This user is banned in current federation! I will remove him.",
        )
        bot.kick_chat_member(chat.id, user.id)
        return True
    return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "{} pengguna di fbanned, pada {} federasi".format(
        len(all_fbanned),
        len(all_feds),
    )


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]

        if int(info["owner"]) == user_id:
            text = "Pengguna ini adalah owner di federasi saat ini: <b>{}</b>.".format(infoname)
        elif is_user_fed_admin(fed_id, user_id):
            text = "Pengguna ini adalah admin di federasi saat ini: <b>{}</b>.".format(infoname)

        elif fban:
            text = "Dilarang di federasi saat ini: <b>Ya</b>"
            text += "\n<b>Alasan:</b> {}".format(fbanreason)
        else:
            text = "Dilarang di federasi saat ini: <b>Tidak</b>"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    if value is False:
        status = False
    else:
        status = True
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        value = chat_data[chat_id]["federation"]
        return value
    except KeyError:
        return {"status": False, "value": False}


def fed_owner_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """👑 *Hanya Pemilik Federasi:*
 ✧ /newfed <nama_fed>*:* Membuat Federasi, Satu diizinkan per pengguna.
 ✧ /renamefed <id_fed> <nama_fed_baru>*:* Mengganti nama id Federasi menjadi nama baru.
 ✧ /delfed <id_fed>`*:* Hapus Federasi, dan informasi apa pun yang terkait dengannya. Tidak akan membatalkan pengguna yang diblokir.
 ✧ /fpromote <pengguna>*:* Menetapkan pengguna sebagai admin federasi. Mengaktifkan semua perintah untuk pengguna di bawah `Admin Federasi.`
 ✧ /fdemote <pengguna>*:* Menurunkan jabatan Pengguna dari Federasi admin menjadi Pengguna biasa.
 ✧ /subfed <id_fed>*:* Berlangganan ke ID Federasi tertentu, larangan dari fed yang berlangganan itu juga akan terjadi di Fed Anda.
 ✧ /unsubfed <id_fed>*:* Berhenti berlangganan ID fed tertentu.
 ✧ /setfedlog <id_fed>*:* Menetapkan grup sebagai basis laporan log Fed untuk federasi.
 ✧ /unsetfedlog <id_fed>*:* Menghapus grup sebagai basis laporan log fed untuk federasi.
 ✧ /fbroadcast <pesan>*:* Menyiarkan pesan ke semua grup yang telah bergabung dengan fed Anda
 ✧ /fedsubs*:* Menunjukkan federasi yang menjadi langganan grup Anda.""",
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_admin_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """🔱 *Admin Federasi:*
 ✧ /fban <pengguna> <reason>*:* Federasi melarang pengguna.
 ✧ /unfban <pengguna> <reason>`*:* Menghapus pengguna dari larangan Fed.
 ✧ /fedinfo <fed_id>*:* Informasi tentang Federasi yang ditentukan.
 ✧ /joinfed <id_fed>*:* Bergabunglah dengan obrolan saat ini ke Federasi. Hanya pemilik obrolan yang dapat melakukan ini. Setiap obrolan hanya bisa dalam satu Federasi.
 ✧ /leavefed <id_fed>*:* Tinggalkan Federasi yang diberikan. Hanya pemilik obrolan yang dapat melakukan ini.
 ✧ /setfrules <aturan>*:* Aturan Federasi.
 ✧ /fedadmins*:* Tampilkan admin Federasi.
 ✧ /fbanlist*:* Menampilkan semua pengguna yang menjadi korban di Federasi saat ini.
 ✧ /fedchats*:* Dapatkan semua obrolan yang terhubung di Federasi.
 ✧ /chatfed*:* Lihat Federasi di obrolan saat ini\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_user_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """🎩 *Setiap pengguna:*
 ✧ /fbanstat*:* Menunjukkan apakah Anda/atau pengguna yang Anda balas atau nama pengguna mereka diblokir di suatu tempat atau tidak.
 ✧ /fednotif <on/off>*:* Pengaturan federasi tidak di PM ketika ada pengguna yang fbaned/unfbanned.
 ✧ /frules*:* Lihat peraturan Federasi\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


__help__ = """
Semuanya menyenangkan, sampai spammer mulai memasuki grup Anda, dan Anda harus memblokirnya. Maka Anda harus mulai melarang lebih banyak, dan lebih banyak lagi, dan itu menyakitkan.
Tapi kemudian Anda memiliki banyak grup, dan Anda tidak ingin spammer ini berada di salah satu grup Anda - bagaimana Anda bisa menanganinya? Apakah Anda harus memblokirnya secara manual, di semua grup Anda?
*Tidak lagi!* Dengan Federasi, Anda dapat membuat larangan dalam satu obrolan yang tumpang tindih dengan semua obrolan lainnya.
Anda bahkan dapat menunjuk admin federasi, sehingga admin tepercaya Anda dapat melarang semua spammer dari obrolan yang ingin Anda lindungi.

✦ *Perintah:*
✧ /fedownerhelp*:* Memberikan bantuan untuk pembuatan Fed dan perintah pemilik saja.
✧ /fedadminhelp*:* Memberikan bantuan untuk perintah administrasi Fed.
✧ /feduserhelp*:* Memberikan bantuan untuk perintah yang dapat digunakan siapa saja.

Federasi sekarang dibagi menjadi 3 bagian untuk kemudahan Anda.
"""

__mod_name__ = "Federations"


NEW_FED_HANDLER = CommandHandler("newfed", new_fed, run_async=True)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, run_async=True)
RENAME_FED = CommandHandler("renamefed", rename_fed, run_async=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, run_async=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, run_async=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, run_async=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, run_async=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, run_async=True)
BAN_FED_HANDLER = DisableAbleCommandHandler("fban", fed_ban, run_async=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, run_async=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, run_async=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, run_async=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, run_async=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, run_async=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, run_async=True)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, run_async=True)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, run_async=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, run_async=True)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, run_async=True)
FEDSTAT_USER = DisableAbleCommandHandler(
    ["fedstat", "fbanstat"], fed_stat_user, run_async=True
)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, run_async=True)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, run_async=True)
SUBS_FED = CommandHandler("subfed", subs_feds, run_async=True)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, run_async=True)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, run_async=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list, run_async=True)
DELETEBTN_FED_HANDLER = CallbackQueryHandler(
    del_fed_button, pattern=r"rmfed_", run_async=True
)
FED_OWNER_HELP_HANDLER = CommandHandler("fedownerhelp", fed_owner_help, run_async=True)
FED_ADMIN_HELP_HANDLER = CommandHandler("fedadminhelp", fed_admin_help, run_async=True)
FED_USER_HELP_HANDLER = CommandHandler("feduserhelp", fed_user_help, run_async=True)

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(RENAME_FED)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
# dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(FEDSTAT_USER)
dispatcher.add_handler(SET_FED_LOG)
dispatcher.add_handler(UNSET_FED_LOG)
dispatcher.add_handler(SUBS_FED)
dispatcher.add_handler(UNSUBS_FED)
dispatcher.add_handler(MY_SUB_FED)
dispatcher.add_handler(MY_FEDS_LIST)
dispatcher.add_handler(DELETEBTN_FED_HANDLER)
dispatcher.add_handler(FED_OWNER_HELP_HANDLER)
dispatcher.add_handler(FED_ADMIN_HELP_HANDLER)
dispatcher.add_handler(FED_USER_HELP_HANDLER)
