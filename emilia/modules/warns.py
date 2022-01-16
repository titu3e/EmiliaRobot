import html
import re
from typing import Optional

import telegram
from emilia import TIGERS, WOLVES, dispatcher
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    is_user_admin,
    user_admin,
    user_can_ban,
    user_admin_no_reply,
    can_delete,
)
from emilia.modules.helper_funcs.extraction import (
    extract_text,
    extract_user,
    extract_user_and_text,
)
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.misc import split_message
from emilia.modules.helper_funcs.string_handling import split_quotes
from emilia.modules.log_channel import loggable
from emilia.modules.sql import warns_sql as sql
from telegram import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    User,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    DispatcherHandlerStop,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html
from emilia.modules.sql.approve_sql import is_approved

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Filter peringatan saat ini di obrolan ini:</b>\n"


# Not async
def warn(user: User,
         chat: Chat,
         reason: str,
         message: Message,
         warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        # message.reply_text("Damn admins, They are too far to be One Punched!")
        return

    if user.id in TIGERS:
        if warner:
            message.reply_text("Tigers cant be warned.")
        else:
            message.reply_text(
                "Tiger triggered an auto warn filter!\n I can't warn tigers but they should avoid abusing this."
            )
        return

    if user.id in WOLVES:
        if warner:
            message.reply_text("Wolf disasters are warn immune.")
        else:
            message.reply_text(
                "Wolf Disaster triggered an auto warn filter!\nI can't warn wolves but they should avoid abusing this."
            )
        return

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Automated warn filter."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # punch
            chat.unban_member(user.id)
            reply = (
                f"peringatan, {mention_html(user.id, user.first_name)} [<code>{user.id}</code>] telah ditendang!")

        else:  # ban
            chat.kick_member(user.id)
            reply = (
                f"peringatan, {mention_html(user.id, user.first_name)} [<code>{user.id}</code>] telah diblokir!")

        for warn_reason in reasons:
            reply += f"\n - {html.escape(warn_reason)}"

        # message.bot.send_sticker(chat.id, BAN_STICKER)  # Emilia's sticker
        keyboard = None
        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN_BAN\n"
                      f"<b>Admin:</b> {warner_tag}\n"
                      f"<b>Pengguna:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>Alasan:</b> {reason}\n"
                      f"<b>menghitung:</b> <code>{num_warns}/{limit}</code>")

    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Hapus peringatan", callback_data="rm_warn({})".format(user.id))
        ]])

        reply = (
            f"{mention_html(user.id, user.first_name)} [<code>{user.id}</code>]"
            f" Diperingatkan ({num_warns} of {limit}).")
        if reason:
            reply += f"\nReason: {html.escape(reason)}"

        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN\n"
                      f"<b>Admin:</b> {warner_tag}\n"
                      f"<b>Pengguna:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>Alasan:</b> {reason}\n"
                      f"<b>Menghitung:</b> <code>{num_warns}/{limit}</code>")

    try:
        message.reply_text(
            reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(
                reply,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                quote=False)
        else:
            raise
    return log_reason



@user_admin_no_reply
# @user_can_ban
@bot_admin
@loggable
def button(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        res = sql.remove_warn(user_id, chat.id)
        if res:
            user_member = chat.get_member(user_id)
            update.effective_message.edit_text(
                f"{mention_html(user_member.user.id, user_member.user.first_name)} [<code>{user_member.user.id}</code>] Peringatan dihapus.",
                parse_mode=ParseMode.HTML,
            )
            user_member = chat.get_member(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNWARN\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>Pengguna:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
            )
        else:
            update.effective_message.edit_text(
                "Pengguna sudah tidak memiliki peringatan.", parse_mode=ParseMode.HTML
            )

    return ""


@user_admin
@can_restrict
# @user_can_ban
@loggable
def warn_user(update: Update, context: CallbackContext) -> str:
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    warner: Optional[User] = update.effective_user

    user_id, reason = extract_user_and_text(message, args)
    if message.text.startswith("/d") and message.reply_to_message:
        message.reply_to_message.delete()
    if user_id:
        if (
            message.reply_to_message
            and message.reply_to_message.from_user.id == user_id
        ):
            return warn(
                message.reply_to_message.from_user,
                chat,
                reason,
                message.reply_to_message,
                warner,
            )
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("Itu terlihat seperti ID Pengguna yang tidak valid bagi saya.")
    return ""


@user_admin
# @user_can_ban
@bot_admin
@loggable
def reset_warns(update: Update, context: CallbackContext) -> str:
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("Peringatan telah disetel ulang!")
        warned = chat.get_member(user_id).user
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESETWARNS\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Pengguna:</b> {mention_html(warned.id, warned.first_name)}"
        )
    else:
        message.reply_text("Tidak ada pengguna yang ditunjuk")
    return ""


def warns(update: Update, context: CallbackContext):
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = (
                f"Pengguna ini memiliki {num_warns}/{limit} peringatan, karena alasan berikut:"
            )
            for reason in reasons:
                text += f"\n {reason}"

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                f"Pengguna ini memiliki {num_warns}/{limit} peringatan, tapi tidak ada alasan untuk salah satu dari mereka."
            )
    else:
        update.effective_message.reply_text("Pengguna ini belum mendapatkan peringatan apa pun!")


# Dispatcher handler stop - do not async
@user_admin
# @user_can_ban
def add_warn_filter(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text(f"Peringatan handler yang ditambahkan untuk '{keyword}'!")
    raise DispatcherHandlerStop


@user_admin
# @user_can_ban
def remove_warn_filter(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("Tidak ada filter peringatan aktif di sini!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("Ya, saya akan berhenti memperingatkan orang-orang untuk itu.")
            raise DispatcherHandlerStop

    msg.reply_text(
        "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif."
    )


def list_warn_filters(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("Tidak ada filter peringatan aktif di sini!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = f" - {html.escape(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if filter_list != CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@loggable
def reply_filter(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    user: Optional[User] = update.effective_user

    if not user:  # Ignore channel
        return

    if user.id == 777000:
        return
    if is_approved(chat.id, user.id):
        return
    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user: Optional[User] = update.effective_user
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@user_admin
# @user_can_ban
@loggable
def set_warn_limit(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("Batas peringatan minimum adalah!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("Memperbarui batas peringatan ke {}".format(args[0]))
                return (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#SET_WARN_LIMIT\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Setel batas peringatan ke <code>{args[0]}</code>"
                )
        else:
            msg.reply_text("Give me a number as an arg!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("Batas peringatan saat ini adalah {}".format(limit))
    return ""


@user_admin
# @user_can_ban
def set_warn_strength(update: Update, context: CallbackContext):
    args = context.args
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("Terlalu banyak peringatan sekarang akan menghasilkan blokir!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah mengaktifkan peringatan kuat. Pengguna akan di blokir"
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text(
                "Terlalu banyak peringatan sekarang akan menghasilkan tendangan! Pengguna akan dapat bergabung lagi setelahnya."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah menonaktifkan peringatan kuat. Pengguna hanya akan ditendang."
            )

        else:
            msg.reply_text("Saya hanya mengerti on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text(
                "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            msg.reply_text(
                "Peringatan saat ini disetel untuk *diblokir* pengguna saat melampaui batas.",
                parse_mode=ParseMode.MARKDOWN,
            )
    return ""


def __stats__():
    return (
        f"× {sql.num_warns()} overall seluruh peringatan, pada {sql.num_warn_chats()} obrolan.\n"
        f"× {sql.num_warn_filters()} seluruh peringatan, pada {sql.num_warn_filter_chats()} obrolan."
    )


def __import_data__(chat_id, data):
    for user_id, count in data.get("warns", {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return (
        f"Obrolan ini mempunyai `{num_warn_filters}` saringan peringatkan. "
        f"Dibutuhkan `{limit}` peringatan sebelum pengguna akan mendapatkan *{'kicked' jika soft_warn kalau tidak 'banned'}*."
    )

__help__ = """
✦ *Command for Members:*
✧ /warns <userhandle>: get a user's number, and reason, of warns.

✦ *This command is for admin or creator only:*
✧ /warnlist: list of all current warning filters
✧ /warn <userhandle>: warn a user. After 3 warns, the user will be banned from the group. Can also be used as a reply.
✧ /dwarn <userhandle>: warn a user and delete the message. After 3 warns, the user will be banned from the group. Can also be used as a reply.
✧ /resetwarn <userhandle>: reset the warns for a user. Can also be used as a reply.
✧ /addwarn <keyword> <reply message>: set a warning filter on a certain keyword. If you want your keyword to be a sentence, encompass it with quotes, as such: /addwarn "very angry" This is an angry user.
✧ /nowarn <keyword>: stop a warning filter
✧ /warnlimit <num>: set the warning limit
✧ /strongwarn <on/yes/off/no>: If set to on, exceeding the warn limit will result in a ban. Else, will just punch.

Keep your members in check with warnings; stop them getting out of control!
If you're looking for automated warnings, go read about the blacklist module.
"""

__mod_name__ = "Warns"

WARN_HANDLER = CommandHandler(["warn", "dwarn"], warn_user, filters=Filters.chat_type.groups, run_async=True)
RESET_WARN_HANDLER = CommandHandler(
    ["resetwarn", "resetwarns"], reset_warns, filters=Filters.chat_type.groups, run_async=True
)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn", run_async=True)
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, filters=Filters.chat_type.groups, run_async=True)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.chat_type.groups, run_async=True)
RM_WARN_HANDLER = CommandHandler(
    ["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.chat_type.groups, run_async=True
)
LIST_WARN_HANDLER = DisableAbleCommandHandler(
    ["warnlist", "warnfilters"], list_warn_filters, filters=Filters.chat_type.groups, admin_ok=True, run_async=True
)
WARN_FILTER_HANDLER = MessageHandler(
    CustomFilters.has_text & Filters.chat_type.groups, reply_filter, run_async=True
)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, filters=Filters.chat_type.groups, run_async=True)
WARN_STRENGTH_HANDLER = CommandHandler(
    "strongwarn", set_warn_strength, filters=Filters.chat_type.groups, run_async=True
)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
