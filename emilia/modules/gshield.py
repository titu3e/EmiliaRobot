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

import asyncio
import os
import re
import better_profanity
import emoji
import nude
import requests
from better_profanity import profanity
from google_trans_new import google_translator
from telethon import events
from telethon.tl.types import ChatBannedRights
from emilia.confing import get_int_key, get_str_key
from emilia.services.telethonbasics import is_admin
from emilia.events import register
from pymongo import MongoClient
from emilia.modules.sql.nsfw_watch_sql import (
    add_nsfwatch,
    get_all_nsfw_enabled_chat,
    is_nsfwatch_indb,
    rmnsfwatch,
)
from emilia import telethn as tbot, MONGO_DB_URI, BOT_ID

translator = google_translator()
MUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=False)

MONGO_DB_URI = get_str_key("MONGO_DB_URI")

client = MongoClient()
client = MongoClient(MONGO_DB_URI)
db = client["emilia"]

async def is_nsfw(event):
    lmao = event
    if not (
        lmao.gif
        or lmao.video
        or lmao.video_note
        or lmao.photo
        or lmao.sticker
        or lmao.media
    ):
        return False
    if lmao.video or lmao.video_note or lmao.sticker or lmao.gif:
        try:
            starkstark = await event.client.download_media(lmao.media, thumb=-1)
        except:
            return False
    elif lmao.photo or lmao.sticker:
        try:
            starkstark = await event.client.download_media(lmao.media)
        except:
            return False
    img = starkstark
    f = {"file": (img, open(img, "rb"))}

    r = requests.post("https://starkapi.herokuapp.com/nsfw/", files=f).json()
    if r.get("success") is False:
        is_nsfw = False
    elif r.get("is_nsfw") is True:
        is_nsfw = True
    elif r.get("is_nsfw") is False:
        is_nsfw = False
    return is_nsfw


@tbot.on(events.NewMessage(pattern="/gshield (.*)"))
async def nsfw_watch(event):
    if not event.is_group:
        await event.reply("Anda Hanya Dapat mengaktifkan Nsfw Watch di Grup")
        return
    input_str = event.pattern_match.group(1)
    if not await is_admin(event, BOT_ID):
        await event.reply("`Saya Harus Menjadi Admin Untuk Melakukan Ini!`")
        return
    if await is_admin(event, event.message.sender_id):
        if (
            input_str == "on"
            or input_str == "On"
            or input_str == "ON"
            or input_str == "enable"
        ):
            if is_nsfwatch_indb(str(event.chat_id)):
                await event.reply("`Obrolan Ini Telah Mengaktifkan Nsfw Watch.`")
                return
            add_nsfwatch(str(event.chat_id))
            await event.reply(
                f"**Menambahkan Obrolan {event.chat.title} Dengan ID {event.chat_id} Ke Basis Data. Grup ini Konten Nsfw Akan Dihapus**"
            )
        elif (
            input_str == "off"
            or input_str == "Off"
            or input_str == "OFF"
            or input_str == "disable"
        ):
            if not is_nsfwatch_indb(str(event.chat_id)):
                await event.reply("Obrolan Ini Belum Mengaktifkan Nsfw Watch.")
                return
            rmnsfwatch(str(event.chat_id))
            await event.reply(
                f"**Menghapus Obrolan {event.chat.title} Dengan ID {event.chat_id} Dari Nsfw Watch**"
            )
        else:
            await event.reply(
                "saya hanya mengerti `/nsfwguardian on` dan `/nsfwguardian off` saja"
            )
    else:
        await event.reply("`Anda Harus Menjadi Admin Untuk Melakukan Ini!`")
        return


approved_users = db.approve
spammers = db.spammer
globalchat = db.globchat

CMD_STARTERS = ["/", "!", "."]
profanity.load_censor_words_from_file("./profanity_wordlist.txt")


@register(pattern="^/profanity(?: |$)(.*)")
async def profanity(event):
    if event.fwd_from:
        return
    if not event.is_group:
        await event.reply("Anda tidak bisa menggunakan kata-kata kotor di Grup.")
        return
    event.pattern_match.group(1)
    if not await is_admin(event, BOT_ID):
        await event.reply("`Saya Harus Menjadi Admin Untuk Melakukan Ini!`")
        return
    if await is_admin(event, event.message.sender_id):
        input = event.pattern_match.group(1)
        chats = spammers.find({})
        if not input:
            for c in chats:
                if event.chat_id == c["id"]:
                    await event.reply(
                        "Mohon masukan yes atau no.\n\nPengaturan saat ini adalah: **diaktifkan**"
                    )
                    return
            await event.reply(
                "Mohon masukan yes atau no.\n\nPengaturan saat ini adalah : **dimatikan**"
            )
            return
        if input == "on":
            if event.is_group:
                chats = spammers.find({})
                for c in chats:
                    if event.chat_id == c["id"]:
                        await event.reply(
                            "Filter kata-kata kotor sudah diaktifkan untuk obrolan ini."
                        )
                        return
                spammers.insert_one({"id": event.chat_id})
                await event.reply("Filter kata-kata tidak sopan diaktifkan untuk obrolan ini.")
        if input == "off":
            if event.is_group:
                chats = spammers.find({})
                for c in chats:
                    if event.chat_id == c["id"]:
                        spammers.delete_one({"id": event.chat_id})
                        await event.reply("Filter kata-kata tidak sopan dimatikan untuk obrolan ini.")
                        return
            await event.reply("Filter kata-kata tidak sopan tidak diaktifkan untuk obrolan ini.")
        if not input == "on" and not input == "off":
            await event.reply("Saya hanya mengerti dengan on atau off")
            return
    else:
        await event.reply("`Anda Harus Menjadi Admin Untuk Melakukan Ini!`")
        return


@register(pattern="^/globalmode(?: |$)(.*)")
async def profanity(event):
    if event.fwd_from:
        return
    if not event.is_group:
        await event.reply("Anda Hanya Dapat mengaktifkan mode global Watch di Grup.")
        return
    event.pattern_match.group(1)
    if not await is_admin(event, BOT_ID):
        await event.reply("`Anda Harus Menjadi Admin Untuk Melakukan Ini!`")
        return
    if await is_admin(event, event.message.sender_id):

        input = event.pattern_match.group(1)
        chats = globalchat.find({})
        if not input:
            for c in chats:
                if event.chat_id == c["id"]:
                    await event.reply(
                        "Mohon masukan yes atau no.\n\nPengaturan saat ini adalah: **on**"
                    )
                    return
            await event.reply(
                "Mohon masukan yes atau no.\n\nPengaturan saat ini adalah : **off**"
            )
            return
        if input == "on":
            if event.is_group:
                chats = globalchat.find({})
                for c in chats:
                    if event.chat_id == c["id"]:
                        await event.reply(
                            "Mode global sudah diaktifkan untuk obrolan ini."
                        )
                        return
                globalchat.insert_one({"id": event.chat_id})
                await event.reply("Mode global diaktifkan untuk obrolan ini.")
        if input == "off":
            if event.is_group:
                chats = globalchat.find({})
                for c in chats:
                    if event.chat_id == c["id"]:
                        globalchat.delete_one({"id": event.chat_id})
                        await event.reply("Mode global dimatikan untuk obrolan ini.")
                        return
            await event.reply("Mode global tidak diaktifkan untuk obrolan ini.")
        if not input == "on" and not input == "off":
            await event.reply("Saya hanya mengerti dengan on atau off")
            return
    else:
        await event.reply("`Anda Harus Menjadi Admin Untuk Melakukan Ini!`")
        return


@tbot.on(events.NewMessage(pattern=None))
async def del_profanity(event):
    if event.is_private:
        return
    msg = str(event.text)
    sender = await event.get_sender()
    # let = sender.username
    if await is_admin(event, event.message.sender_id):
        return
    chats = spammers.find({})
    for c in chats:
        if event.text:
            if event.chat_id == c["id"]:
                if better_profanity.profanity.contains_profanity(msg):
                    await event.delete()
                    if sender.username is None:
                        st = sender.first_name
                        hh = sender.id
                        final = f"[{st}](tg://user?id={hh}) **{msg}** terdeteksi sebagai kata slang dan pesan Anda telah dihapus"
                    else:
                        final = f"Woii coeg! **{msg}** terdeteksi sebagai kata slang dan pesan Anda telah dihapus"
                    dev = await event.respond(final)
                    await asyncio.sleep(10)
                    await dev.delete()
        if event.photo:
            if event.chat_id == c["id"]:
                await event.client.download_media(event.photo, "nudes.jpg")
                if nude.is_nude("./nudes.jpg"):
                    await event.delete()
                    st = sender.first_name
                    hh = sender.id
                    final = f"**NSFW TERDETEKSI**\n\n{st}](tg://user?id={hh}) pesanmu mengandung konten NSFW.. Jadi, Emilia menghapus pesannya\n\n **Pengirim Nsfw - Pengguna / Bot :** {st}](tg://user?id={hh})  \n\n`⚔️Deteksi Otomatis Didukung oleh EmiliaAI` \n**#GROUP_GUARDIAN** "
                    dev = await event.respond(final)
                    await asyncio.sleep(10)
                    await dev.delete()
                    os.remove("nudes.jpg")


def extract_emojis(s):
    return "".join(c for c in s if c in emoji.UNICODE_EMOJI)


@tbot.on(events.NewMessage(pattern=None))
async def del_profanity(event):
    if event.is_private:
        return
    msg = str(event.text)
    sender = await event.get_sender()
    # sender.username
    if await is_admin(event, event.message.sender_id):
        return
    chats = globalchat.find({})
    for c in chats:
        if event.text:
            if event.chat_id == c["id"]:
                u = msg.split()
                emj = extract_emojis(msg)
                msg = msg.replace(emj, "")
                if (
                    [(k) for k in u if k.startswith("@")]
                    and [(k) for k in u if k.startswith("#")]
                    and [(k) for k in u if k.startswith("/")]
                    and re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []
                ):
                    h = " ".join(filter(lambda x: x[0] != "@", u))
                    km = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", h)
                    tm = km.split()
                    jm = " ".join(filter(lambda x: x[0] != "#", tm))
                    hm = jm.split()
                    rm = " ".join(filter(lambda x: x[0] != "/", hm))
                elif [(k) for k in u if k.startswith("@")]:
                    rm = " ".join(filter(lambda x: x[0] != "@", u))
                elif [(k) for k in u if k.startswith("#")]:
                    rm = " ".join(filter(lambda x: x[0] != "#", u))
                elif [(k) for k in u if k.startswith("/")]:
                    rm = " ".join(filter(lambda x: x[0] != "/", u))
                elif re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []:
                    rm = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", msg)
                else:
                    rm = msg
                # print (rm)
                b = translator.detect(rm)
                if not "en" in b and not b == "":
                    await event.delete()
                    st = sender.first_name
                    hh = sender.id
                    final = f"[{st}](tg://user?id={hh}) Anda hanya harus berbicara dalam bahasa Inggris di sini!"
                    dev = await event.respond(final)
                    await asyncio.sleep(10)
                    await dev.delete()

__mod_name__ = "Shield"
