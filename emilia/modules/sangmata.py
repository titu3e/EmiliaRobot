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

from telethon.errors.rpcerrorlist import YouBlockedUserError
from emilia import telethn as tbot
from emilia.events import register
from emilia import ubot2 as ubot
from asyncio.exceptions import TimeoutError


@register(pattern="^/sg ?(.*)")
async def lastname(steal):
    steal.pattern_match.group(1)
    puki = await steal.reply("```Mengambil Informasi Pengguna Tersebut..```")
    if steal.fwd_from:
        return
    if not steal.reply_to_msg_id:
        await puki.edit("```Mohon Balas Ke Pesan Pengguna.```")
        return
    message = await steal.get_reply_message()
    chat = "@SangMataInfo_bot"
    user_id = message.sender.id
    id = f"/search_id {user_id}"
    if message.sender.bot:
        await puki.edit("```Balas Pesan Pengguna Asli.```")
        return
    await puki.edit("```Tunggu sebentar...```")
    try:
        async with ubot.conversation(chat) as conv:
            try:
                msg = await conv.send_message(id)
                r = await conv.get_response()
                response = await conv.get_response()
            except YouBlockedUserError:
                await steal.reply(
                    "```Error, melapor kepada @ZenitsuPrjkt```"
                )
                return
            if r.text.startswith("Name"):
                respond = await conv.get_response()
                await puki.edit(f"`{r.message}`")
                await ubot.delete_messages(
                    conv.chat_id, [msg.id, r.id, response.id, respond.id]
                ) 
                return
            if response.text.startswith("No records") or r.text.startswith(
                "No records"
            ):
                await puki.edit("```Saya Tidak Dapat Menemukan Informasi Pengguna Ini, Sepertinya Pengguna Ini Belum Pernah Mengubah Namanya Sebelumnya.```")
                await ubot.delete_messages(
                    conv.chat_id, [msg.id, r.id, response.id]
                )
                return
            else:
                respond = await conv.get_response()
                await puki.edit(f"```{response.message}```")
            await ubot.delete_messages(
                conv.chat_id, [msg.id, r.id, response.id, respond.id]
            )
    except TimeoutError:
        return await puki.edit("`I'm Sick Sorry...`")



@register(pattern="^/quotly ?(.*)")
async def quotess(qotli):
    if qotli.fwd_from:
        return
    if not qotli.reply_to_msg_id:
        return await qotli.reply("```Mohon Balas Ke Pesan```")
    reply_message = await qotli.get_reply_message()
    if not reply_message.text:
        return await qotli.reply("```Mohon Balas Ke Pesan```")
    chat = "@QuotLyBot"
    if reply_message.sender.bot:
        return await qotli.reply("```Mohon Balas Ke Pesan```")
    await qotli.reply("```Sedang Memproses Sticker, Mohon Menunggu```")
    try:
        async with ubot.conversation(chat) as conv:
            try:
                response = await conv.get_response()
                msg = await ubot.forward_messages(chat, reply_message)
                response = await response
                """ - don't spam notif - """
                await ubot.send_read_acknowledge(conv.chat_id)
            except YouBlockedUserError:
                return await qotli.edit("```Harap Jangan Blockir @QuotLyBot Buka Blokir Lalu Coba Lagi```")
            if response.text.startswith("Hi!"):
                await qotli.edit("```Mohon Menonaktifkan Pengaturan Privasi Forward Anda```")
            else:
                await qotli.delete()
                await tbot.send_message(qotli.chat_id, response.message)
                await tbot.send_read_acknowledge(qotli.chat_id)
                """ - cleanup chat after completed - """
                await ubot.delete_messages(conv.chat_id,
                                              [msg.id, response.id])
    except TimeoutError:
        await qotli.edit()
