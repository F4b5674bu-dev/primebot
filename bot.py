import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View
import random
from datetime import datetime, timedelta, timezone

# =========================
# KONFIG
# =========================
TOKEN = "DEIN_TOKEN_HIER"
BOT_VERSION = "v2.1(Build N.385)"

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
            winners_count = min(len(participants), data["winners"])

            if winners_count == 0:
                await channel.send("❌ Niemand hat teilgenommen.")
                continue

            winners = random.sample(participants, winners_count)

            result = "\n".join(
                f"**{i+1}.** <@{uid}>"
                for i, uid in enumerate(winners)
            )

            embed = discord.Embed(
                title="🎉 Giveaway beendet",
                description=result,
                color=discord.Color.gold()
            )
            embed.set_footer(text=data["titel"])

            await channel.send(embed=embed)

            data["final_winners"] = winners
            finished_giveaways[gid] = data

    for gid in finished:
        del active_giveaways[gid]

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"Primebot {BOT_VERSION}"
    )

    await bot.change_presence(
        status=discord.Status.online,
        activity=activity
    )

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
    beschreibung: str,
    dauer: int,
    winners: int
):
    ende = datetime.now(timezone.utc) + timedelta(minutes=dauer)
    participants = set()

    embed = discord.Embed(
        title=f"🎉 {titel}",
        description=beschreibung,
        color=discord.Color.gold()
    )
    embed.add_field(name="Endet um", value=f"<t:{int(ende.timestamp())}:t>")
    embed.add_field(name="Teilnehmer", value="0")
    embed.add_field(name="Gewinner", value=str(winners))
    embed.set_footer(text="Klicke auf den Button, um teilzunehmen")

    button = Button(label="Teilnehmen", style=discord.ButtonStyle.green)

    async def join_callback(i: discord.Interaction):
        participants.add(i.user.id)
        embed.set_field_at(1, name="Teilnehmer", value=str(len(participants)))
        await i.response.edit_message(embed=embed)
        await i.followup.send("✅ Du bist dabei!", ephemeral=True)

    button.callback = join_callback
    view = View()
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

    active_giveaways[msg.id] = {
        "titel": titel,
        "ende": ende,
        "channel": msg.channel.id,
        "participants": participants,
        "winners": winners
    }

# =========================
# /reroll
# =========================
@bot.tree.command(name="reroll", description="Ziehe neuen Gewinner")
async def reroll(interaction: discord.Interaction, message_id: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Nur Admins.", ephemeral=True)
        return

    try:
        mid = int(message_id)
        data = finished_giveaways[mid]
    except:
        await interaction.response.send_message("❌ Ungültige ID.", ephemeral=True)
        return

    winner = random.choice(list(data["participants"]))

    embed = discord.Embed(
        title="🔁 Reroll",
        description=f"**1.** <@{winner}>",
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)

# =========================
# /gamble
# =========================
@bot.tree.command(name="gamble", description="Lose Gewinner aus")
async def gamble(interaction: discord.Interaction, users: str, winners: int):
    user_ids = []

    for word in users.split():
        if word.startswith("<@") and word.endswith(">"):
            uid = word.replace("<@", "").replace(">", "").replace("!", "")
            if uid.isdigit():
                user_ids.append(int(uid))

    if len(user_ids) < 2:
        await interaction.response.send_message("❌ Mindestens 2 User.", ephemeral=True)
        return

    winners = min(winners, len(user_ids))
    chosen = random.sample(user_ids, winners)

    result = "\n".join(
        f"**{i+1}.** <@{uid}>"
        for i, uid in enumerate(chosen)
    )

    embed = discord.Embed(
        title="🎲 Gamble Ergebnis",
        description=result,
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Teilnehmer: {len(user_ids)}")

    await interaction.response.send_message(embed=embed)

# =========================
# /groups  ⭐ NEU ⭐
# =========================
@bot.tree.command(name="groups", description="Erstelle zufällige, gleich große Teams")
async def groups(interaction: discord.Interaction, users: str, teams: int):
    user_ids = []

    for word in users.split():
        if word.startswith("<@") and word.endswith(">"):
            uid = word.replace("<@", "").replace(">", "").replace("!", "")
            if uid.isdigit():
                user_ids.append(int(uid))

    if teams < 2:
        await interaction.response.send_message("❌ Mindestens 2 Teams.", ephemeral=True)
        return

    if len(user_ids) < teams:
        await interaction.response.send_message("❌ Zu wenige User.", ephemeral=True)
        return

    if len(user_ids) % teams != 0:
        await interaction.response.send_message(
            "❌ Useranzahl muss durch Teamanzahl teilbar sein.",
            ephemeral=True
        )
        return

    random.shuffle(user_ids)
    per_team = len(user_ids) // teams

    embed = discord.Embed(
        title="👥 Team-Aufteilung",
        color=discord.Color.orange()
    )

    for i in range(teams):
        team_users = user_ids[i * per_team:(i + 1) * per_team]
        value = "\n".join(f"<@{uid}>" for uid in team_users)
        embed.add_field(
            name=f"Team {i + 1}",
            value=value,
            inline=False
        )

    embed.set_footer(text=f"{len(user_ids)} Spieler • {teams} Teams")

    await interaction.response.send_message(embed=embed)

# =========================
# START
# =========================
bot.run(TOKEN)
