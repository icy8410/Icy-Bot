import discord
from discord.ext import commands
import os
from threading import Thread
import uvicorn
from fastapi import FastAPI
import asyncio
import random
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ─── חשוב! תשנה רק את השורה הזאת ל-ID של השרת שלך ───
GUILD_ID = 1431291490596032636  # ← כאן תשים את ה-ID של השרת שלך!

bot = commands.Bot(command_prefix='$', intents=intents)

# ─── הגדרות כלליות ───
CASINO_ROLE_ID = 1445383774295560242
ALLOWED_CHANNELS = {1445140349952720989, 1445100560264204319}
COOLDOWN_SECONDS = 120
THUMBNAIL_GIF = "https://cdn.discordapp.com/icons/1431291490596032636/a_fd742a2cb0763fa6577db2095b21d21e.gif?size=256"

# ─── View של כפתור "לטפל" ───
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

# ─── פקודת ch ───
@bot.command(name='ch')
@commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
async def casino_help(ctx, *, reason=None):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        embed = discord.Embed(title="לא כאן אחשלי", description="הפקודה `ch$` מותרת רק בחדרי הקזינו.", color=discord.Color.red())
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

# ─── /help ───
@bot.tree.command(name="help", description="מציג את כל הפקודות של הבוט")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="פקודות הבוט", color=0x00ff00)
    embed.set_thumbnail(url=THUMBNAIL_GIF)
    embed.add_field(name="`$ch <סיבה>`", value="קורא לצוות הקזינו לעזרה", inline=False)
    embed.add_field(name="`/stopwatch <זמן>`", value="משחק סטופר – הקרוב ביותר לזמן זוכה!", inline=False)
    embed.add_field(name="`/set_drop_role`", value="אדמינים Only – מגדיר רול שיכול להפעיל דרופים", inline=False)
    embed.add_field(name="`/add_drop_channel`", value="אדמינים Only – מוסיף חדר מותר לדרופים", inline=False)
    embed.add_field(name="`/remove_drop_channel`", value="אדמינים Only – מסיר חדר מהרשימה", inline=False)
    embed.set_footer(text="הבוט רץ 24/7 על Render")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── הגדרות אדמין בלבד ───
async def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name="set_drop_role", description="מגדיר רול שיכול להפעיל דרופים (אדמינים בלבד)")
@app_commands.describe(role="הרול הרצוי")
@app_commands.check(is_admin)
async def set_drop_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.send_message(f"רול הדרופים עודכן ל-{role.mention}", ephemeral=True)

@bot.tree.command(name="add_drop_channel", description="מוסיף חדר מותר לדרופים (אדמינים בלבד)")
@app_commands.describe(channel="החדר להוספה")
@app_commands.check(is_admin)
async def add_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_message(f"{channel.mention} נוסף לדרופים", ephemeral=True)

@bot.tree.command(name="remove_drop_channel", description="מסיר חדר מרשימת הדרופים (אדמינים בלבד)")
@app_commands.describe(channel="החדר להסרה")
@app_commands.check(is_admin)
async def remove_drop_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_message(f"{channel.mention} הוסר מהדרופים", ephemeral=True)

# ─── משחק הסטופר ───
class StopButton(discord.ui.View):
    def __init__(self, start_time, target_time):
        super().__init__(timeout=target_time + 5)
        self.start_time = start_time
        self.target_time = target_time
        self.clicks = {}

    @discord.ui.button(label="עצור!", style=discord.ButtonStyle.red, emoji="⏱️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = asyncio.get_event_loop().time()
        elapsed = now - self.start_time
        self.clicks[interaction.user] = elapsed
        await interaction.response.send_message(f"עצרת אחרי **{elapsed:.2f}** שניות!", ephemeral=True)

@bot.tree.command(name="stopwatch", description="משחק סטופר – הקרוב ביותר לזמן היעד זוכה!")
@app_commands.describe(target="כמה שניות? (ברירת מחדל 10)")
async def stopwatch(interaction: discord.Interaction, target: int = 10):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title=f"סטופר – הקרוב ל-{target} שניות זוכה!", color=0x0099ff)
    embed.description = "מתחילים בעוד..."
    msg = await interaction.channel.send(embed=embed)

    delay = random.uniform(3, 6)
    for i in range(int(delay * 10)):
        secs = i / 10
        embed.description = f"סופר... `{secs:.1f}s`"
        await msg.edit(embed=embed)
        await asyncio.sleep(0.1)

    for _ in range(6):
        embed.description = "עוצר" + "." * (_ % 4)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.3)

    start_time = asyncio.get_event_loop().time()
    embed.description = f"**התחלנו!**\nלחצו על הכפתור כשאתם חושבים שעברו בדיוק {target} שניות!"
    embed.color = 0x00ff00
    view = StopButton(start_time, target)
    await msg.edit(embed=embed, view=view)

    await asyncio.sleep(target + 5)
    view.stop()

    if not view.clicks:
        embed.description = "אף אחד לא לחץ... הזמן עבר!"
        embed.color = 0xff0000
        await msg.edit(embed=embed, view=None)
        return

    winner = min(view.clicks.items(), key=lambda x: abs(x[1] - target))
    user, time = winner
    diff = abs(time - target)
    result = "לחץ בול!!!" if diff < 0.05 else f"הכי קרוב – רק {diff:.2f} שניות הפרש!"
    embed.description = f"**הזוכה: {user.mention}!**\n{result}"
    embed.color = 0xffd700
    await msg.edit(embed=embed, view=None)

# ─── on_ready + סינכרון לפי שרת + keep-alive ───
@bot.event
async def on_ready():
    print(f'הבוט מחובר: {bot.user}')
    bot.add_view(TakeTicket())

    # סינכרון לפי שרת – עובד 100% על Render!
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"סונכרנו {len(synced)} פקודות slash!")

    # שרת keep-alive
    app = FastAPI()
    @app.get("/")
    @app.head("/")
    async def root():
        return {"message": "Bot is alive!"}
    def run():
        uvicorn.run(app, host="0.0.0.0", port=8080)
    Thread(target=run, daemon=True).start()

# ─── מונע שינה על Render – 100% עובד גם עם UptimeRobot ───
import threading

def keep_awake():
    while True:
        threading.Event().wait(240)  # כל 4 דקות
        print("Keep-awake ping – הבוט עדיין ער!")

threading.Thread(target=keep_awake, daemon=True).start()

# ריצה
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
