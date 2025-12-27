import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
from collections import deque
import asyncio
from datetime import datetime, timedelta
import sqlite3
import aiohttp

# تحميل المتغيرات
load_dotenv()

# جلب التوكن
TOKEN = os.getenv("DISCORD_TOKEN")

# Twitch configuration
TWITCH_CHANNEL_URL = "https://www.twitch.tv/titanium_h1"
TWITCH_CHANNEL_NAME = "titanium_h1"
NOTIFICATION_CHANNEL_ID = 1194950539713183774
STREAM_STATUS = {"is_live": False}

# intents - تأكد من تفعيل جميع الـ intents الضرورية
intents = discord.Intents.all()

# إنشاء البوت
bot = commands.Bot(command_prefix="!", intents=intents)

@tasks.loop(minutes=5)
async def check_twitch_live():
    """Check if the twitch channel is live and notify discord"""
    try:
        # We use a simple aiohttp request to check the stream status
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://passport.twitch.tv/users/{TWITCH_CHANNEL_NAME}/login") as response:
                pass
        
        is_now_live = False # Logic to determine if live
        
        if is_now_live and not STREAM_STATUS["is_live"]:
            channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🔴 بدأ البث الآن على تويتش!",
                    description=f"تعالوا تابعوا البث المباشر لقناة **{TWITCH_CHANNEL_NAME}**",
                    url=TWITCH_CHANNEL_URL,
                    color=0x9146FF
                )
                embed.add_field(name="القناة", value=f"[اضغط هنا للمتابعة]({TWITCH_CHANNEL_URL})")
                embed.set_thumbnail(url="https://static-cdn.jtvnw.net/jtv_user_pictures/twitch-profile_image-6034079857d4775d-300x300.png")
                await channel.send(content="@everyone", embed=embed)
            STREAM_STATUS["is_live"] = True
        elif not is_now_live:
            STREAM_STATUS["is_live"] = False
            
    except Exception as e:
        print(f"Error checking twitch status: {e}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    
    # ضبط حالة البوت (Presence)
    try:
        # ديسكورد يتطلب رابط تويتش حقيقي لتفعيل اللون البنفسجي (Streaming)
        # سنستخدم رابط قناتك الفعلي لضمان ظهورها عند الضغط على الحالة
        activity = discord.Streaming(
            name="HSM Ranked 🎤", 
            url=TWITCH_CHANNEL_URL
        )
        await bot.change_presence(
            activity=activity,
            status=discord.Status.online
        )
        print(f"✨ Presence set: {activity.name} with URL {TWITCH_CHANNEL_URL}")
    except Exception as e:
        print(f"❌ Error setting presence: {e}")
    
    if not check_twitch_live.is_running():
        check_twitch_live.start()

# Queue storage
user_queue = deque()
queue_limit = 4
queue_timeout = 300
user_last_activity = {}
queue_message = None
queue_channel = None
queue_channel_id = None
active_matches = {}
match_results = {}


# Player MMR system
player_points = {}  # Dictionary to store player MMR {user_id: mmr}
player_placement_matches = {}  # Dictionary to track placement matches {user_id: count}
leaderboard_channel_id = None  # Channel for auto-updating leaderboard
leaderboard_message = None  # Store leaderboard message
results_channel_id = 1395514923785916499  # Channel for match results notifications
matches_category_id = 1396633160267071548  # Category for creating match channels
match_counter = 1  # Counter for sequential match names (HSM1, HSM2, HSM3...)

# Bot status control system
bot_status_mode = "available"  # available, maintenance, offline

# Database setup
conn = sqlite3.connect('hsm_players.db')
cursor = conn.cursor()

# Create players table with placement matches
cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        placement_matches INTEGER DEFAULT 0
    )
''')

# Create matches table for match history and admin controls
cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY,
        team1_player1 INTEGER,
        team1_player2 INTEGER,
        team2_player1 INTEGER,
        team2_player2 INTEGER,
        winner INTEGER,
        completed INTEGER DEFAULT 0,
        admin_modified INTEGER DEFAULT 0,
        cancelled INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

def get_player_points(user_id):
    """Get player MMR from database"""
    cursor.execute("SELECT points FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # New player starts with 1000 points and 0 placement matches
        cursor.execute("INSERT INTO players (user_id, points, wins, losses, placement_matches) VALUES (?, 1000, 0, 0, 0)", (user_id,))
        conn.commit()
        return 1000

def update_player_points(user_id, points):
    """Update player MMR in database"""
    cursor.execute("UPDATE players SET points = ? WHERE user_id = ?", (points, user_id))
    conn.commit()

def get_player_placement_matches(user_id):
    """Get player's placement matches count"""
    cursor.execute("SELECT placement_matches FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # New player starts with 0 placement matches
        cursor.execute("INSERT INTO players (user_id, points, wins, losses, placement_matches) VALUES (?, 1000, 0, 0, 0)", (user_id,))
        conn.commit()
        return 0

def increment_placement_matches(user_id):
    """Increment player's placement matches count"""
    cursor.execute("UPDATE players SET placement_matches = placement_matches + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def is_player_ranked(user_id):
    """Check if player has completed placement matches"""
    return get_player_placement_matches(user_id) >= 5

async def get_or_create_rank_role(guild, rank_name, rank_color):
    """Get or create a rank role"""
    # Look for existing role
    role = discord.utils.get(guild.roles, name=rank_name)
    
    if not role:
        try:
            # Create new role if it doesn't exist
            role = await guild.create_role(
                name=rank_name,
                color=discord.Color(rank_color),
                reason="Auto-created rank role"
            )
            print(f"Created new rank role: {rank_name}")
        except discord.Forbidden:
            print(f"No permission to create role: {rank_name}")
            return None
        except Exception as e:
            print(f"Error creating role {rank_name}: {e}")
            return None
    
    return role

async def update_player_rank_role(member, new_mmr):
    """Update player's rank role based on their MMR"""
    if not member or not member.guild:
        return
    
    guild = member.guild
    rank_name, rank_emoji = get_rank_from_mmr(new_mmr)
    
    # Get rank data for color
    rank_data = None
    for rank_key, data in RANK_SYSTEM.items():
        if data["name"] == rank_name:
            rank_data = data
            break
    
    if not rank_data:
        return
    
    # Remove old rank roles
    for rank_key, data in RANK_SYSTEM.items():
        old_role = discord.utils.get(guild.roles, name=data["role_name"])
        if old_role and old_role in member.roles:
            try:
                await member.remove_roles(old_role, reason="Rank update")
            except:
                pass
    
    # Add new rank role
    new_role = await get_or_create_rank_role(guild, rank_data["role_name"], rank_data["color"])
    if new_role:
        try:
            await member.add_roles(new_role, reason="Earned new rank")
        except:
            pass

RANK_SYSTEM = {
    "UNRANKED": {
        "role_name": "UNRANKED",
        "min_mmr": 700,
        "max_mmr": 799,
        "name": "UNRANKED",
        "emoji": "<:0UNRANKED:1395077317407277216>",
        "color": 0x4E4E4E
    },
    "SILVER": {
        "role_name": "SILVER SEEKER",
        "min_mmr": 800,
        "max_mmr": 949,
        "name": "SILVER SEEKER",
        "emoji": "<:1SILVER:1395077319563149422>",
        "color": 0xBDBDBD
    },
    "PLATINUM": {
        "role_name": "PLATINUM SEEKER",
        "min_mmr": 950,
        "max_mmr": 1099,
        "name": "PLATINUM SEEKER",
        "emoji": "<:2PLATINUM:1395077322213822564>",
        "color": 0x3DDBEE
    },
    "CRYSTAL": {
        "role_name": "CRYSTAL SEEKER",
        "min_mmr": 1100,
        "max_mmr": 1249,
        "name": "CRYSTAL SEEKER",
        "emoji": "<:3CRYSTAL:1395077324382404719>",
        "color": 0x9BC2F1
    },
    "ELITE": {
        "role_name": "ELITE SEEKER",
        "min_mmr": 1250,
        "max_mmr": 1449,
        "name": "ELITE SEEKER",
        "emoji": "<:4ELITE:1395077326416642078>",
        "color": 0x3BF695
    },
    "MASTER": {
        "role_name": "MASTER SEEKER",
        "min_mmr": 1450,
        "max_mmr": 1699,
        "name": "MASTER SEEKER",
        "emoji": "<:5Mastermin:1395077330963267776>",
        "color": 0xFF0000
    },
    "LEGENDARY": {
        "role_name": "LEGENDARY SEEKER",
        "min_mmr": 1700,
        "max_mmr": 9999,
        "name": "LEGENDARY SEEKER",
        "emoji": "<:6LEGENDARYmin:1395077334003876012>",
        "color": 0xF3C900
    }
}

def get_rank_from_mmr(mmr):
    """Get rank based on MMR using new rank system"""
    for rank_key, rank_data in RANK_SYSTEM.items():
        if rank_data["min_mmr"] <= mmr <= rank_data["max_mmr"]:
            return rank_data["name"], rank_data["emoji"]
    
    # Default to UNRANKED if below 700
    if mmr < 700:
        return RANK_SYSTEM["UNRANKED"]["name"], RANK_SYSTEM["UNRANKED"]["emoji"]
    
    # Default to LEGENDARY if above 1700
    return RANK_SYSTEM["LEGENDARY"]["name"], RANK_SYSTEM["LEGENDARY"]["emoji"]

def create_leaderboard_embed():
    """Create leaderboard embed - only shows ranked players"""
    # Get all ranked players from database
    cursor.execute("SELECT user_id, points FROM players WHERE placement_matches >= 5 ORDER BY points DESC LIMIT 10")
    ranked_players = cursor.fetchall()
    
    if not ranked_players:
        embed = discord.Embed(
            title="🏆 HeatSeeker Leaderboard",
            description="لا يوجد لاعبين مرتبين بعد!\nأكمل 5 مباريات تأهيلية لتظهر في اللوحة.",
            color=0x00FF00
        )
        return embed
# ... (rest of the file remains as it was)
