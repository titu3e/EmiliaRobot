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

from gpytranslate import Translator
from telegram.ext import CommandHandler, CallbackContext
from telegram import (
    Message,
    Chat,
    User,
    ParseMode,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from emilia import dispatcher, pbot
from pyrogram import filters
from emilia.modules.disable import DisableAbleCommandHandler


__help__ = """ 
✦ *Commands:*
✧ /tl (or /tr): as a reply to a message, translates it to English.
✧ /tl <lang>: translates to <lang>
eg: /tl ja: translates to Japanese.
✧ /tl <source>//<dest>: translates from <source> to <lang>.
eg:  /tl ja//en: translates from Japanese to English.
✧ /langs: get a list of supported languages for translation.
✧ /tts <lang code>*:* Reply to any message to get text to speech output
✧ /stt*:* Type in reply to a voice message(support english only) to extract text from it.

✦ *Language Codes*
`af,am,ar,az,be,bg,bn,bs,ca,ceb,co,cs,cy,da,de,el,en,eo,es,
et,eu,fa,fi,fr,fy,ga,gd,gl,gu,ha,haw,hi,hmn,hr,ht,hu,hy,
id,ig,is,it,iw,ja,jw,ka,kk,km,kn,ko,ku,ky,la,lb,lo,lt,lv,mg,mi,mk,
ml,mn,mr,ms,mt,my,ne,nl,no,ny,pa,pl,ps,pt,ro,ru,sd,si,sk,sl,
sm,sn,so,sq,sr,st,su,sv,sw,ta,te,tg,th,tl,tr,uk,ur,uz,
vi,xh,yi,yo,zh,zh_CN,zh_TW,zu`
"""

__mod_name__ = "Translator"


trans = Translator()


@pbot.on_message(filters.command(["tl", "tr"]))
async def translate(_, message: Message) -> None:
    reply_msg = message.reply_to_message
    if not reply_msg:
        await message.reply_text("Balas pesan untuk menerjemahkannya!")
        return
    if reply_msg.caption:
        to_translate = reply_msg.caption
    elif reply_msg.text:
        to_translate = reply_msg.text
    try:
        args = message.text.split()[1].lower()
        if "//" in args:
            source = args.split("//")[0]
            dest = args.split("//")[1]
        else:
            source = await trans.detect(to_translate)
            dest = args
    except IndexError:
        source = await trans.detect(to_translate)
        dest = "en"
    translation = await trans(to_translate, sourcelang=source, targetlang=dest)
    reply = (
        f"<b>Diterjemahkan dari {source} ke {dest}</b>:\n"
        f"<code>{translation.text}</code>"
    )

    await message.reply_text(reply, parse_mode="html")


def languages(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text(
        "Klik tombol di bawah untuk melihat daftar kode bahasa yang didukung.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Language codes",
                        url="https://telegra.ph/Lang-codes-table-01-15",
                    ),
                ],
            ],
            disable_web_page_preview=True,
        ),
    )


LANG_HANDLER = DisableAbleCommandHandler("langs", languages, run_async=True)

dispatcher.add_handler(LANG_HANDLER)
