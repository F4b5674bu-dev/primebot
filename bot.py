import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View
import random
from datetime import datetime, timedelta, timezone

# =========================
# KONFIG
# =========================
TOKEN = "111"  # PLATZHALTER – wird später in Railway ersetzt
BOT_VERSION = "v2.1(Build N.375)"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_giveaways = {}
finished_giveaways = {}

# =========================
# GIVEAWAY CHECKER
# =========================
@tasks.loop(seconds=10)
async def giveaway_checker():
    now = datetime.now(timezone.utc)
    finished = []

    for gid, data in active_giveaways.items():
        if now >= data["ende"]:
            finished.append(gid)

            channel = bot.get_channel(data["channel"])
            if not channel:
                continue

            participants = list(data["participants"])
            if not participants:
                await channel.send("❌ Niemand hat teilgenommen.")
                continue

            winners = random.sample(
                participants,
                min(len(participants), data["winners"])
            )

            embed = discord.Embed(
                title="🎉 Giveaway beendet",
                description="\n".join(f"<@{w}>" for w in winners),
                color=discord.Color.gold()
            )

            await channel.send(embed=embed)
            finished_giveaways[gid] = data

    for gid in finished:
        del active_giveaways[gid]

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    if not giveaway_checker.is_running():
        giveaway_checker.start()
    print(f"Bot online als {bot.user}")

# =========================
# /giveaway
# =========================
@bot.tree.command(name="giveaway", description="Starte ein Giveaway")
async def giveaway(
    interaction: discord.Interaction,
    titel: str,
    dauer: int,
    winners: int
):
    ende = datetime.now(timezone.utc) + timedelta(minutes=dauer)
    participants = set()

    embed = discord.Embed(
        title=f"🎉 {titel}",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Endet",
        value=f"<t:{int(ende.timestamp())}:R>"
    )
    embed.add_field(
        name="Teilnehmer",
        value="0"
    )

    button = Button(
        label="Teilnehmen",
        style=discord.ButtonStyle.green
    )

    async def join_callback(i: discord.Interaction):
        participants.add(i.user.id)
        embed.set_field_at(
            1,
            name="Teilnehmer",
            value=str(len(participants))
        )
        await i.response.edit_message(embed=embed)

    button.callback = join_callback
    view = View()
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

    active_giveaways[msg.id] = {
        "ende": ende,
        "participants": participants,
        "winners": winners,
        "channel": msg.channel.id
    }

# =========================
# START
# =========================
bot.run(TOKEN)
