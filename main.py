import discord
from discord.ext import commands
import os
from threading import Thread
import uvicorn
from fastapi import FastAPI

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

# ─── הגדרות ───
CASINO_ROLE_ID = 1445383774295560242
ALLOWED_CHANNELS = {1445140349952720989, 1445100560264204319}
COOLDOWN_SECONDS = 120
THUMBNAIL_GIF = "https://cdn.discordapp.com/icons/1431291490596032636/a_fd742a2cb0763fa6577db2095b21d21e.gif?size=256"

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
