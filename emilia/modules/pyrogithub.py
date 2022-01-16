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

import aiohttp
from pyrogram import filters
from emilia import pbot, BOT_USERNAME
from emilia.utils.errors import capture_err


__mod_name__ = "Github"


@pbot.on_message(filters.command(["github", "git", f"git@{BOT_USERNAME}"]))
@capture_err
async def github(_, message):
    if len(message.command) != 2:
        await message.reply_text("/git Nama pengguna")
        return
    username = message.text.split(None, 1)[1]
    URL = f"https://api.github.com/users/{username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as request:
            if request.status == 404:
                return await message.reply_text("404")

            result = await request.json()
            try:
                url = result["html_url"]
                name = result["name"]
                company = result["company"]
                bio = result["bio"]
                created_at = result["created_at"]
                avatar_url = result["avatar_url"]
                blog = result["blog"]
                location = result["location"]
                repositories = result["public_repos"]
                followers = result["followers"]
                following = result["following"]
                caption = f"""**Info dari {name}**
**Nama Pengguna:** `{username}`
**Bio:** `{bio}`
**Tautan Profil:** [Here]({url})
**Perusahaan:** `{company}`
**Dibuat pada:** `{created_at}`
**Repositori:** `{repositories}`
**Blog:** `{blog}`
**Lokasi:** `{location}`
**Pengikut:** `{followers}`
**Mengikuti:** `{following}`"""
            except Exception as e:
                print(str(e))
                pass
    await message.reply_photo(photo=avatar_url, caption=caption)
