import discord
from discord.ext import commands
import os
from threading import Thread
import uvicorn
from fastapi import FastAPI
import asyncio
import json
import random
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

# ─── הגדרות ───
CASINO_ROLE_ID = 1445383774295560242
ALLOWED_CHANNELS = {1445140349952720989, 1445100560264204319}
COOLDOWN_SECONDS = 120
THUMBNAIL_GIF = "https://cdn.discordapp.com/icons/1431291490596032636/a_fd742a2cb0763fa6577db2095b21d21e.gif?size=256"

# קובץ לשמירת הגדרות
CONFIG_FILE = 'config.json'

# טעינת הגדרות
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'drop_role_id': None, 'drop_allowed_channels': []}

# שמירת הגדרות
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

class TakeTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="לטפל", style=discord.ButtonStyle.green, emoji="✔", custom_id="take_ticket_button")
    async def take_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if any(role.id == CASINO_ROLE_ID for role in interaction.user.roles):
            button.label = f"מטופל ע״י {interaction.user.name}"
            button.style = discord.ButtonStyle.grey
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"{interaction.user.mention} לקח את הקריאה!", ephemeral=True)
        else:
            await interaction.response.send_message("אחשלי אתה לא צוות קזינו", ephemeral=True)

@bot.command(name='ch')
@commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
async def casino_help(ctx, *, reason=None):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        embed = discord.Embed(title="לא כאן אחשלי", description="הפקודה `ch$` מותרת **רק** בחדרי הקזינו.", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
        return

    reason = reason.strip() if reason else "לא צוין סיבה"

    embed = discord.Embed(title="עזרה מצוות הקזינו", color=0x00ff00)
    embed.add_field(name="ממבר:", value=ctx.author.mention, inline=False)
    embed.add_field(name="סיבה:", value=reason, inline=False)
    embed.add_field(name="הערות:", value="תמתין בסבלנות הצוות יענה לך מהר הכי שהם יכולים!", inline=False)
    embed.set_footer(text=f"חדר: #{ctx.channel.name}")
    embed.set_thumbnail(url=THUMBNAIL_GIF)

    await ctx.send(f"<@&{CASINO_ROLE_ID}> {ctx.channel.mention}", embed=embed, view=TakeTicket())

@casino_help.error
async def casino_help_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining = int(error.retry_after)
        embed = discord.Embed(
            title="חכה ישמן לא להספים את הפקודה!",
            description=f"חכה עוד **{remaining} שניות** לפני שתוכל להפעיל שוב את הפקודה.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, delete_after=8)

# פקודה להגדרת רול דרופים
@bot.tree.command(name='set_drop_role', description='הגדר את הרול שיכול לבצע פקודות דרופים')
@app_commands.describe(role='הרול להגדרה')
async def set_drop_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_admin(interaction):  # הוסף בדיקת אדמין אם צריך
        await interaction.response.send_message("אין לך הרשאה!", ephemeral=True)
        return
    config['drop_role_id'] = role.id
    save_config(config)
    await interaction.response.send_message(f"רול דרופים הוגדר ל-{role.mention}", ephemeral=True)

# פקודה להוספת חדרים מותרים לדרופים
@bot.tree.command(name='add_drop_channel', description='הוסף חדר מותר לפקודות דרופים')
@app_commands.describe(channel='החדר להוספה')
async def add_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await check_admin(interaction):
        await interaction.response.send_message("אין לך הרשאה!", ephemeral=True)
        return
    if channel.id not in config['drop_allowed_channels']:
        config['drop_allowed_channels'].append(channel.id)
        save_config(config)
        await interaction.response.send_message(f"חדר {channel.mention} הוסף למותרים לדרופים", ephemeral=True)
    else:
        await interaction.response.send_message("החדר כבר מותר", ephemeral=True)

# פקודה להסרת חדרים מותרים
@bot.tree.command(name='remove_drop_channel', description='הסר חדר מותר לפקודות דרופים')
@app_commands.describe(channel='החדר להסרה')
async def remove_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await check_admin(interaction):
        await interaction.response.send_message("אין לך הרשאה!", ephemeral=True)
        return
    if channel.id in config['drop_allowed_channels']:
        config['drop_allowed_channels'].remove(channel.id)
        save_config(config)
        await interaction.response.send_message(f"חדר {channel.mention} הוסר מהמותרים לדרופים", ephemeral=True)
    else:
        await interaction.response.send_message("החדר לא מותר", ephemeral=True)

# בדיקת הרשאה (הוסף בדיקה לאדמין אם צריך, כאן רק דוגמה)
async def check_admin(interaction: discord.Interaction):
    # שנה למה שמתאים לך, למשל אם יש רול אדמין
    return True  # או return interaction.user.guild_permissions.administrator

# View לכפתור עצירה
class StopButton(discord.ui.View):
    def __init__(self, start_time, target_time):
        super().__init__(timeout=target_time + 5)
        self.start_time = start_time
        self.target_time = target_time
        self.times = {}  # משתמש: זמן לחיצה

    @discord.ui.button(label="עצור!", style=discord.ButtonStyle.primary)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = asyncio.get_event_loop().time()
        user_time = now - self.start_time
        self.times[interaction.user.id] = user_time
        await interaction.response.send_message(f"לחצת אחרי {user_time:.1f} שניות!", ephemeral=True)

# פקודה למשחק סטופר
@bot.tree.command(name='stopwatch', description='התחל משחק סטופר – הקרוב ביותר לזמן היעד זוכה')
@app_commands.describe(target='הזמן היעד בשניות (למשל 10)')
async def stopwatch(interaction: discord.Interaction, target: int):
    if config['drop_role_id'] is None or not any(role.id == config['drop_role_id'] for role in interaction.user.roles):
        await interaction.response.send_message("אין לך הרשאה לבצע פקודת דרופים!", ephemeral=True)
        return
    if config['drop_allowed_channels'] and interaction.channel_id not in config['drop_allowed_channels']:
        await interaction.response.send_message("הפקודה מותרת רק בחדרים מסוימים!", ephemeral=True)
        return

    await interaction.response.send_message("מתחיל משחק סטופר...", ephemeral=True)

    embed = discord.Embed(title=f"משחק סטופר – הקרוב ל-{target} שניות זוכה!", color=0x00ff00)
    embed.description = "מחכה להתחלה..."
    message = await interaction.channel.send(embed=embed)

    # ספירה ראשונית רנדומלית 3-6 שניות
    random_stop = random.uniform(3, 6)
    start_loop = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_loop < random_stop:
        current = asyncio.get_event_loop().time() - start_loop
        embed.description = f"סופר... {current:.1f}"
        await message.edit(embed=embed)
        await asyncio.sleep(0.1)

    # אנימציה של עצירה
    for i in range(5):
        embed.description = "עוצר!" + "." * (i % 4)
        await message.edit(embed=embed)
        await asyncio.sleep(0.2)

    # התחלת הזמן האמיתי
    start_time = asyncio.get_event_loop().time()
    embed.description = f"GO! לחץ עצור כשאתה חושב שעברו {target} שניות."
    view = StopButton(start_time, target)
    await message.edit(embed=embed, view=view)

    await view.wait()

    # סיום
    if not view.times:
        embed.description = "עבר הזמן – אף אחד לא לחץ!"
        await message.edit(embed=embed, view=None)
        return

    # מציאת הזוכה
    winner_id, winner_time = min(view.times.items(), key=lambda x: abs(x[1] - target))
    winner = interaction.guild.get_member(winner_id)
    diff = abs(winner_time - target)
    if diff == 0:
        msg = "לחץ בול!"
    else:
        msg = f"היה קרוב ב-{diff:.1f} שניות!"
    embed.description = f"הזוכה הוא {winner.mention}! {msg}"
    await message.edit(embed=embed, view=None)

@bot.event
async def on_ready():
    print(f'הבוט מחובר ועובד 24/7! שם: {bot.user}')
    bot.add_view(TakeTicket())

    # ─── שרת קטן שמקבל גם GET וגם HEAD (כדי ש-UptimeRobot לא יקבל 405) ───
    app = FastAPI()

    @app.get("/")
    @app.head("/")  # ← זה מה שפותר את ה-405!
    async def root():
        return {"message": "Bot is alive! Casino Help Bot is running 24/7!"}

    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=8080)

    Thread(target=run_server, daemon=True).start()

# ריצה
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
