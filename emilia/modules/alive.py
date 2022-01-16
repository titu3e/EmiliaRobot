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

import os
import re
from platform import python_version as kontol
from telethon import events, Button
from telegram import __version__ as telever
from telethon import __version__ as tlhver
from pyrogram import __version__ as pyrover
from emilia.events import register
from emilia import telethn as tbot


PHOTO = "https://telegra.ph/file/7cd17e6f15a68275a33a5.jpg"

@register(pattern=("/alive"))
async def awake(event):
  TEXT = f"**✧ Halo [{event.sender.first_name}](tg://user?id={event.sender.id}), I'm Emilia.** \n\n"
  TEXT += "**✧ Saya Bekerja Dengan Benar** \n\n"
  TEXT += f"✧ **My Master : [Zenitsu Prjkt](https://t.me/ZenitsuPrjkt)** \n\n"
  TEXT += f"✧ **Versi Library  :** `{telever}` \n\n"
  TEXT += f"✧ **Versi Telethon :** `{tlhver}` \n\n"
  TEXT += f"✧ **Versi Pyrogram :** `{pyrover}` \n\n"
  BUTTON = [[Button.url("Bantuan", "https://t.me/EmiliaPrjkt_bot?start=help"), Button.url("Repo", "https://github.com/ZenitsuPrjkt/Emilia")]]
  await tbot.send_file(event.chat_id, PHOTO, caption=TEXT,  buttons=BUTTON)
