import discord
import requests
import json
import asyncio
import os
import random
import psutil
from discord.ext import tasks
from discord.ext import commands
import re
import aiohttp
from dotenv import load_dotenv
from server import keep_alive

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "em!"
LOG_CHANNEL_ID = 1193285574551941191

intents = discord.Intents.default()
intents.dm_messages = True
intents.message_content = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='em!', intents=intents)


def load_channels():
    try:
        with open('channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_channels(channels):
    with open('channels.json', 'w') as f:
        json.dump(channels, f)


# Create a lock
lock = asyncio.Lock()

# Shared sent_memes list
sent_memes = []


async def send_random_meme():
    print("Inside send_random_meme function")  # Debug statement

    # Initialize a flag to indicate whether a suitable meme has been found
    found = False
    meme_url = None

    # Loop until a suitable meme is found
    while not found:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meme-api.com/gimme/memes') as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        meme_url = data['url']
                        nsfw = data['nsfw']
                        title = data['title']

                        # Use the lock when checking and updating the sent_memes list
                        async with lock:
                            if meme_url in sent_memes[-20:]:
                                continue  # Skip this meme and try another one
                            else:
                                if not nsfw and not contains_inappropriate_words(title) and meme_url != 'https://i.redd.it/03p7uh2xpg7c1.gif' and meme_url != 'https://i.redd.it/f3e33eszxf8c1.png':
                                    # Add the sent meme to the list
                                    sent_memes.append(meme_url)
                                    # If the size of the sent_memes list exceeds 20, remove the oldest meme
                                    if len(sent_memes) > 20:
                                        sent_memes.pop(0)
                                    found = True  # Set the flag to True to exit the loop
                                else:
                                    print("not found")
                                    continue  # Skip this meme and try another one
                    except json.JSONDecodeError:
                        print("Invalid JSON response from the meme API.")
                        break  # Exit the loop if there is an error
                else:
                    print("Failed to make a request to the meme API.")
                    break  # Exit the loop if there is an error

    return meme_url


def contains_inappropriate_words(text):
    inappropriate_words = ['swear_word1', 'swear_word2',
                           'inappropriate_word1', 'inappropriate_word2']
    pattern = r'\b(?:{})\b'.format(
        '|'.join(map(re.escape, inappropriate_words)))
    if re.search(pattern, text, flags=re.IGNORECASE):
        return True
    return False


async def enable_auto_meme(channel):
    channels = load_channels()
    if 'channel_ids' in channels and channel.id in channels['channel_ids']:
        await channel.send("Already enabled scheduled memes.")
    else:
        channels.setdefault('channel_ids', []).append(channel.id)
        save_channels(channels)
        await channel.send("Auto meme enabled for this channel.")


async def disable_auto_meme(channel):
    channels = load_channels()
    if 'channel_ids' in channels and channel.id in channels['channel_ids']:
        channels['channel_ids'].remove(channel.id)
        save_channels(channels)
        await channel.send("Auto meme disabled for this channel.")
    else:
        await channel.send("Schedule memes already disabled.")

@bot.command('meme')
async def meme(ctx):
    try:
        meme_url = await send_random_meme()
        await ctx.send(meme_url)
    except Exception as e:
        print(f"Error getting meme: {e}")
        await ctx.send("Error getting meme")

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(send_memes())  # Create a background task
    log_system_stats.start()  # Start the memory logging task
    if not send_memes.is_running():
        send_memes.start()  # Start the task only if it's not running


@tasks.loop(hours=1)
async def log_system_stats():
    try:
        memory_info = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_percentage = memory_info.percent

        message = f"Memory Usage: {memory_percentage}%\nCPU Usage: {cpu_usage}%"

        log_channel = client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(message)
        else:
            print(f"Log channel with ID {LOG_CHANNEL_ID} not found.")
    except Exception as e:
        print(f"Error logging system stats: {e}")


@tasks.loop(minutes=1)
async def send_memes():
    channels = load_channels()
    if channels and 'channel_ids' in channels:
        # Get a meme
        meme_url = await send_random_meme()
        if meme_url:
            # Send the meme to all channels
            for channel_id in channels['channel_ids']:
                channel = client.get_channel(channel_id)
                if channel:
                    await channel.send(meme_url)
                else:
                    print(f"Channel {channel_id} not found.")


@client.event
async def on_message(message):
    # Debug statement
    print(f"{message.author} sent ({message.guild}): {message.content}")
    if message.author == client.user or message.author.bot:
        return

    if message.content.startswith(PREFIX + "meme"):
        await meme(message.channel)

    elif message.content.startswith(PREFIX + 'schedule memes') and "Moderator" in [role.name for role in message.author.roles]:
        print("Inside schedule_meme command handler")  # Debug statement
        await enable_auto_meme(message.channel)

    elif message.content.startswith(PREFIX + 'unschedule memes') and "Moderator" in [role.name for role in message.author.roles]:
        print("Inside unschedule_memes command handler")  # Debug statement
        await disable_auto_meme(message.channel)

keep_alive()

client.run(TOKEN)