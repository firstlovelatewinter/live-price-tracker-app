import discord
import os
import asyncio

async def send_price_drop_notification(product):
    token = os.environ.get('DISCORD_BOT_TOKEN')
    user_id = os.environ.get('DISCORD_USER_ID')

    if not token or not user_id:
        print("Discord token or user ID not set. Skipping notification.")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        user = await client.fetch_user(int(user_id))
        if user:
            message = (
                f"**Price Drop Alert!**\n\n"
                f"**{product['name']}** is now **${product['current_price']:.2f}**!\n\n"
                f"View it here: {product['url']}"
            )
            await user.send(message)
            print(f"Sent price drop notification to {user.name}")
        await client.close()

    try:
        await client.start(token)
    except discord.LoginFailure:
        print("Failed to log in to Discord. Please check your bot token.")
    except Exception as e:
        print(f"An error occurred: {e}")

def notify_price_drop(product):
    # Run the async discord logic in a new event loop
    asyncio.run(send_price_drop_notification(product))
