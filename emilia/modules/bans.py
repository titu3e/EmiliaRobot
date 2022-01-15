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
import random

from time import sleep
from telegram import (
    ParseMode,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters, CommandHandler, run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_html
from typing import Optional, List
from telegram import TelegramError

import emilia.modules.sql.users_sql as sql
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia import (
    DEV_USERS,
    LOGGER,
    OWNER_ID,
    DRAGONS,
    DEMONS,
    TIGERS,
    WOLVES,
    dispatcher,
)
from emilia.modules.helper_funcs.chat_status import (
    user_admin_no_reply,
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    is_user_in_chat,
    user_admin,
    user_can_ban,
    can_delete,
    dev_plus,
)
from emilia.modules.helper_funcs.extraction import extract_user_and_text
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.log_channel import gloggable, loggable



@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot = context.bot
    args = context.args
    reason = ""
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("Saluran {} berhasil dilarang dari {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
        else:
            message.reply_text("Gagal blokir saluran")
        return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya tidak dapat menemukan pengguna ini 😣.")
        return log_message
    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Saya tidak dapat menemukan pengguna ini 😣":
            raise
        message.reply_text("Saya tidak dapat menemukan pengguna ini 😣")
        return log_message
    if user_id == bot.id:
        message.reply_text("Saya tidak akan BAN diri saya sendiri, apakah kamu gila? 😠")
        return log_message

    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        if user_id == OWNER_ID:
            message.reply_text("Mencoba menempatkanku melawan seorang Raja? 🤔")
        elif user_id in DEV_USERS:
            message.reply_text("Saya tidak bisa bertindak melawan Pangeran kami 😋")
        elif user_id in DRAGONS:
            message.reply_text(
                "Melawan Kaisar ini di sini akan membahayakan nyawa pengguna 😥"
            )
        elif user_id in DEMONS:
            message.reply_text(
                "Bawa perintah dari Kapten untuk melawan pelayan Assassin 🤭"
            )
        elif user_id in TIGERS:
            message.reply_text(
                "Bawa perintah dari Prajurit untuk melawan pelayan Lancer 🤪"
            )
        elif user_id in WOLVES:
            message.reply_text("Akses trader membuat mereka kebal banned 😅")
        else:
            message.reply_text("Saya tidak bisa banned orang ini karena dia adalah admin 😒")
        return log_message
    if message.text.startswith("/s"):
        silent = True
        if not can_delete(chat, context.bot.id):
            return ""
    else:
        silent = False
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#{'S' if silent else ''}BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += "<b>Alasan:</b> {}".format(reason)

    try:
        chat.ban_member(user_id)

        if silent:
            if message.reply_to_message:
                message.reply_to_message.delete()
            message.delete()
            return log

        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        reply = (
            f"Terbanned 😝 {mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>]!"
        )
        if reason:
            reply += f"\nAlasan: {html.escape(reason)}"

        bot.sendMessage(
            chat.id,
            reply,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Unban", callback_data=f"unbanb_unban={user_id}"
                        ),
                        InlineKeyboardButton(text="Delete", callback_data="unbanb_del"),
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            if silent:
                return log
            message.reply_text("Terbanned! 😝", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR membanned pengguna %s di obrolan %s (%s) disebabkan oleh %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Yah sial, aku tidak bisa banned pengguna itu 😒")

    return log_message


@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("User not found.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Saya tidak akan BAN diri saya sendiri, apakah kamu gila? 😠")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Saya tidak bisa banned orang ini karena dia adalah admin 😒")
        return log_message

    if not reason:
        message.reply_text("Anda tidak punya hak untuk membatasi seseorang!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += "\nAlasan: {}".format(reason)

    try:
        chat.ban_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker

        reply_msg = (
            f"Banned! Pengguna diblokir {mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>]"
            f" untuk (`{time_val}`)."
        )

        if reason:
            reply_msg += f"\nAlasan: `{html.escape(reason)}`"

        bot.sendMessage(
            chat.id,
            reply_msg,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Unban", callback_data=f"unbanb_unban={user_id}"
                        ),
                        InlineKeyboardButton(text="Delete", callback_data="unbanb_del"),
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(
                f"Banned! Pengguna diblokir {mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] untuk waktu {time_val}.", quote=False
            )
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR banning user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Yah sial, aku tidak bisa menendang pengguna itu 😒")

    return log_message


@connection_status
@bot_admin
@can_restrict
@user_admin_no_reply
@user_can_ban
@loggable
def unbanb_btn(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    if query.data != "unbanb_del":
        splitter = query.data.split("=")
        query_match = splitter[0]
        if query_match == "unbanb_unban":
            user_id = splitter[1]
            if not is_user_admin(chat, int(user.id)):
                bot.answer_callback_query(
                    query.id,
                    text="Anda tidak memiliki cukup hak untuk mute suara orang",
                    show_alert=True,
                )
                return ""
            log_message = ""
            try:
                member = chat.get_member(user_id)
            except BadRequest:
                pass
            chat.unban_member(user_id)
            query.message.edit_text(
                f"Unbanned! Pengguna tidak lagi diblokir {member.user.first_name} [{member.user.id}]"
            )
            bot.answer_callback_query(query.id, text="Unbanned!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNBANNED\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
            )

    else:
        if not is_user_admin(chat, int(user.id)):
            bot.answer_callback_query(
                query.id,
                text="Anda tidak memiliki cukup hak untuk menghapus pesan ini.",
                show_alert=True,
            )
            return ""
        query.message.delete()
        bot.answer_callback_query(query.id, text="Dihapus!")
        return ""

    
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def punch(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("User not found")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise

        message.reply_text("Saya tidak dapat menemukan pengguna ini.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Bagaimana saya akan unban diri saya sendiri jika saya tidak ada di sini...? 🤔")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Saya benar-benar berharap saya bisa memukul pengguna ini....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"{mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] Kicked.",
            parse_mode=ParseMode.HTML
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            log += f"\n<b>Alasan:</b> {reason}"

        return log

    else:
        message.reply_text("Yah sial, aku tidak bisa menendang pengguna itu 😒")

    return log_message



@bot_admin
@can_restrict
def punchme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Saya berharap saya bisa ... tetapi Anda seorang admin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text(
            "Tidak masalah 😊",
        )
    else:
        update.effective_message.reply_text("Hah? Aku tidak bisa 🙄")


@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("Saluran {} pemblokiran berhasil dibatalkan dari {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
        else:
            message.reply_text("Gagal membatalkan pemblokiran saluran")
        return

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("User not found.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        message.reply_text("Saya tidak dapat menemukan pengguna ini.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Bagaimana saya akan unban diri saya sendiri jika saya tidak ada di sini...? 🤔")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text(f"User not found.")
        return log_message

    chat.unban_member(user_id)
    message.reply_text(
        f"Ya, pengguna ini dapat bergabung! 😁 {member.user.first_name} [{member.user.id}]."
    )

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    return log


@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in DRAGONS or user.id not in TIGERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Berikan ID obrolan yang valid.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Saya tidak dapat menemukan pengguna ini.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Mengapa Anda mencoba unban seseorang yang sudah ada di obrolan? 😑")
        return

    chat.unban_member(user.id)
    message.reply_text(f"Ya, pengguna ini dapat bergabung! 😁")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )

    return log


@bot_admin
@can_restrict
@loggable
def banme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    chat = update.effective_chat
    user = update.effective_user
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Saya tidak bisa banned admin.")
        return

    res = update.effective_chat.ban_member(user_id)
    if res:
        update.effective_message.reply_text("Ya kau benar! GTFO..")
        return (
            "<b>{}:</b>"
            "\n#BANME"
            "\n<b>User:</b> {}"
            "\n<b>ID:</b> <code>{}</code>".format(
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
                user_id,
            )
        )

    else:
        update.effective_message.reply_text("Hah? Aku tidak bisa 🙄")


@dev_plus
def snipe(update: Update, context: CallbackContext):
    args = context.args
    bot = context.bot
    try:
        chat_id = str(args[0])
        del args[0]
    except TypeError:
        update.effective_message.reply_text("Please give me a chat to echo to!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("Tidak dapat mengirim ke grup %s", str(chat_id))
            update.effective_message.reply_text(
                "Tidak dapat mengirim pesan. Mungkin saya bukan bagian dari grup itu?"
            )


__help__ = """
✦ *User Commands:*
✧ /kickme*:* kicks the user who issued the command

✦ *Admins only:*
✧ /ban <userhandle>*:* bans a user. (via handle, or reply)
✧ /sban <userhandle>*:* Silently ban a user. Deletes command, Replied message and doesn't reply. (via handle, or reply)
✧ /tban <userhandle> x(m/h/d)*:* bans a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
✧ /unban <userhandle>*:* unbans a user. (via handle, or reply)
✧ /kick <userhandle>*:* kicks a user out of the group, (via handle, or reply)
✧ /mute <userhandle>*:* silences a user. Can also be used as a reply, muting the replied to user.
✧ /tmute <userhandle> x(m/h/d)*:* mutes a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
✧ /unmute <userhandle>*:* unmutes a user. Can also be used as a reply, muting the replied to user.
✧ /zombies*:* searches deleted accounts
✧ /zombies clean*:* removes deleted accounts from the group.
✧ /snipe <chatid> <string>*:* Make me send a message to a specific chat.
"""


__mod_name__ = "Bans/Mutes"

BAN_HANDLER = CommandHandler(["ban", "sban"], ban, run_async=True)
TEMPBAN_HANDLER = CommandHandler(["tban"], temp_ban, run_async=True)
KICK_HANDLER = CommandHandler(["kick", "punch"], punch, run_async=True)
UNBAN_HANDLER = CommandHandler("unban", unban, run_async=True)
ROAR_HANDLER = CommandHandler("roar", selfunban, run_async=True)
UNBAN_BUTTON_HANDLER = CallbackQueryHandler(unbanb_btn, pattern=r"unbanb_")
KICKME_HANDLER = DisableAbleCommandHandler(["kickme", "punchme"], punchme, filters=Filters.chat_type.groups, run_async=True)
SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=CustomFilters.sudo_filter, run_async=True)
BANME_HANDLER = CommandHandler("banme", banme, run_async=True)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(UNBAN_BUTTON_HANDLER)
dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANME_HANDLER)

__handlers__ = [
    BAN_HANDLER,
    TEMPBAN_HANDLER,
    KICK_HANDLER,
    UNBAN_HANDLER,
    ROAR_HANDLER,
    KICKME_HANDLER,
    UNBAN_BUTTON_HANDLER,
    SNIPE_HANDLER,
    BANME_HANDLER,
]
