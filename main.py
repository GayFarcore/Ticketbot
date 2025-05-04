import os
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, Thread
from flask import Flask
import threading
import asyncio
import re

# --- Keep-alive web server for Render ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

web_thread = threading.Thread(target=run_web)
web_thread.start()
# ----------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1368483776149323816  # Replace with your log channel ID


# --- Util: Thread naming sanitation ---
def sanitize_title(title: str) -> str:
    title = re.sub(r"[^\w\s-]", "", title)
    return title.strip().replace(" ", "-")[:80]


# --- View for closing a ticket ---
class CloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: Interaction, button: ui.Button):
        if isinstance(interaction.channel, Thread):
            thread: Thread = interaction.channel

            # Collect all users who sent a message
            participants = set()
            async for msg in thread.history(limit=None):
                participants.add(msg.author)

            for user in participants:
                if user.bot:
                    continue
                member = interaction.guild.get_member(user.id)
                if member and not any(role.permissions.administrator for role in member.roles):
                    try:
                        await thread.remove_user(member)
                    except discord.Forbidden:
                        pass

            await thread.send("✅ Ticket closed. Only staff can view this thread.")
            await interaction.response.send_message("Closed the ticket for non-staff users.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This button must be used inside a ticket thread.", ephemeral=True)


# --- Modal for reason input ---
class TicketReasonModal(ui.Modal, title="Open a Ticket"):
    reason = ui.TextInput(
        label="Why are you opening a ticket?",
        placeholder="Describe your issue...",
        max_length=200
    )

    def __init__(self, user: discord.User, origin_interaction: Interaction):
        super().__init__()
        self.user = user
        self.origin_interaction = origin_interaction

    async def on_submit(self, interaction: Interaction):
        thread_name = sanitize_title(self.reason.value[:50])
        thread_title = f"ticket-{thread_name}"

        # Create private thread
        thread = await self.origin_interaction.channel.create_thread(
            name=thread_title,
            type=discord.ChannelType.private_thread,
            invitable=False
        )

        # Add user
        await thread.add_user(self.user)

        # Send message in thread with close button
        await thread.send(
            embed=discord.Embed(
                title="🎫 New Ticket",
                description=f"{self.user.mention} has opened a ticket.\n\n**Reason:** {self.reason.value}",
                color=discord.Color.green()
            ),
            view=CloseView()
        )

        # Ephemeral response to user
        await interaction.response.send_message(
            f"✅ Your ticket has been created: {thread.mention}",
            ephemeral=True
        )

        # Log to ticket log channel
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📥 Ticket Opened",
                description=(
                    f"**User:** {self.user.mention}\n"
                    f"**Reason:** {self.reason.value}\n"
                    f"**Thread:** {thread.mention}"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"User ID: {self.user.id}")
            await log_channel.send(embed=embed)


# --- View for opening a ticket ---
class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketReasonModal(interaction.user, interaction))


# --- On bot ready: sync commands + register persistent views ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(TicketView())
    bot.add_view(CloseView())  # Ensures button works across restarts
    print(f"✅ Bot is ready as {bot.user}")


# --- Setup command for admin ---
@bot.tree.command(name="setup_ticket")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: Interaction, message: str):
    embed = discord.Embed(
        title="🎟️ Support Ticket",
        description=message,
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket system initialized.", ephemeral=True)


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
