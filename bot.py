import os
import asyncio
import requests
from io import BytesIO
from PIL import Image, ImageFilter
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# ============================
# LOAD ENV
# ============================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env")

# ============================
# CONFIG
# ============================

TARGET_W = 1080
TARGET_H = 1920

SAVE_DIR = "covers"
os.makedirs(SAVE_DIR, exist_ok=True)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ============================
# IGDB
# ============================

def pick_main_game(results, query):
    query = query.lower()
    for g in results:
        if g["name"].lower() == query:
            return g
    return min(results, key=lambda g: len(g["name"]))


def search_game(game_name: str):
    url = "https://api.igdb.com/v4/games"
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    body = f'''
        search "{game_name}";
        fields name, cover.image_id;
        limit 10;
    '''

    r = requests.post(url, headers=headers, data=body)

    if r.status_code != 200:
        return None

    results = r.json()
    if not results:
        return None

    return pick_main_game(results, game_name)


def download_image(image_id: str):
    url = f"https://images.igdb.com/igdb/image/upload/t_1080p/{image_id}.jpg"
    r = requests.get(url)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


# ============================
# POSTER
# ============================

def make_tiktok_cover(img: Image.Image):
    bg = img.resize((TARGET_W, TARGET_H))
    bg = bg.filter(ImageFilter.GaussianBlur(45))

    ratio = img.width / img.height
    new_h = int(TARGET_H * 0.75)
    new_w = int(new_h * ratio)

    cover = img.resize((new_w, new_h))

    x = (TARGET_W - new_w) // 2
    y = (TARGET_H - new_h) // 2

    bg.paste(cover, (x, y))
    return bg


# ============================
# BOT HANDLERS
# ============================

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "🎮 Напиши название игры\n\n"
        "Пример:\n"
        "SOMA\n"
        "GTA V\n"
        "Cyberpunk 2077"
    )


@dp.message()
async def game_handler(message: types.Message):
    game_name = message.text.strip()

    await message.answer("🔍 Ищу игру...")

    game = search_game(game_name)

    if not game or "cover" not in game:
        await message.answer("❌ Обложка не найдена")
        return

    image_id = game["cover"]["image_id"]

    img = download_image(image_id)
    poster = make_tiktok_cover(img)

    filename = game["name"].replace(":", "").replace("/", "")
    path = f"{SAVE_DIR}/{filename}.jpg"

    poster.save(path, quality=95)

    await message.answer_photo(
        types.FSInputFile(path),
        caption=f"✅ {game['name']}\n1080x1920"
    )


# ============================
# RUN
# ============================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
