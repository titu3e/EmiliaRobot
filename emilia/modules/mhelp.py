import re
import os

from telethon import events, Button
from telethon import __version__ as tlhver
from pyrogram import __version__ as pyrover
from emilia.events import register as MEMEK
from emilia import telethn as tbot

PHOTO = "https://telegra.ph/file/8142e7aac030eebd40a4e.jpg"

@MEMEK(pattern=("/mhelp"))
async def awake(event):
  tai = event.sender.first_name
  EMILIA = "** ──「 Perintah Dasar 」── ** \n\n"
  EMILIA += "• /play **(nama lagu / balas ke audio) — play musik via YouTube** \n"
  EMILIA += "• /vplay ** (nama lagu / balas ke audio) – play video stream via YouTube** \n"
  EMILIA += "• /playlist - **Untuk memutar playlist Anda atau playlist group anda** \n"
  EMILIA += "• /song - ** (nama lagu) mendownload lagu via YouTube** \n\n"
  EMILIA += "** ──「 Admin CMD 」── ** \n\n"
  EMILIA += "• /music on|off - **mengaktifkan atau menonaktifkan music player di grup anda** \n"
  EMILIA += "• /pause atau /vpause - **Untuk pause musik/video yang sedang di putar** \n"
  EMILIA += "• /resume atau /vresume - **Untuk melanjutkan musik/video yang sedang ter pause** \n"
  EMILIA += "• /skip - **Untuk melewati lagu berikutnya** \n"
  EMILIA += "• /end - **Untuk memberhentikan pemutaran musik** \n"
  EMILIA += "• /vstop - **Untuk memberhentikan video stream yang sedang diputar** \n"
  EMILIA += "• /reload - **Untuk memperbarui admin list** \n"

  await tbot.send_file(event.chat_id, PHOTO, caption=EMILIA)
