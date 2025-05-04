import os
import re
import discord
import asyncio
import threading
from discord.ext import commands
from discord import app_commands, ui, Interaction, Thread
from flask import Flask

# --- Keep-alive web server for Render ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web).start()
# ----------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1368483776149323816  # Replace with your log channel ID


def sanitize_title(title: str) -> str:
    title = re.sub(r"[^\w\s-]", "", title)
    return title.strip().replace(" ", "-")[:80]


class CloseView(ui.View):
    def __init__(self, thread: Thread, opener_id: int):
        super().__init__(timeout=None)
        self.thread = thread
        self.opener_id = opener_id

    @ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: Interaction, button: ui.Button):
        if not isinstance(interaction.channel, Thread):
            return await interaction.response.send_message("❌ This button must be used in a thread.", ephemeral=True)

        participants = set()
        async for msg in interaction.channel.history(limit=None):
            participants.add(msg.author.id)

        for user_id in participants:
            member = interaction.guild.get_member(user_id)
            if member and not member.bot:
                if not member.guild_permissions.administrator:
                    try:
                        await interaction.channel.remove_user(member)
                    except discord.Forbidden:
                        pass

        await interaction.channel.send("✅ Ticket closed. Only staff can view this now.")
        await interaction.response.send_message("Ticket successfully closed.", ephemeral=True)


class TicketReasonModal(ui.Modal, title="Open a Ticket"):
    reason = ui.TextInput(
        label="Why are you opening a ticket?",
        placeholder="Briefly explain your issue...",
        max_length=200
    )

    def __init__(self, user: discord.User, interaction: Interaction):
        super().__init__()
        self.user = user
        self.origin_interaction = interaction

    async def on_submit(self, interaction: Interaction):
        thread_name = sanitize_title(f"{self.reason.value[:50]}")

        thread = await self.origin_interaction.channel.create_thread(
            name=f"ticket-{thread_name}",
            type=discord.ChannelType.private_thread,
            invitable=False
        )

        await thread.add_user(self.user)

        await thread.send(
            embed=discord.Embed(
                title="🎫 New Ticket",
                description=f"{self.user.mention} has opened a ticket.\n\n**Reason:** {self.reason.value}",
                color=discord.Color.green()
            ),
            view=CloseView(thread, self.user.id)
        )

        await self.origin_interaction.followup.send(f"🎫 Ticket created: {thread.mention}", ephemeral=True)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🆕 Ticket Opened",
                description=(
                    f"**User:** {self.user.mention}\n"
                    f"**Thread:** {thread.mention}\n"
                    f"**Reason:** {self.reason.value}"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"User ID: {self.user.id}")
            await log_channel.send(embed=embed)


class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketReasonModal(interaction.user, interaction))


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready as {bot.user}")


@bot.tree.command(name="setup_ticket", description="Send the ticket system message.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: Interaction, message: str):
    embed = discord.Embed(
        title="🎟️ Support Ticket",
        description=message,
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket system initialized.", ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need **Administrator** permissions to use this command.",
            ephemeral=True
        )
    else:
        raise error


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
