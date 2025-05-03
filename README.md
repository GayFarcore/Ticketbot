# Discord Ticket Bot

A Discord bot that handles tickets using private threads.

## Features

- "Open Ticket" button with customizable message
- Automatically creates a private thread for the user and moderators
- "Close Ticket" button inside the ticket thread
- Designed for hosting on Render.com

## Setup

1. Clone the repo and upload to GitHub
2. Set `DISCORD_BOT_TOKEN` in your Render environment
3. Deploy a web service with `main.py` as the entry point
4. Use `/setup_ticket <your message>` in a channel to initialize

## Dependencies

- discord.py v2+

## License

MIT