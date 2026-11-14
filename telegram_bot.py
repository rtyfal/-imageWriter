import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

# Переконайтеся, що зміна TOKEN оголошена або завантажується з env

DJANGO_API_URL = 'https://rtyfal.pythonanywhere.com/api/process-image/'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Сховище налаштувань користувачів
USER_SETTINGS = {}

# Клавіатури
def get_settings_keyboard(current_color="white", current_pos="bottom"):
    buttons = [
        [InlineKeyboardButton(text=f"Колорит: {current_color.upper()}", callback_data="change_color")],
        [InlineKeyboardButton(text=f"Позиция: {current_pos.upper()}", callback_data="change_position")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_color_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔴 Красный", callback_data="set_color_red"),
         InlineKeyboardButton(text="🟢 Зеленый", callback_data="set_color_green")],
        [InlineKeyboardButton(text="🔵 Синий", callback_data="set_color_blue"),
         InlineKeyboardButton(text="⚪ Белый", callback_data="set_color_white")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_position_keyboard():
    buttons = [
        [InlineKeyboardButton(text="⬆️ Сверху", callback_data="set_pos_top")],
        [InlineKeyboardButton(text="⬅️ Слева", callback_data="set_pos_left"),
         InlineKeyboardButton(text="➡️ Справа", callback_data="set_pos_right")],
        [InlineKeyboardButton(text="⬇️ Снизу", callback_data="set_pos_bottom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Реєстрація команд із очищенням старих
async def setup_bot_commands(bot: Bot):
    await bot.delete_my_commands()  # Скидаємо старе меню
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="settings", description="Настройки цвета и текста")
    ]
    await bot.set_my_commands(commands)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Нажми /settings или выбери настройки из меню слева, чтобы настроить вид текста. Затем просто отправляй фото с подписью.")

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    user_id = message.from_user.id
    settings = USER_SETTINGS.get(user_id, {"color": "white", "position": "bottom"})
    
    await message.answer(
        "⚙️ **Текущие настройки:**",
        reply_markup=get_settings_keyboard(settings["color"], settings["position"]),
        parse_mode="Markdown"
    )

# Додано callback.answer() для усунення подвійних спрацьовувань
@dp.callback_query(F.data == "change_color")
async def choose_color(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Выберите цвет текста:", reply_markup=get_color_keyboard())

@dp.callback_query(F.data == "change_position")
async def choose_position(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Выберите позицию текста:", reply_markup=get_position_keyboard())

@dp.callback_query(F.data.startswith("set_color_"))
async def save_color(callback: types.CallbackQuery):
    await callback.answer()
    color = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {"color": "white", "position": "bottom"}
    USER_SETTINGS[user_id]["color"] = color

    await callback.message.edit_text(
        f"✅ Цвет изменен на **{color}**!",
        reply_markup=get_settings_keyboard(USER_SETTINGS[user_id]["color"], USER_SETTINGS[user_id]["position"]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("set_pos_"))
async def save_position(callback: types.CallbackQuery):
    await callback.answer()
    position = callback.data.split("_")[2]
    user_id = callback.from_user.id

    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {"color": "white", "position": "bottom"}
    USER_SETTINGS[user_id]["position"] = position

    await callback.message.edit_text(
        f"✅ Позиция изменена на **{position}**!",
        reply_markup=get_settings_keyboard(USER_SETTINGS[user_id]["color"], USER_SETTINGS[user_id]["position"]),
        parse_mode="Markdown"
    )

@dp.message(F.photo & F.caption)
async def process_photo(message: types.Message):
    user_id = message.from_user.id
    user_config = USER_SETTINGS.get(user_id, {"color": "white", "position": "bottom"})

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(file_info.file_path)

    data = aiohttp.FormData()
    data.add_field('photo', photo_bytes, filename='photo.jpg', content_type='image/jpeg')
    data.add_field('text', message.caption)
    data.add_field('color', user_config["color"])
    data.add_field('position', user_config["position"])

    async with aiohttp.ClientSession() as session:
        async with session.post(DJANGO_API_URL, data=data) as resp:
            if resp.status == 200:
                result_bytes = await resp.read()
                result_photo = types.BufferedInputFile(result_bytes, filename="result.jpg")
                await message.answer_photo(photo=result_photo, caption="Готово!")
            else:
                await message.answer("Ошибка при обработке изображения.")

async def on_startup(bot: Bot):
    await setup_bot_commands(bot)
    logging.info("Команды меню успешно обновлены!")

async def main():
    dp.startup.register(on_startup)
    # Гарантовано скидаємо всі накопичені оновлення та з'єднання
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())