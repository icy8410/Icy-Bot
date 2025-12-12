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

# ─── הגדרות כלליות ───
CASINO_ROLE_ID = 1445383774295560242
ALLOWED_CHANNELS = {1445140349952720989, 1445100560264204319}
COOLDOWN_SECONDS = 120
THUMBNAIL_GIF = "https://cdn.discordapp.com/icons/1431291490596032636/a_fd742a2cb0763fa6577db2095b21d21e.gif?size=256"

# קובץ הגדרות
CONFIG_FILE = 'config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'drop_role_id': None, 'drop_allowed_channels': []}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

config = load_config()

# ─── View של כפתור "לטפל" ───
class TakeTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="לטפל", style=discord.ButtonStyle.green, emoji="", custom_id="take_ticket_button")
    async def take_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if any(role.id == CASINO_ROLE_ID for role in interaction.user.roles):
            button.label = f"מטופל ע״י {interaction.user.name}"
            button.style = discord.ButtonStyle.grey
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"{interaction.user.mention} לקח את הקריאה!", ephemeral=True)
        else:
            await interaction.response.send_message("אחשלי אתה לא צוות קזינו", ephemeral=True)

# ─── פקודת ch ישנה ───
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

# ─── עזרה – /help ───
@bot.tree.command(name="help", description="מציג את כל הפקודות של הבוט")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="פקודות הבוט", color=0x00ff00)
    embed.set_thumbnail(url=THUMBNAIL_GIF)

    embed.add_field(name="`$ch <סיבה>`", value="קורא לצוות הקזינו לעזרה", inline=False)
    embed.add_field(name="`/stopwatch <זמן>`", value="משחק סטופר – מי שקרוב ביותר לזמן היעד זוכה!", inline=False)
    embed.add_field(name="`/set_drop_role <רול>`", value="**אדמינים בלבד** – מגדיר איזה רול יכול להפעיל דרופים", inline=False)
    embed.add_field(name="`/add_drop_channel <חדר>`", value="**אדמינים בלבד** – מוסיף חדר שבו מותר להפעיל דרופים", inline=False)
    embed.add_field(name="`/remove_drop_channel <חדר>`", value="**אדמינים בלבד** – מסיר חדר מהרשימה", inline=False)
    embed.add_field(name="`/help`", value="מציג את ההודעה הזו", inline=False)

    embed.set_footer(text="הבוט פותח במיוחד בשבילכם")
    await interaction.response.send_message(embed=embed)

# ─── הגדרות אדמין (רק אדמינים) ───
async def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name="set_drop_role", description="מגדיר רול שיכול להפעיל דרופים (אדמינים בלבד)")
@app_commands.describe(role="הרול שיוכל להפעיל דרופים")
@app_commands.check(is_admin)
async def set_drop_role(interaction: discord.Interaction, role: discord.Role):
    config['drop_role_id'] = role.id
    save_config(config)
    await interaction.response.send_message(f"רול הדרופים עודכן ל-{role.mention}", ephemeral=True)

@bot.tree.command(name="add_drop_channel", description="מוסיף חדר שבו מותר להפעיל דרופים (אדמינים בלבד)")
@app_commands.describe(channel="החדר להוספה")
@app_commands.check(is_admin)
async def add_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id not in config['drop_allowed_channels']:
        config['drop_allowed_channels'].append(channel.id)
        save_config(config)
        await interaction.response.send_message(f"{channel.mention} נוסף לחדרי דרופים", ephemeral=True)
    else:
        await interaction.response.send_message("החדר כבר ברשימה", ephemeral=True)

@bot.tree.command(name="remove_drop_channel", description="מסיר חדר מרשימת חדרי הדרופים (אדמינים בלבד)")
@app_commands.describe(channel="החדר להסרה")
@app_commands.check(is_admin)
async def remove_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in config['drop_allowed_channels']:
        config['drop_allowed_channels'].remove(channel.id)
        save_config(config)
        await interaction.response.send_message(f"{channel.mention} הוסר מחדרי דרופים", ephemeral=True)
    else:
        await interaction.response.send_message("החדר לא היה ברשימה", ephemeral=True)

# ─── משחק הסטופר המושלם ───
class StopButton(discord.ui.View):
    def __init__(self, start_time, target_time):
        super().__init__(timeout=target_time + 5)
        self.start_time = start_time
        self.target_time = target_time
        self.clicks = {}

    @discord.ui.button(label="עצור!", style=discord.ButtonStyle.red, emoji="")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = asyncio.get_event_loop().time()
        elapsed = now - self.start_time
        self.clicks[interaction.user] = elapsed
        await interaction.response.send_message(f"עצרת אחרי **{elapsed:.2f}** שניות!", ephemeral=True)

@bot.tree.command(name="stopwatch", description="משחק סטופר – הקרוב ביותר לזמן היעד זוכה!")
@app_commands.describe(target="כמה שניות היעד? (למשל 10)")
async def stopwatch(interaction: discord.Interaction, target: int = 10):
    # בדיקת רול
    if config['drop_role_id'] and not any(r.id == config['drop_role_id'] for r in interaction.user.roles):
        await interaction.response.send_message("אין לך הרשאה להפעיל דרופים!", ephemeral=True)
        return
    # בדיקת חדר
    if config['drop_allowed_channels'] and interaction.channel_id not in config['drop_allowed_channels']:
        await interaction.response.send_message("אסור להפעיל דרופים בחדר הזה!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(title="סטופר – הקרוב ל-{} שניות זוכה!".format(target), color=0x0099ff)
    embed.description = "מתחילים בעוד..."
    msg = await interaction.channel.send(embed=embed)

    # ספירה רנדומלית 3-6 שניות
    delay = random.uniform(3, 6)
    for i in range(int(delay * 10)):
        secs = i / 10
        embed.description = f"סופר... `{secs:.1f}`"
        await msg.edit(embed=embed)
        await asyncio.sleep(0.1)

    # אנימציית עצירה
    for _ in range(6):
        embed.description = "עוצר" + "." * (_ % 4)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.3)

    # התחלה!
    start_time = asyncio.get_event_loop().time()
    embed.description = f"**התחלנו!**\nלחצו על הכפתור כשאתם חושבים שעברו בדיוק {target} שניות!"
    embed.color = 0x00ff00
    view = StopButton(start_time, target)
    await msg.edit(embed=embed, view=view)

    # חכה עד סיום
    await asyncio.sleep(target + 5)
    view.stop()

    if not view.clicks:
        embed.description = "אף אחד לא לחץ... הזמן עבר!"
        embed.color = 0xff0000
        await msg.edit(embed=embed, view=None)
        await interaction.followup.send("אף אחד לא השתתף", ephemeral=True)
        return

    # מצא זוכה
    winner = min(view.clicks.items(), key=lambda x: abs(x[1] - target))
    user, time = winner
    diff = abs(time - target)

    if diff < 0.05:
        result = "לחץ **בול על 10 שניות**!!!"
    elif diff < 0.3:
        result = f"קרוב מאוד! רק **{diff:.2f}** שניות הפרש!"
    else:
        result = f"הכי קרוב עם **{diff:.2f}** שניות הפרש!"

    embed.description = f"**הזוכה: {user.mention}!**\n{result}"
    embed.color = 0xffd700
    await msg.edit(embed=embed, view=None)
    await interaction.followup.send("המשחק הסתיים!", ephemeral=True)

# ─── on_ready + שרת keep-alive ───
@bot.event
async def on_ready():
    print(f'הבוט מחובר ועובד 24/7! שם: {bot.user}')
    bot.add_view(TakeTicket())
    await bot.tree.sync()  # חשוב! כדי שה-slash commands יופיעו

    app = FastAPI()
    @app.get("/")
    @app.head("/")
    async def root():
        return {"message": "Bot is alive!"}
    def run():
        uvicorn.run(app, host="0.0.0.0", port=8080)
    Thread(target=run, daemon=True).start()
    
# פקודה ל-sync ידני (רק לך – בעל הבוט)
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("הפקודות סונכרנו! עכשיו תראה את כל ה-slash commands")
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
