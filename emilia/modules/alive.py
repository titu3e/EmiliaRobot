import os
import re
from platform import python_version as kontol
from telethon import events, Button
from telegram import __version__ as telever
from telethon import __version__ as tlhver
from pyrogram import __version__ as pyrover
from emilia.events import register
from emilia import telethn as tbot


PHOTO = "https://telegra.ph/file/f39bb53399e4c4bfaa9db.jpg"

@register(pattern=("/alive"))
async def awake(event):
  TEXT = f"**Hi [{event.sender.first_name}](tg://user?id={event.sender.id}), I'm Emilia.** \n\n"
  TEXT += "**I'm Working Properly** \n\n"
  TEXT += f"**My Master : [ZenitsuPrjkt](https://t.me/ZenitsuPrjkt)** \n\n"
  TEXT += f"**Library Version :** `{telever}` \n\n"
  TEXT += f"**Telethon Version :** `{tlhver}` \n\n"
  TEXT += f"**Pyrogram Version :** `{pyrover}` \n\n"
  TEXT += "**Thanks For Adding Me Here️**"
  BUTTON = [[Button.url("Help", "https://t.me/EmiliaPrjkt_bot?start=help"), Button.url("Repo", "https://github.com/ZenitsuPrjkt/Emilia")]]
  await tbot.send_file(event.chat_id, PHOTO, caption=TEXT,  buttons=BUTTON)
