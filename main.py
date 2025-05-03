import os
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, Thread
from flask import Flask
import threading
import asyncio

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
MODERATOR_ROLES = [1358163292220293356, 1358654187705204798, 1358163292220293354, 1358163292182413419, 1359044764804055130, 1358163292182413418]
TICKET_MESSAGE = "Click the button below to open a support ticket."

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: Interaction, button: ui.Button):
        thread_name = f"ticket-{interaction.user.name}"
        thread = await interaction.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(interaction.user)

        for member in interaction.guild.members:
            if any(role.id in MODERATOR_ROLE_IDS for role in member.roles):
                try:
                    await thread.add_user(member)
                except:
                    continue

        await thread.send(
            f"{interaction.user.mention}, your ticket has been created.",
            view=CloseView()
        )
        await interaction.response.send_message(f"Ticket created: {thread.mention}", ephemeral=True)

class CloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: Interaction, button: ui.Button):
        if isinstance(interaction.channel, Thread):
            await interaction.channel.send("Closing ticket in 3 seconds...")
            await asyncio.sleep(3)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("This command can only be used in a ticket thread.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready as {bot.user}")

@bot.tree.command(name="setup_ticket")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: Interaction, message: str):
    await interaction.channel.send(message, view=TicketView())
    await interaction.response.send_message("Ticket system initialized.", ephemeral=True)

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
