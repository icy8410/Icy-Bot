import discord
from discord.ext import commands
import os
from threading import Thread
import uvicorn
from fastapi import FastAPI
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

# ─── פקודת $ch (עם תיקון מלא – תמיד שולח הודעה) ───
@bot.command(name='ch')
@commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
async def casino_help(ctx, *, reason=None):
    if ctx.channel.id not in ALLOWED_CHANNELS:
        embed = discord.Embed(title="לא כאן אחשלי", description="הפקודה `ch$` מותרת **רק** בחדרי הקזינו.", color=discord.Color.red())
        try:
            await ctx.send(embed=embed, delete_after=10)
        except discord.Forbidden:
            await ctx.send(embed=embed)
        return

    reason = reason.strip() if reason else "לא צוין סיבה"
    embed = discord.Embed(title="עזרה מצוות הקזינו", color=0x00ff00)
    embed.add_field(name="ממבר:", value=ctx.author.mention, inline=False)
    embed.add_field(name="סיבה:", value=reason, inline=False)
    embed.add_field(name="הערות:", value="תמתין בסבלנות הצוות יענה לך מהר הכי שהם יכולים!", inline=False)
    embed.set_footer(text=f"חדר: #{ctx.channel.name}")
    embed.set_thumbnail(url=THUMBNAIL_GIF)
    await ctx.send(f"<@&{CASINO_ROLE_ID}> {ctx.channel.mention}", embed=embed, view=TakeTicket())

# ─── תיקון שגיאות – תמיד שולח הודעה! ───
@casino_help.error
async def casino_help_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining = int(error.retry_after)
        embed = discord.Embed(
            title="חכה קצת אחשלי",
            description=f"חכה עוד **{remaining} שניות** לפני שתוכל להשתמש ב-$ch שוב.",
            color=discord.Color.orange()
        )
        try:
            await ctx.send(embed=embed, delete_after=8)
        except discord.Forbidden:
            await ctx.send(embed=embed)

# ─── /help יפה ───
@bot.tree.command(name="help", description="מציג את כל הפקודות של הבוט")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="פקודות הבוט", color=0x00ff00)
    embed.set_thumbnail(url=THUMBNAIL_GIF)
    embed.add_field(name="`$ch <סיבה>`", value="קורא לצוות הקזינו לעזרה", inline=False)
    embed.add_field(name="`/help`", value="מציג את ההודעה הזו", inline=False)
    embed.set_footer(text="הבוט רץ 24/7 על Render – בלי תקלות!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── on_ready + סינכרון + keep-alive ───
@bot.event
async def on_ready():
    print(f'הבוט מחובר: {bot.user}')
    bot.add_view(TakeTicket())

    # סינכרון לפי שרת – מראה את /help תוך 10 שניות
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

    # מונע שינה על Render
    def keep_awake():
        while True:
            threading.Event().wait(240)
            print("Keep-awake ping – הבוט ער!")
    threading.Thread(target=keep_awake, daemon=True).start()

# ריצה
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
