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

from emilia import LOGGER, DRAGONS, TIGERS, WOLVES, dispatcher
from emilia.modules.helper_funcs.chat_status import user_admin, user_not_admin
from emilia.modules.log_channel import loggable
from emilia.modules.sql import reporting_sql as sql
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import mention_html

REPORT_GROUP = 12
REPORT_IMMUNE_USERS = DRAGONS + TIGERS + WOLVES


@user_admin
def report_setting(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "Menghidupkan pelaporan! Anda akan diberi tahu setiap kali ada yang melaporkan sesuatu.",
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Mematikan pelaporan! Anda tidak akan mendapatkan laporan apa pun.")
        else:
            msg.reply_text(
                f"Preferensi laporan Anda saat ini: `{sql.user_should_report(chat.id)}`",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text(
                    f"Mengaktifkan pelaporan di {chat.title}!\n\nAdmin yang telah mengaktifkan laporan akan diberi tahu ketika seseorang menyebut `/report` "
                    "or @admin is called.",
                )

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text(
                    f"Mematikan pelaporan di {chat.title}!\n\nTidak ada admin yang akan diberitahukan ketika seseorang menyebut `/report` atau @admin.",
                )
        else:
            msg.reply_text(
                f"Pengaturan obrolan saat ini adalah: `{sql.chat_should_report(chat.id)}`.\n\nUntuk mengubah pengaturan ini, coba perintah ini lagi, dengan salah satu argumen berikut: yes/no/on/off",
                parse_mode=ParseMode.MARKDOWN,
            )


@user_not_admin
@loggable
def report(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        message = update.effective_message

        if not args:
            message.reply_text("Tambahkan alasan untuk melaporkan terlebih dahulu.")
            return ""

        if user.id == reported_user.id:
            message.reply_text("Oh ya, tentu saja... sangat banyak?")
            return ""

        if user.id == bot.id:
            message.reply_text("Selamat mencoba.")
            return ""

        if reported_user.id in REPORT_IMMUNE_USERS:
            message.reply_text("eh? Anda melaporkan Asosiasi?")
            return ""

        if chat.username and chat.type == Chat.SUPERGROUP:

            reported = f"{mention_html(user.id, user.first_name)} dilaporkan {mention_html(reported_user.id, reported_user.first_name)} ke admin!"

            msg = (
                f"<b>Laporan: </b>{html.escape(chat.title)}\n"
                f"<b>Di laporkan oleh:</b> {mention_html(user.id, user.first_name)}(<code>{user.id}</code>)\n"
                f"<b>Pengguna yang dilaporkan:</b> {mention_html(reported_user.id, reported_user.first_name)} (<code>{reported_user.id}</code>)\n"
            )
            link = f'<b>Pesan yang dilaporkan:</b> <a href="https://t.me/{chat.username}/{message.reply_to_message.message_id}">Klik disini</a>'
            should_forward = False
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Pesan",
                        url=f"https://t.me/{chat.username}/{message.reply_to_message.message_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Tendang",
                        callback_data=f"report_{chat.id}=kick={reported_user.id}={reported_user.first_name}",
                    ),
                    InlineKeyboardButton(
                        "Banned",
                        callback_data=f"report_{chat.id}=banned={reported_user.id}={reported_user.first_name}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Hapus pesan",
                        callback_data=f"report_{chat.id}=delete={reported_user.id}={message.reply_to_message.message_id}",
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reported = (
                f"{mention_html(user.id, user.first_name)} "
                f"{mention_html(reported_user.id, reported_user.first_name)} Telah di laporkan ke semua admin!"
            )

            msg = f'{mention_html(user.id, user.first_name)} memanggil admin di "{html.escape(chat_name)}"!'
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    if not chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)
                    if not chat.username:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if chat.username and chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Pengecualian saat melaporkan pengguna")

        message.reply_to_message.reply_text(
            f"{mention_html(user.id, user.first_name)} laporkan pesan ke admin.",
            parse_mode=ParseMode.HTML,
        )
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, _):
    return f"Obrolan ini disetel untuk mengirim laporan pengguna ke admin, melalui /report dan @admin: `{sql.chat_should_report(chat_id)}`"


def __user_settings__(user_id):
    if sql.user_should_report(user_id) is True:
        text = "Anda akan menerima laporan dari obrolan yang Anda kelola."
    else:
        text = "Anda *tidak* akan menerima laporan dari obrolan yang Anda kelola."
    return text


def buttons(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            bot.unbanChatMember(splitter[0], splitter[2])
            query.aswer("Berhasil ditendang")
            return ""
        except Exception as err:
            query.answer("Gagal Menendang")
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
    elif splitter[1] == "banned":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            query.answer("Berhasil di Banned")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("Gagal Membanned")
    elif splitter[1] == "delete":
        try:
            bot.deleteMessage(splitter[0], splitter[3])
            query.answer("Pesan dihapus")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("gagal menghapus Pesan!")


SETTING_HANDLER = CommandHandler("reports", report_setting, run_async=True)
REPORT_HANDLER = CommandHandler(
    "report", report, filters=Filters.chat_type.groups, run_async=True
)
ADMIN_REPORT_HANDLER = MessageHandler(
    Filters.regex(r"(?i)@admin(s)?"), report, run_async=True
)
REPORT_BUTTON_USER_HANDLER = CallbackQueryHandler(
    buttons, pattern=r"report_", run_async=True
)

dispatcher.add_handler(REPORT_BUTTON_USER_HANDLER)
dispatcher.add_handler(SETTING_HANDLER)
dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)

__mod_name__ = "Reporting"
__handlers__ = [
    (REPORT_HANDLER, REPORT_GROUP),
    (ADMIN_REPORT_HANDLER, REPORT_GROUP),
    (SETTING_HANDLER),
]
