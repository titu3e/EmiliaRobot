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

# Pokedex Module Credits Pranav Ajay 🐰Github = Red-Aura 🐹 Telegram= @madepranav

import aiohttp
from pyrogram import filters
from emilia import pbot as tomori


@tomori.on_message(filters.command("pokedex"))
async def PokeDex(_, message):
    if len(message.command) != 2:
        await message.reply_text("/pokedex Nama Pokemon")
        return
    pokemon = message.text.split(None, 1)[1]
    pokedex = f"https://some-random-api.ml/pokedex?pokemon={pokemon}"
    async with aiohttp.ClientSession() as session:
        async with session.get(pokedex) as request:
            if request.status == 404:
                return await message.reply_text("Nama Pokemon Salah")

            result = await request.json()
            try:
                pokemon = result["name"]
                pokedex = result["id"]
                type = result["type"]
                poke_img = f"https://img.pokemondb.net/artwork/large/{pokemon}.jpg"
                abilities = result["abilities"]
                height = result["height"]
                weight = result["weight"]
                gender = result["gender"]
                stats = result["stats"]
                description = result["description"]
                caption = f"""
**Pokemon:** `{pokemon}`
**Pokedex:** `{pokedex}`
**Type:** `{type}`
**Abilities:** `{abilities}`
**Height:** `{height}`
**Weight:** `{weight}`
**Gender:** `{gender}`
**Stats:** `{stats}`
**Description:** `{description}`"""
            except Exception as e:
                print(str(e))
                pass
    await message.reply_photo(photo=poke_img, caption=caption)
