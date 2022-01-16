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

import html
from typing import Optional, List
import re

from telegram import Message, Chat, Update, User, ChatPermissions

from emilia import TIGERS, WOLVES, dispatcher
from emilia.modules.helper_funcs.chat_status import (
    bot_admin,
    is_user_admin,
    user_admin,
    user_admin_no_reply,
)
from emilia.modules.log_channel import loggable
from emilia.modules.sql import antiflood_sql as sql
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import mention_html
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.connection import connected
from emilia.modules.helper_funcs.alternate import send_message
from emilia.modules.sql.approve_sql import is_approved

FLOOD_GROUP = 3


@loggable
def check_flood(update, context) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    if not user:  # ignore channels
        return ""

    # ignore admins and whitelists
    if is_user_admin(chat, user.id) or user.id in WOLVES or user.id in TIGERS:
        sql.update_flood(chat.id, None)
        return ""
    # ignore approved users
    if is_approved(chat.id, user.id):
        sql.update_flood(chat.id, None)
        return
    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.ban_member(user.id)
            execstrings = "Keluar!"
            tag = "BANNED"
        elif getmode == 2:
            chat.ban_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Keluar!"
            tag = "KICKED"
        elif getmode == 3:
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Sekarang kamu diam"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.ban_member(user.id, until_date=bantime)
            execstrings = "Keluar selama {}".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Sekarang kamu diam selama {}".format(getvalue)
            tag = "TMUTE"
        send_message(
            update.effective_message,
            "Saya tidak suka orang yang mengirim pesan beruntun. Tapi kamu hanya membuat! saya kecewa!\n{}!".format(execstrings),
        )

        return (
            "<b>{}:</b>"
            "\n#{}"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                tag,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )

    except BadRequest:
        msg.reply_text(
            "Saya tidak bisa menendang orang di sini, beri saya izin terlebih dahulu! Sampai saat itu, saya akan menonaktifkan antiflood.",
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nTidak memiliki izin kick, jadi secara otomatis menonaktifkan antiflood".format(
                chat.title,
            )
        )


@user_admin_no_reply
@bot_admin
def flood_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat.id
        try:
            bot.restrict_chat_member(
                chat,
                int(user_id),
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            update.effective_message.edit_text(
                f"Disuarakan oleh {mention_html(user.id, html.escape(user.first_name))}.",
                parse_mode="HTML",
            )
        except:
            pass


@user_admin
@loggable
def set_flood(update, context) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Anda bisa lakukan command ini pada grup, bukan pada PM",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text(
                    "Antiflood telah dinonaktifkan di {}.".format(chat_name),
                )
            else:
                text = message.reply_text("Antiflood telah dinonaktifkan.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text(
                        "Antiflood telah dinonaktifkan di {}.".format(chat_name),
                    )
                else:
                    text = message.reply_text("Antiflood telah dinonaktifkan.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nDisable antiflood.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                    )
                )

            if amount <= 3:
                send_message(
                    update.effective_message,
                    "Antiflood harus baik 0 (dinonaktifkan), atau nomor lebih besar dari 3!",
                )
                return ""
            sql.set_flood(chat_id, amount)
            if conn:
                text = message.reply_text(
                    "Antiflood telah diperbarui dan diatur menjadi {} pada: {}".format(
                        amount,
                        chat_name,
                    ),
                )
            else:
                text = message.reply_text(
                    "Antiflood telah diperbarui dan diatur menjadi {}!".format(amount),
                )
            return (
                "<b>{}:</b>"
                "\n#SETFLOOD"
                "\n<b>Admin:</b> {}"
                "\nSet antiflood to <code>{}</code>.".format(
                    html.escape(chat_name),
                    mention_html(user.id, html.escape(user.first_name)),
                    amount,
                )
            )

        else:
            message.reply_text("Argumen tidak dikenal - harap gunakan angka, 'off' atau 'no'")
    else:
        message.reply_text(
            (
                "Gunakan `/setflood nomor` untuk menyetel anti pesan beruntun.\nAtau gunakan `/setflood off` untuk menonaktifkan anti pesan beruntun!."
            ),
            parse_mode="markdown",
        )
    return ""


def flood(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Anda bisa lakukan command ini pada grup, bukan pada PM",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = msg.reply_text(
                "Saat ini saya tidak memberlakukan pengendalian pesan beruntun pada {}!".format(chat_name),
            )
        else:
            text = msg.reply_text("Saat ini saya tidak memberlakukan pengendalian pesan beruntun!")
    else:
        if conn:
            text = msg.reply_text(
                "Saat ini saya melarang pengguna jika mereka mengirim lebih dari {} pesan berturut-turut pada {}.".format(
                    limit,
                    chat_name,
                ),
            )
        else:
            text = msg.reply_text(
                "Saat ini saya melarang pengguna jika mereka mengirim lebih dari {} pesan berturut-turut.".format(
                    limit,
                ),
            )


@user_admin
def set_flood_mode(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Anda bisa lakukan command ini pada grup, bukan pada PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "blokir"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "tendang"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "bisukan"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """Sepertinya Anda mencoba menetapkan nilai sementara untuk anti-banjir, tetapi belum menentukan waktu; gunakan `/setfloodmode tban <timevalue>`.
    Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "blokir sementara selama {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = (
                    update.effective_message,
                    """Sepertinya Anda mencoba menetapkan nilai sementara untuk anti-banjir, tetapi belum menentukan waktu; gunakan `/setfloodmode tban <timevalue>`.
    Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.""",
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "bisukan sementara selama {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(
                update.effective_message,
                "Saya hanya mengerti ban/kick/mute/tban/tmute!",
            )
            return
        if conn:
            text = msg.reply_text(
                "Terlalu banyak mengirim pesan sekarang akan menghasilkan {} pada {}!".format(
                    settypeflood,
                    chat_name,
                ),
            )
        else:
            text = msg.reply_text(
                "Terlalu banyak mengirim pesan sekarang akan menghasilkan {}!".format(
                    settypeflood,
                ),
            )
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Has changed antiflood mode. User will {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )
    getmode, getvalue = sql.get_flood_setting(chat.id)
    if getmode == 1:
        settypeflood = "blokir"
    elif getmode == 2:
        settypeflood = "tendang"
    elif getmode == 3:
        settypeflood = "bisukan"
    elif getmode == 4:
        settypeflood = "blokir sementara selama {}".format(getvalue)
    elif getmode == 5:
        settypeflood = "bisukan sementara selama {}".format(getvalue)
    if conn:
        text = msg.reply_text(
            "Jika member mengirim pesan beruntun, maka dia akan di {} pada {}.".format(
                settypeflood,
                chat_name,
            ),
        )
    else:
        text = msg.reply_text(
            "Jika member mengirim pesan beruntun, maka dia akan di {}.".format(
                settypeflood,
            ),
        )
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Saat ini *Tidak* menegakkan pengendalian pesan beruntun."
    return "Anti Pesan Beruntun diatur ke `{}` pesan.".format(limit)

__help__ = """
Anda tahu bagaimana terkadang, orang bergabung, mengirim 100 pesan, dan merusak obrolan Anda? Dengan antibanjir, itu tidak terjadi lagi!
Antiflood memungkinkan Anda untuk mengambil tindakan pada pengguna yang mengirim lebih dari x pesan berturut-turut. Tindakannya adalah: ban/kick/mute

✦ *Perintah admin:*
 ✧ /flood: Dapatkan pengaturan antibanjir saat ini.
 ✧ /setflood <number/off/no>: Tetapkan jumlah pesan yang akan diambil tindakan pada pengguna. Setel ke '0', 'nonaktif', atau 'tidak' untuk menonaktifkan.
 ✧ /setfloodmode <action type>: Pilih tindakan yang akan diambil terhadap pengguna yang telah membanjiri. Pilihan: ban/kick/mute.
 ✧ /delflood <yes/no/on/off>: Jika Anda ingin bot menghapus pesan yang dibanjiri pengguna.
"""

__mod_name__ = "Antiflood"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all & ~Filters.status_update & Filters.chat_type.groups,
    check_flood,
    run_async=True,
)
SET_FLOOD_HANDLER = CommandHandler(
    "setflood", set_flood, filters=Filters.chat_type.group, run_async=True
)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode",
    set_flood_mode,
    pass_args=True,
    run_async=True,
)  # , filters=Filters.chat_type.group)
FLOOD_QUERY_HANDLER = CallbackQueryHandler(
    flood_button, pattern=r"unmute_flooder", run_async=True
)
FLOOD_HANDLER = CommandHandler(
    "flood", flood, filters=Filters.chat_type.groups, run_async=True
)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(FLOOD_QUERY_HANDLER)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

__handlers__ = [
    (FLOOD_BAN_HANDLER, FLOOD_GROUP),
    SET_FLOOD_HANDLER,
    FLOOD_HANDLER,
    SET_FLOOD_MODE_HANDLER,
]
