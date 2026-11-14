import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Бот успішно запущений як {bot.user}")
    try:
        # Глобальна синхронізація (потрібна для роботи в ЛС)
        synced = await bot.tree.sync()
        print(f"Синхронізовано {len(synced)} глобальних команд(и)")
    except Exception as e:
        print(f"Помилка синхронізації команд: {e}")

@bot.tree.command(name="process_image", description="Обробити фото та додати текст")
# Дозволяємо команду на серверах (guilds), у приватних повідомленнях (dms) та приватних каналах
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
# Дозволяємо використовувати бота як на сервері, так і прив'язаним до користувача
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.describe(
    image="Завантажте зображення",
    text="Текст, який потрібно накласти",
    position="Позиція тексту на фото",
    color="Колір тексту (наприклад: white, red, #ff0000)"
)
@app_commands.choices(position=[
    app_commands.Choice(name="Знизу", value="bottom"),
    app_commands.Choice(name="Зверху", value="top"),
    app_commands.Choice(name="Зліва", value="left"),
    app_commands.Choice(name="Справа", value="right")
])
async def process_image(
    interaction: discord.Interaction,
    image: discord.Attachment,
    text: str,
    position: app_commands.Choice[str],
    color: str = "white"
):
    await interaction.response.defer()

    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.followup.send("Будь ласка, завантажте файл зображення (PNG, JPG тощо).")
        return

    try:
        image_bytes = await image.read()

        data = aiohttp.FormData()
        data.add_field('image', image_bytes, filename=image.filename, content_type=image.content_type)
        data.add_field('text', text)
        data.add_field('textPosition', position.value)
        data.add_field('textColor', color)

        async with aiohttp.ClientSession() as session:
            async with session.post("https://rtyfal.pythonanywhere.com/api/process-image/", data=data) as resp:
                if resp.status == 200:
                    result_bytes = await resp.read()
                    result_file = discord.File(io.BytesIO(result_bytes), filename="processed_image.png")
                    await interaction.followup.send("Ваше оброблене зображення:", file=result_file)
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(f"Помилка сервера ({resp.status}): {error_text}")

    except Exception as e:
        await interaction.followup.send(f"Виникла помилка під час обробки: {e}")

bot.run(TOKEN)