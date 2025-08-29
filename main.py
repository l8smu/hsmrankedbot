import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
from collections import deque
import asyncio
from datetime import datetime, timedelta
import sqlite3
import threading
from flask import Flask

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Queue storage - using deque for efficient queue operations
user_queue = deque()
queue_limit = 4  # Maximum queue size (2v2)
queue_timeout = 300  # 5 minutes timeout
user_last_activity = {}  # Track user activity for timeout
queue_message = None  # Store the queue message to avoid duplicates
queue_channel = None  # Store the queue channel object
queue_channel_id = None  # Store the channel ID for queue
active_matches = {}  # Store active match information
match_results = {}  # Store match results to prevent duplicate reporting

# Player MMR system
player_points = {}  # Dictionary to store player MMR {user_id: mmr}
player_placement_matches = {
}  # Dictionary to track placement matches {user_id: count}
leaderboard_channel_id = None  # Channel for auto-updating leaderboard
leaderboard_message = None  # Store leaderboard message
results_channel_id = 1395514923785916499  # Channel for match results notifications
matches_category_id = 1396633160267071548  # Category for creating match channels
match_counter = 1  # Counter for sequential match names (HSM1, HSM2, HSM3...)

# Rank roles system
RANK_ROLES = {
    "SILVER SEEKER": {
        "id": 1135152624971300875,
        "min_mmr": 800,
        "max_mmr": 949,
        "emoji": "🥈"
    },
    "PLATINUM SEEKER": {
        "id": 1135152815392706631,
        "min_mmr": 950,
        "max_mmr": 1099,
        "emoji": "💎"
    },
    "CRYSTAL SEEKER": {
        "id": 1135152940160655521,
        "min_mmr": 1100,
        "max_mmr": 1249,
        "emoji": "💠"
    },
    "ELITE SEEKER": {
        "id": 1135153011224752209,
        "min_mmr": 1250,
        "max_mmr": 1449,
        "emoji": "⚡"
    },
    "MASTER SEEKER": {
        "id": 1135153217156677722,
        "min_mmr": 1450,
        "max_mmr": 1699,
        "emoji": "🔥"
    },
    "LEGENDARY SEEKER": {
        "id": 1135153132352061502,
        "min_mmr": 1700,
        "max_mmr": 9999,
        "emoji": "🏆"
    }
}

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

# Flask web server for health checks (required for Autoscale deployment)
app = Flask(__name__)


@app.route('/')
def health_check():
    """Health check endpoint for deployment health checks"""
    return {
        "status": "healthy",
        "service": "HeatSeeker Discord Bot",
        "bot_ready": bot.is_ready() if bot else False,
        "timestamp": datetime.now().isoformat()
    }, 200


@app.route('/health')
def health():
    """Alternative health check endpoint"""
    return health_check()


def run_flask():
    """Run Flask server in a separate thread"""
    port = int(os.environ.get('PORT', 8080))  # Use PORT env var for deployment
    app.run(host='0.0.0.0', port=port, debug=False)


def get_player_points(user_id):
    """Get player MMR from database"""
    cursor.execute("SELECT points FROM players WHERE user_id = ?", (user_id, ))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # New player starts with 1300 points and 0 placement matches
        cursor.execute(
            "INSERT INTO players (user_id, points, wins, losses, placement_matches) VALUES (?, 1300, 0, 0, 0)",
            (user_id, ))
        conn.commit()
        return 1300


def update_player_points(user_id, points):
    """Update player MMR in database"""
    cursor.execute("UPDATE players SET points = ? WHERE user_id = ?",
                   (points, user_id))
    conn.commit()


def get_player_placement_matches(user_id):
    """Get player's placement matches count"""
    cursor.execute("SELECT placement_matches FROM players WHERE user_id = ?",
                   (user_id, ))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # New player starts with 0 placement matches
        cursor.execute(
            "INSERT INTO players (user_id, points, wins, losses, placement_matches) VALUES (?, 1300, 0, 0, 0)",
            (user_id, ))
        conn.commit()
        return 0


def increment_placement_matches(user_id):
    """Increment player's placement matches count"""
    cursor.execute(
        "UPDATE players SET placement_matches = placement_matches + 1 WHERE user_id = ?",
        (user_id, ))
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
            role = await guild.create_role(name=rank_name,
                                           color=discord.Color(rank_color),
                                           reason="Auto-created rank role")
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
    
    # Check if player has completed placement matches
    placement_matches = get_player_placement_matches(member.id)
    if placement_matches < 5:
        print(f"Player {member.display_name} hasn't completed placement matches ({placement_matches}/5)")
        return

    # Get appropriate rank for MMR
    new_rank_data = None
    for rank_name, data in RANK_ROLES.items():
        if data["min_mmr"] <= new_mmr <= data["max_mmr"]:
            new_rank_data = data
            break

    if not new_rank_data:
        print(f"No rank found for MMR {new_mmr}")
        return

    # Remove all old rank roles
    for rank_name, data in RANK_ROLES.items():
        try:
            old_role = guild.get_role(data["id"])
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role, reason="Rank update")
                print(f"Removed role {rank_name} from {member.display_name}")
        except Exception as e:
            print(f"Error removing role {rank_name}: {e}")

    # Add new rank role
    try:
        new_role = guild.get_role(new_rank_data["id"])
        if new_role:
            await member.add_roles(new_role, reason="Earned new rank")
            print(f"Added role {list(RANK_ROLES.keys())[list(RANK_ROLES.values()).index(new_rank_data)]} to {member.display_name}")
        else:
            print(f"Role with ID {new_rank_data['id']} not found in guild")
    except Exception as e:
        print(f"Error adding new role: {e}")




def get_rank_from_mmr(mmr):
    """Get rank based on MMR using new rank system"""
    for rank_name, rank_data in RANK_ROLES.items():
        if rank_data["min_mmr"] <= mmr <= rank_data["max_mmr"]:
            return rank_name, rank_data["emoji"]

    # Default to UNRANKED if below 800
    if mmr < 800:
        return "UNRANKED", "🔹"

    # Default to LEGENDARY if above 1700
    return "LEGENDARY SEEKER", RANK_ROLES["LEGENDARY SEEKER"]["emoji"]


async def update_all_player_roles(guild):
    """Update all players' rank roles in the guild"""
    if not guild:
        return
    
    updated_count = 0
    cursor.execute("SELECT user_id, points, placement_matches FROM players WHERE placement_matches >= 5")
    ranked_players = cursor.fetchall()
    
    for user_id, points, placement_matches in ranked_players:
        member = guild.get_member(user_id)
        if member:
            try:
                await update_player_rank_role(member, points)
                updated_count += 1
            except Exception as e:
                print(f"Error updating role for {member.display_name}: {e}")
    
    print(f"Updated roles for {updated_count} ranked players")
    return updated_count


async def create_leaderboard_embed(page=1, players_per_page=10):
    """Create paginated leaderboard embed - only shows ranked players"""
    # Calculate offset for pagination
    offset = (page - 1) * players_per_page

    # Get total count of ranked players (temporarily show all players with games)
    cursor.execute(
        "SELECT COUNT(*) FROM players WHERE (wins > 0 OR losses > 0) OR placement_matches >= 1"
    )
    total_ranked = cursor.fetchone()[0]

    # Calculate total pages
    total_pages = max(1, (total_ranked + players_per_page - 1) //
                      players_per_page)

    # Ensure page is within valid range
    page = max(1, min(page, total_pages))

    # Get ranked players for current page (temporarily show all players with games)
    cursor.execute(
        """
        SELECT user_id, points, wins, losses 
        FROM players 
        WHERE (wins > 0 OR losses > 0) OR placement_matches >= 1
        ORDER BY points DESC 
        LIMIT ? OFFSET ?
    """, (players_per_page, offset))
    ranked_players = cursor.fetchall()
    print(f"🔍 Leaderboard debug: Found {len(ranked_players)} ranked players")

    if not ranked_players:
        embed = discord.Embed(
            title="🏆 HeatSeeker Leaderboard",
            description=
            "لا يوجد لاعبين بمباريات مكتملة بعد!\nالعب مباريات للظهور في لوحة المتصدرين.",
            color=0xFFD700)
        embed.add_field(
            name="📋 ابدأ اللعب",
            value=
            "• انضم للطابور باستخدام الأزرار أدناه\n• العب مباريات 2v2 مع لاعبين آخرين\n• التوزيع عادل ومتوازن حسب نقاط MMR\n• ستحصل على نقاط MMR حسب نتائج مبارياتك",
            inline=False)
        return embed, 1, 1

    embed = discord.Embed(
        title="🏆 HeatSeeker Leaderboard",
        description=
        f"أفضل لاعبي HeatSeeker المرتبين حسب MMR\n**الصفحة {page} من {total_pages}**",
        color=0xFFD700)

    leaderboard_text = ""
    for i, (user_id, mmr, wins, losses) in enumerate(ranked_players):
        rank_name, rank_emoji = get_rank_from_mmr(mmr)
        global_position = offset + i + 1
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0

        # Try to get user name
        user_name = f"Player {str(user_id)[-4:]}"  # Default fallback name
        try:
            user = bot.get_user(user_id)
            if user:
                user_name = user.display_name
            else:
                # Try to fetch from Discord if not in cache
                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        user_name = user.display_name
                except:
                    pass  # Keep the fallback name
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            pass  # Keep the fallback name

        # Always add the player to leaderboard
        leaderboard_text += f"**{global_position}.** {rank_emoji} **{user_name}**\n"
        leaderboard_text += f"`{mmr} MMR | Wins: {wins} | Lose: {losses} | Games: {total_games} | {win_rate:.0f}%`\n\n"

    if not leaderboard_text:
        leaderboard_text = "لا يوجد لاعبين مرتبين"

    embed.add_field(name=f"🏅 التصنيف العالمي (صفحة {page})",
                    value=leaderboard_text,
                    inline=False)

    # Get total players and placement players count
    cursor.execute("SELECT COUNT(*) FROM players")
    total_players = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM players WHERE (wins > 0 OR losses > 0) OR placement_matches >= 1"
    )
    ranked_count = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM players WHERE placement_matches < 5 AND placement_matches > 0"
    )
    placement_count = cursor.fetchone()[0]

    embed.add_field(
        name="📊 إحصائيات النظام",
        value=
        f"**لاعبين مرتبين:** {ranked_count}\n**في المباريات التأهيلية:** {placement_count}\n**إجمالي اللاعبين:** {total_players}",
        inline=False)

    embed.set_footer(
        text=f"صفحة {page}/{total_pages} • يتم التحديث كل 10 دقائق")
    embed.timestamp = datetime.now()

    return embed, page, total_pages


# Button View Classes
class QueueView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(label='Join Queue',
                       style=discord.ButtonStyle.success,
                       emoji='➕',
                       custom_id='join_queue')
    async def join_queue(self, interaction: discord.Interaction,
                         button: discord.ui.Button):
        user = interaction.user

        # Check if user is already in queue
        if user in user_queue:
            await interaction.response.send_message(
                f"❌ {user.display_name}, أنت موجود بالفعل في الطابور!",
                ephemeral=True)
            return

        # Check if user is in an active match
        for match_name, match_info in active_matches.items():
            if user in match_info['players']:
                await interaction.response.send_message(
                    f"❌ أنت حالياً في مباراة {match_name}! أنهِ المباراة أولاً.",
                    ephemeral=True)
                return

        # Check queue limit
        if len(user_queue) >= queue_limit:
            await interaction.response.send_message(
                f"❌ الطابور مكتمل! الحد الأقصى {queue_limit} مستخدم.",
                ephemeral=True)
            return

        # Add user to queue
        user_queue.append(user)
        user_last_activity[user.id] = datetime.now()

        # Save queue channel info globally
        global queue_channel_id, queue_channel
        queue_channel_id = interaction.channel.id
        queue_channel = interaction.channel

        await interaction.response.send_message(
            f"✅ تم انضمامك للطابور! موقعك: #{len(user_queue)}", ephemeral=True)

        # Update queue display first
        await update_queue_embed()

        # Check if queue is full and create match
        if len(user_queue) == queue_limit:
            await create_match(interaction.guild, list(user_queue))
            user_queue.clear()
            user_last_activity.clear()
            await update_queue_embed()  # Update again after clearing queue

    @discord.ui.button(label='Leave Queue',
                       style=discord.ButtonStyle.danger,
                       emoji='➖',
                       custom_id='leave_queue')
    async def leave_queue(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        user = interaction.user

        if user not in user_queue:
            await interaction.response.send_message(
                f"❌ {user.display_name}, أنت لست في الطابور!", ephemeral=True)
            return

        user_queue.remove(user)
        if user.id in user_last_activity:
            del user_last_activity[user.id]

        await interaction.response.send_message(f"✅ تم خروجك من الطابور!",
                                                ephemeral=True)
        await update_queue_embed()

    @discord.ui.button(label='Queue Status',
                       style=discord.ButtonStyle.primary,
                       emoji='📋',
                       custom_id='queue_status')
    async def queue_status(self, interaction: discord.Interaction,
                           button: discord.ui.Button):
        if not user_queue:
            await interaction.response.send_message("📋 الطابور فارغ حالياً!",
                                                    ephemeral=True)
            return

        # Show user's position if they're in queue
        user = interaction.user
        if user in user_queue:
            position = list(user_queue).index(user) + 1
            await interaction.response.send_message(
                f"📍 موقعك في الطابور: #{position}\nإجمالي المستخدمين: {len(user_queue)}",
                ephemeral=True)
        else:
            await interaction.response.send_message(
                f"📋 عدد المستخدمين في الطابور: {len(user_queue)}\nأنت لست في الطابور حالياً.",
                ephemeral=True)

    @discord.ui.button(label='Ping',
                       style=discord.ButtonStyle.secondary,
                       emoji='🔔',
                       custom_id='ping')
    async def ping(self, interaction: discord.Interaction,
                   button: discord.ui.Button):
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! زمن الاستجابة: {latency}ms", ephemeral=True)


# Reset Database View
class ResetDatabaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout
    
    @discord.ui.button(label='نعم، أعد تعيين قاعدة البيانات', style=discord.ButtonStyle.danger, emoji='⚠️')
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm database reset"""
        try:
            # Clear all tables
            cursor.execute("DELETE FROM players")
            cursor.execute("DELETE FROM matches")
            conn.commit()
            
            # Update player points dictionary
            global player_points, player_placement_matches
            player_points.clear()
            player_placement_matches.clear()
            
            # Clear active matches and results
            global active_matches, match_results
            active_matches.clear()
            match_results.clear()
            
            # Success embed
            embed = discord.Embed(
                title="✅ تم إعادة تعيين قاعدة البيانات بنجاح",
                description="تم حذف جميع البيانات وإعادة ضبط النظام",
                color=0x00FF00
            )
            
            embed.add_field(
                name="📊 الإعدادات الجديدة",
                value="• **النقاط الافتراضية:** 1300 MMR\n"
                      "• **المباريات التأهيلية:** 5 مباريات\n"
                      "• **عدد اللاعبين:** 0\n"
                      "• **تاريخ المباريات:** فارغ",
                inline=False
            )
            
            embed.add_field(
                name="🎮 ما يحدث الآن",
                value="• جميع اللاعبين الجدد سيبدؤون بـ 1300 نقطة\n"
                      "• لوحة المتصدرين ستكون فارغة حتى تكتمل مباريات جديدة\n"
                      "• يمكن البدء فوراً في لعب مباريات جديدة",
                inline=False
            )
            
            embed.set_footer(text=f"تم بواسطة {interaction.user.display_name}")
            embed.timestamp = datetime.now()
            
            await interaction.response.edit_message(embed=embed, view=None)
            print(f"Database reset by {interaction.user.display_name}")
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ فشل في إعادة تعيين قاعدة البيانات",
                description=f"حدث خطأ: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.edit_message(embed=error_embed, view=None)
            print(f"Database reset failed: {e}")
    
    @discord.ui.button(label='إلغاء', style=discord.ButtonStyle.secondary, emoji='❌')
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel database reset"""
        embed = discord.Embed(
            title="✅ تم إلغاء إعادة التعيين",
            description="لم يتم تغيير أي شيء في قاعدة البيانات.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Reset Placements View
class ResetPlacementsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout
    
    @discord.ui.button(label='نعم، أعد تعيين المباريات التأهيلية', style=discord.ButtonStyle.primary, emoji='🔄')
    async def confirm_reset_placements(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm placement matches reset"""
        try:
            # Reset all players' placement matches to 0
            cursor.execute("UPDATE players SET placement_matches = 0")
            conn.commit()
            
            # Clear placement matches dictionary
            global player_placement_matches
            player_placement_matches.clear()
            
            # Get count of affected players
            cursor.execute("SELECT COUNT(*) FROM players")
            player_count = cursor.fetchone()[0]
            
            # Success embed
            embed = discord.Embed(
                title="✅ تم إعادة تعيين المباريات التأهيلية بنجاح",
                description="تم إعادة ضبط المباريات التأهيلية لجميع اللاعبين",
                color=0x00FF00
            )
            
            embed.add_field(
                name="📊 النتائج",
                value=f"• **عدد اللاعبين المتأثرين:** {player_count}\n"
                      "• **المباريات التأهيلية:** 0/5 للجميع\n"
                      "• **النقاط والإحصائيات:** لم تتغير\n"
                      "• **الحالة:** جميع اللاعبين في المباريات التأهيلية",
                inline=False
            )
            
            embed.add_field(
                name="🎮 ما يحدث الآن",
                value="• جميع اللاعبين يحتاجون 5 مباريات للحصول على رانك\n"
                      "• لوحة المتصدرين ستكون فارغة حتى إكمال المباريات التأهيلية\n"
                      "• يمكن البدء فوراً في لعب مباريات تأهيلية جديدة",
                inline=False
            )
            
            embed.set_footer(text=f"تم بواسطة {interaction.user.display_name}")
            embed.timestamp = datetime.now()
            
            await interaction.response.edit_message(embed=embed, view=None)
            print(f"Placement matches reset by {interaction.user.display_name} - {player_count} players affected")
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ فشل في إعادة تعيين المباريات التأهيلية",
                description=f"حدث خطأ: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.edit_message(embed=error_embed, view=None)
            print(f"Placement matches reset failed: {e}")
    
    @discord.ui.button(label='إلغاء', style=discord.ButtonStyle.secondary, emoji='❌')
    async def cancel_reset_placements(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel placement matches reset"""
        embed = discord.Embed(
            title="✅ تم إلغاء إعادة التعيين",
            description="لم يتم تغيير المباريات التأهيلية لأي لاعب.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Admin View for moderators
class AdminView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Next User',
                       style=discord.ButtonStyle.success,
                       emoji='⏭️',
                       custom_id='next_user')
    async def next_user(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        # Check permissions
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ هذا الأمر يعمل في السيرفر فقط!", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
            return

        if not user_queue:
            await interaction.response.send_message("❌ الطابور فارغ!",
                                                    ephemeral=True)
            return

        next_user_obj = user_queue.popleft()
        if next_user_obj.id in user_last_activity:
            del user_last_activity[next_user_obj.id]

        await interaction.response.send_message(
            f"🎯 تم استدعاء {next_user_obj.display_name} من الطابور!")

        # Try to DM the user
        try:
            guild_name = interaction.guild.name if interaction.guild else "السيرفر"
            await next_user_obj.send(
                f"🎯 تم استدعاؤك من الطابور في {guild_name}!")
        except:
            pass

        await update_queue_embed(interaction.message)

    @discord.ui.button(label='Clear Queue',
                       style=discord.ButtonStyle.danger,
                       emoji='🗑️',
                       custom_id='clear_queue')
    async def clear_queue(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        # Check permissions
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ هذا الأمر يعمل في السيرفر فقط!", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
            return

        if not user_queue:
            await interaction.response.send_message("❌ الطابور فارغ بالفعل!",
                                                    ephemeral=True)
            return

        queue_size = len(user_queue)
        user_queue.clear()
        user_last_activity.clear()

        await interaction.response.send_message(
            f"🗑️ تم مسح الطابور! تمت إزالة {queue_size} مستخدم.")
        await update_queue_embed()


# Result Menu Select View
class ResultSelect(discord.ui.Select):

    def __init__(self, match_name: str):
        self.match_name = match_name

        options = [
            discord.SelectOption(label="🔵 Team 1 (Blue) Win",
                                 description="الفريق الأزرق فائز",
                                 value="team1",
                                 emoji="🔵"),
            discord.SelectOption(label="🟠 Team 2 (Orange) Win",
                                 description="الفريق البرتقالي فائز",
                                 value="team2",
                                 emoji="🟠")
        ]

        super().__init__(placeholder="اختر الفريق الفائز...",
                         options=options,
                         min_values=1,
                         max_values=1)

    async def callback(self, interaction: discord.Interaction):
        winner = 1 if self.values[0] == "team1" else 2
        result_text = "Team 1 (Blue)" if winner == 1 else "Team 2 (Orange)"

        # Acknowledge the interaction first
        await interaction.response.send_message(
            f"✅ تم تسجيل النتيجة: **{result_text}** فائز!\nجاري معالجة النتائج...",
            ephemeral=True)

        # Process the result
        await process_match_result(interaction, self.match_name, winner,
                                   result_text)


class ResultMenuView(discord.ui.View):

    def __init__(self, match_name: str):
        super().__init__(timeout=60)  # 1 minute timeout
        self.match_name = match_name
        self.add_item(ResultSelect(match_name))


# Leaderboard Pagination View
class LeaderboardView(discord.ui.View):

    def __init__(self, current_page=1, total_pages=1):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.current_page = current_page
        self.total_pages = total_pages

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Clear existing items
        self.clear_items()

        # First page button
        first_button = discord.ui.Button(label="<<",
                                         style=discord.ButtonStyle.primary,
                                         disabled=(self.current_page == 1),
                                         custom_id="leaderboard_first")
        first_button.callback = self.first_page
        self.add_item(first_button)

        # Previous page button
        prev_button = discord.ui.Button(label="السابق",
                                        style=discord.ButtonStyle.secondary,
                                        disabled=(self.current_page == 1),
                                        emoji="⬅️",
                                        custom_id="leaderboard_prev")
        prev_button.callback = self.previous_page
        self.add_item(prev_button)

        # Current page indicator
        page_button = discord.ui.Button(
            label=f"{self.current_page}/{self.total_pages}",
            style=discord.ButtonStyle.gray,
            disabled=True,
            custom_id="leaderboard_current")
        self.add_item(page_button)

        # Next page button
        next_button = discord.ui.Button(
            label="التالي",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_page == self.total_pages),
            emoji="➡️",
            custom_id="leaderboard_next")
        next_button.callback = self.next_page
        self.add_item(next_button)

        # Last page button
        last_button = discord.ui.Button(
            label=">>",
            style=discord.ButtonStyle.primary,
            disabled=(self.current_page == self.total_pages),
            custom_id="leaderboard_last")
        last_button.callback = self.last_page
        self.add_item(last_button)

        # Refresh button
        refresh_button = discord.ui.Button(label="تحديث",
                                           style=discord.ButtonStyle.success,
                                           emoji="🔄",
                                           custom_id="leaderboard_refresh")
        refresh_button.callback = self.refresh_leaderboard
        self.add_item(refresh_button)

    async def first_page(self, interaction: discord.Interaction):
        """Go to first page"""
        self.current_page = 1
        await self.update_leaderboard(interaction)

    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
        await self.update_leaderboard(interaction)

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
        await self.update_leaderboard(interaction)

    async def last_page(self, interaction: discord.Interaction):
        """Go to last page"""
        self.current_page = self.total_pages
        await self.update_leaderboard(interaction)

    async def refresh_leaderboard(self, interaction: discord.Interaction):
        """Refresh current page"""
        await self.update_leaderboard(interaction)

    async def update_leaderboard(self, interaction: discord.Interaction):
        """Update leaderboard embed and buttons"""
        try:
            embed, current_page, total_pages = await create_leaderboard_embed(
                self.current_page)
            self.current_page = current_page
            self.total_pages = total_pages
            self.update_buttons()

            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            print(f"Error updating leaderboard: {e}")
            await interaction.response.send_message(
                "❌ حدث خطأ في تحديث اللوحة!", ephemeral=True)


# Admin Result View Classes
class AdminMatchSelect(discord.ui.Select):

    def __init__(self, options):
        super().__init__(placeholder="اختر المباراة لتعديل نتيجتها...",
                         options=options,
                         min_values=1,
                         max_values=1)

    async def callback(self, interaction: discord.Interaction):
        match_id = int(self.values[0])

        # Get match details from database
        cursor.execute(
            """
            SELECT match_id, team1_player1, team1_player2, team2_player1, team2_player2, 
                   winner, created_at 
            FROM matches 
            WHERE match_id = ? AND completed = 1
        """, (match_id, ))
        match_data = cursor.fetchone()

        if not match_data:
            await interaction.response.send_message("❌ المباراة غير موجودة!",
                                                    ephemeral=True)
            return

        # Show result modification options
        view = AdminResultActionView(match_id, match_data)
        embed = discord.Embed(title=f"🛠️ تعديل نتيجة HSM{match_id}",
                              description="اختر النتيجة الجديدة للمباراة:",
                              color=0xFF6B00)

        # Get player names for display
        try:
            p1 = bot.get_user(match_data[1])
            p2 = bot.get_user(match_data[2])
            p3 = bot.get_user(match_data[3])
            p4 = bot.get_user(match_data[4])

            if p1 and p2 and p3 and p4:
                current_winner = "Team 1" if match_data[
                    5] == 1 else "Team 2" if match_data[5] == 2 else "ملغية"

                embed.add_field(name="🔵 Team 1 (Blue)",
                                value=f"{p1.display_name}\n{p2.display_name}",
                                inline=True)

                embed.add_field(name="🟠 Team 2 (Orange)",
                                value=f"{p3.display_name}\n{p4.display_name}",
                                inline=True)

                embed.add_field(name="📊 النتيجة الحالية",
                                value=f"**الفائز الحالي:** {current_winner}",
                                inline=False)

        except:
            pass

        embed.add_field(
            name="⚠️ تحذير",
            value="تعديل النتيجة سيؤثر على MMR والرانك للاعبين المشاركين",
            inline=False)

        await interaction.response.edit_message(embed=embed, view=view)


class AdminResultActionView(discord.ui.View):

    def __init__(self, match_id: int, match_data):
        super().__init__(timeout=300)  # 5 minute timeout
        self.match_id = match_id
        self.match_data = match_data

    @discord.ui.button(label='Team 1 يفوز',
                       style=discord.ButtonStyle.primary,
                       emoji='🔵')
    async def team1_wins(self, interaction: discord.Interaction,
                         button: discord.ui.Button):
        await self.modify_result(interaction, 1, "Team 1 (Blue)")

    @discord.ui.button(label='Team 2 يفوز',
                       style=discord.ButtonStyle.primary,
                       emoji='🟠')
    async def team2_wins(self, interaction: discord.Interaction,
                         button: discord.ui.Button):
        await self.modify_result(interaction, 2, "Team 2 (Orange)")

    @discord.ui.button(label='إلغاء المباراة',
                       style=discord.ButtonStyle.danger,
                       emoji='❌')
    async def cancel_match(self, interaction: discord.Interaction,
                           button: discord.ui.Button):
        await self.modify_result(interaction, -1, "ملغية")

    async def modify_result(self, interaction: discord.Interaction,
                            new_winner: int, result_text: str):
        """Modify match result and update player stats"""
        old_winner = self.match_data[5]

        if old_winner == new_winner:
            await interaction.response.send_message(
                f"❌ النتيجة لم تتغير! الفائز الحالي هو {result_text}",
                ephemeral=True)
            return

        # Get all players
        team1_players = [self.match_data[1], self.match_data[2]]
        team2_players = [self.match_data[3], self.match_data[4]]
        all_players = team1_players + team2_players

        # Revert old result first
        if old_winner != -1:  # If match wasn't cancelled
            old_winners = team1_players if old_winner == 1 else team2_players
            old_losers = team2_players if old_winner == 1 else team1_players

            for player_id in old_winners:
                # Revert winner stats
                cursor.execute(
                    "SELECT points, wins FROM players WHERE user_id = ?",
                    (player_id, ))
                result = cursor.fetchone()
                if result:
                    old_points, wins = result
                    new_points = max(0, old_points - 25)  # Remove win points
                    new_wins = max(0, wins - 1)  # Remove win
                    cursor.execute(
                        "UPDATE players SET points = ?, wins = ? WHERE user_id = ?",
                        (new_points, new_wins, player_id))

            for player_id in old_losers:
                # Revert loser stats
                cursor.execute(
                    "SELECT points, losses FROM players WHERE user_id = ?",
                    (player_id, ))
                result = cursor.fetchone()
                if result:
                    old_points, losses = result
                    new_points = old_points + 20  # Add back lost points
                    new_losses = max(0, losses - 1)  # Remove loss
                    cursor.execute(
                        "UPDATE players SET points = ?, losses = ? WHERE user_id = ?",
                        (new_points, new_losses, player_id))

        # Apply new result
        if new_winner != -1:  # If match is not being cancelled
            new_winners = team1_players if new_winner == 1 else team2_players
            new_losers = team2_players if new_winner == 1 else team1_players

            for player_id in new_winners:
                # Apply winner stats
                cursor.execute(
                    "SELECT points, wins FROM players WHERE user_id = ?",
                    (player_id, ))
                result = cursor.fetchone()
                if result:
                    old_points, wins = result
                    new_points = old_points + 25  # Add win points
                    new_wins = wins + 1  # Add win
                    cursor.execute(
                        "UPDATE players SET points = ?, wins = ? WHERE user_id = ?",
                        (new_points, new_wins, player_id))

            for player_id in new_losers:
                # Apply loser stats
                cursor.execute(
                    "SELECT points, losses FROM players WHERE user_id = ?",
                    (player_id, ))
                result = cursor.fetchone()
                if result:
                    old_points, losses = result
                    new_points = max(0, old_points - 20)  # Remove points
                    new_losses = losses + 1  # Add loss
                    cursor.execute(
                        "UPDATE players SET points = ?, losses = ? WHERE user_id = ?",
                        (new_points, new_losses, player_id))

        # Update match in database
        cursor.execute(
            """
            UPDATE matches 
            SET winner = ?, admin_modified = 1, cancelled = ?
            WHERE match_id = ?
        """, (new_winner, 1 if new_winner == -1 else 0, self.match_id))

        conn.commit()

        # Update player roles for all affected players
        for player_id in all_players:
            try:
                guild = interaction.guild
                if guild:
                    member = guild.get_member(player_id)
                    if member:
                        points = get_player_points(player_id)
                        await update_player_rank_role(member, points)
            except Exception as e:
                print(f"Error updating player role: {e}")
                pass

        # Create success embed
        embed = discord.Embed(
            title="✅ تم تعديل النتيجة بنجاح",
            description=
            f"**HSM{self.match_id}** - النتيجة الجديدة: **{result_text}**",
            color=0x00FF00)

        embed.add_field(
            name="📊 التغييرات المطبقة",
            value=
            "• تم تحديث MMR للاعبين\n• تم تحديث الانتصارات والهزائم\n• تم تحديث الرانكات والأدوار",
            inline=False)

        embed.add_field(name="👤 تم التعديل بواسطة",
                        value=interaction.user.display_name,
                        inline=False)

        embed.set_footer(text="تم حفظ التعديل في قاعدة البيانات")
        embed.timestamp = datetime.now()

        await interaction.response.edit_message(embed=embed, view=None)

        # Send admin modification notification to results channel
        try:
            results_channel = bot.get_channel(results_channel_id)
            if results_channel and isinstance(
                    results_channel, discord.TextChannel
            ) and new_winner != -1:  # Don't send for cancelled matches
                # Get player info for notification
                team1_players = [self.match_data[1], self.match_data[2]]
                team2_players = [self.match_data[3], self.match_data[4]]

                admin_embed = discord.Embed(
                    title=f"🛠️ Admin Modified: HSM{self.match_id}",
                    description=f"**New Result:** {result_text}",
                    color=0xFF6B00)

                # Show teams
                try:
                    p1 = bot.get_user(team1_players[0])
                    p2 = bot.get_user(team1_players[1])
                    p3 = bot.get_user(team2_players[0])
                    p4 = bot.get_user(team2_players[1])

                    if p1 and p2 and p3 and p4:
                        team1_text = f"🔵 {p1.display_name}\n🔵 {p2.display_name}"
                        team2_text = f"🟠 {p3.display_name}\n🟠 {p4.display_name}"

                        admin_embed.add_field(name="Team 1 (Blue)",
                                              value=team1_text,
                                              inline=True)
                        admin_embed.add_field(name="Team 2 (Orange)",
                                              value=team2_text,
                                              inline=True)
                except:
                    pass

                admin_embed.add_field(
                    name="⚠️ Admin Action",
                    value=
                    f"Match result modified by {interaction.user.display_name}\nAll player stats have been updated accordingly",
                    inline=False)

                admin_embed.set_footer(
                    text=f"Match ID: {self.match_id} • Admin Modified")
                admin_embed.timestamp = datetime.now()

                await results_channel.send(embed=admin_embed)
            elif results_channel and isinstance(
                    results_channel, discord.TextChannel
            ) and new_winner == -1:  # Cancelled match
                cancel_embed = discord.Embed(
                    title=f"❌ Match Cancelled: HSM{self.match_id}",
                    description="Match has been cancelled by admin",
                    color=0xFF0000)

                cancel_embed.add_field(
                    name="🛠️ Admin Action",
                    value=
                    f"Match cancelled by {interaction.user.display_name}\nAll stats have been reverted",
                    inline=False)

                cancel_embed.set_footer(
                    text=f"Match ID: {self.match_id} • Cancelled")
                cancel_embed.timestamp = datetime.now()

                await results_channel.send(embed=cancel_embed)

        except Exception as e:
            print(f"Error sending admin notification: {e}")


class AdminResultView(discord.ui.View):

    def __init__(self, options):
        super().__init__(timeout=300)  # 5 minute timeout
        self.add_item(AdminMatchSelect(options))


async def update_queue_embed(interaction_message=None):
    """Update the queue embed with current information"""
    global queue_message, queue_channel
    embed = create_queue_embed()
    view = QueueView()

    try:
        if queue_message and queue_channel:
            # Always update the main queue message
            await queue_message.edit(embed=embed, view=view)
        elif queue_channel and isinstance(queue_channel, discord.TextChannel):
            # If no queue message exists, find and update it
            async for message in queue_channel.history(limit=20):
                if message.author == bot.user and message.embeds and len(
                        message.embeds) > 0:
                    if hasattr(message.embeds[0], 'title') and message.embeds[
                            0].title and "HeatSeeker Queue" in message.embeds[
                                0].title:
                        queue_message = message
                        await message.edit(embed=embed, view=view)
                        break
    except Exception as e:
        print(f"Error updating queue embed: {e}")
        # Try to send a new message if editing fails
        if queue_channel and isinstance(queue_channel, discord.TextChannel):
            try:
                queue_message = await queue_channel.send(embed=embed,
                                                         view=view)
            except Exception as send_error:
                print(f"Error sending queue message: {send_error}")


def create_queue_embed():
    """Create the main queue embed"""
    embed = discord.Embed(title="🔥 HeatSeeker Queue (2v2)", color=0x2F3136)

    if not user_queue:
        embed.add_field(
            name="لا يوجد لاعبون في الطابور",
            value=
            "انقر على ➕ **Join Queue** للبدء!\n**نحتاج 4 لاعبين لبدء المباراة**",
            inline=False)
        embed.add_field(name="🕐 Queue Timeout",
                        value="5 دقائق من عدم النشاط",
                        inline=False)
    else:
        # Show all users in queue with MMR/placement status
        queue_text = ""
        for i, user in enumerate(list(user_queue)):
            points = get_player_points(user.id)
            placement_matches = get_player_placement_matches(user.id)

            if placement_matches < 5:
                # Show placement matches progress
                queue_text += f"**{i+1}.** 📋 {user.display_name} `(Placement {placement_matches}/5)`\n"
            else:
                # Show rank for completed players
                rank_name, rank_emoji = get_rank_from_mmr(points)
                queue_text += f"**{i+1}.** {rank_emoji} {user.display_name} `({points} mmr - {rank_name})`\n"

        embed.add_field(name=f"👥 اللاعبون في الطابور ({len(user_queue)}/4)",
                        value=queue_text,
                        inline=False)

        if len(user_queue) == 4:
            embed.add_field(
                name="🎮 الطابور مكتمل!",
                value=
                "جاري إنشاء المباراة...\n⚖️ سيتم التوزيع العادل والمتوازن للفرق",
                inline=False)
        else:
            embed.add_field(
                name="⏳ في انتظار المزيد",
                value=
                f"نحتاج {4 - len(user_queue)} لاعبين إضافيين\n⚖️ سيتم التوزيع العادل حسب نقاط MMR",
                inline=False)

        embed.add_field(name="🕐 Queue Timeout",
                        value="5 دقائق من عدم النشاط",
                        inline=False)

    return embed


async def create_match(guild, players):
    """Create match channels and organize teams with balanced MMR distribution"""
    global match_counter

    # Create match name
    match_name = f"HSM{match_counter}"
    match_counter += 1

    # Get player MMR for balanced team distribution
    player_mmr = []
    for player in players:
        mmr = get_player_points(player.id)
        player_mmr.append((player, mmr))

    # Sort players by MMR (highest to lowest)
    player_mmr.sort(key=lambda x: x[1], reverse=True)

    # Balanced team distribution:
    # Team 1: Highest MMR + Lowest MMR
    # Team 2: 2nd Highest MMR + 2nd Lowest MMR
    team1 = [player_mmr[0][0], player_mmr[3][0]]  # Highest + Lowest
    team2 = [player_mmr[1][0], player_mmr[2][0]]  # 2nd Highest + 2nd Lowest

    # Calculate team MMR averages for display
    team1_avg = (player_mmr[0][1] + player_mmr[3][1]) // 2
    team2_avg = (player_mmr[1][1] + player_mmr[2][1]) // 2

    # Get the specified category for matches
    category = bot.get_channel(matches_category_id)
    if not category:
        # Fallback: create category if not found
        category = await guild.create_category(
            name=f"🏆 Matches",
            overwrites={
                guild.default_role:
                discord.PermissionOverwrite(read_messages=False,
                                            view_channel=False),
                guild.me:
                discord.PermissionOverwrite(read_messages=True,
                                            manage_channels=True)
            })

    # Set permissions for match participants
    overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(read_messages=False, view_channel=False),
        guild.me:
        discord.PermissionOverwrite(read_messages=True, manage_channels=True)
    }

    for player in players:
        overwrites[player] = discord.PermissionOverwrite(read_messages=True,
                                                         send_messages=True,
                                                         connect=True,
                                                         speak=True,
                                                         view_channel=True)

    # Create text channel for match
    text_channel = await guild.create_text_channel(
        name=f"📱-{match_name.lower()}",
        category=category,
        overwrites=overwrites)

    # Create Team 1 voice channel with 2 player limit
    team1_overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(connect=False, view_channel=False),
        guild.me:
        discord.PermissionOverwrite(connect=True,
                                    manage_channels=True,
                                    view_channel=True)
    }
    for player in team1:
        team1_overwrites[player] = discord.PermissionOverwrite(
            connect=True, speak=True, view_channel=True)

    team1_voice = await guild.create_voice_channel(name=f"🔵 Team 1 Voice",
                                                   category=category,
                                                   overwrites=team1_overwrites,
                                                   user_limit=2)

    # Create Team 2 voice channel with 2 player limit
    team2_overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(connect=False, view_channel=False),
        guild.me:
        discord.PermissionOverwrite(connect=True,
                                    manage_channels=True,
                                    view_channel=True)
    }
    for player in team2:
        team2_overwrites[player] = discord.PermissionOverwrite(
            connect=True, speak=True, view_channel=True)

    team2_voice = await guild.create_voice_channel(name=f"🟠 Team 2 Voice",
                                                   category=category,
                                                   overwrites=team2_overwrites,
                                                   user_limit=2)

    # Store match in database
    cursor.execute(
        """
        INSERT INTO matches (match_id, team1_player1, team1_player2, team2_player1, team2_player2, winner, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (match_counter - 1, team1[0].id, team1[1].id, team2[0].id,
          team2[1].id, 0, 0))
    conn.commit()

    # Store match info
    active_matches[match_name] = {
        'players': players,
        'team1': team1,
        'team2': team2,
        'text_channel': text_channel,
        'team1_voice': team1_voice,
        'team2_voice': team2_voice,
        'category': category,
        'match_id': match_counter - 1
    }

    # Send match information
    embed = discord.Embed(title=f"🎮 {match_name} - 2v2 Match",
                          description="**معلومات المباراة**",
                          color=0x00FF00)

    embed.add_field(
        name="📊 تفاصيل المباراة",
        value=
        f"**Name:** {match_name}\n**Server:** ME Only\n**Mode:** 2v2\n🔵 Team 1 Voice: {team1_voice.mention}\n🟠 Team 2 Voice: {team2_voice.mention}\n\n⚖️ **توزيع متوازن:** Team 1 Avg: `{team1_avg} MMR` | Team 2 Avg: `{team2_avg} MMR`",
        inline=False)

    # Team 1 (Blue)
    team1_text = ""
    for player in team1:
        points = get_player_points(player.id)
        rank_name, rank_emoji = get_rank_from_mmr(points)
        team1_text += f"🔵 {rank_emoji} {player.display_name} `({points} mmr - {rank_name})`\n"

    embed.add_field(name="🔵 Team 1 (Blue)", value=team1_text, inline=True)

    # Team 2 (Orange)
    team2_text = ""
    for player in team2:
        points = get_player_points(player.id)
        rank_name, rank_emoji = get_rank_from_mmr(points)
        team2_text += f"🟠 {rank_emoji} {player.display_name} `({points} mmr - {rank_name})`\n"

    embed.add_field(name="🟠 Team 2 (Orange)", value=team2_text, inline=True)

    embed.add_field(
        name="📝 تقرير النتيجة",
        value="**كوماند تسجيل النتيجة:**\n"
        "`/report` - يفتح قائمة تفاعلية لاختيار الفريق الفائز\n\n"
        "⚠️ **ملاحظة مهمة:** أول لاعب يكتب `/report` يحصل على القائمة!",
        inline=False)

    embed.add_field(name="⚖️ نظام التوزيع العادل",
                    value="• تم توزيع الفرق بناءً على نقاط MMR\n"
                    "• أعلى لاعب + أقل لاعب في فريق واحد\n"
                    "• ثاني أعلى + ثاني أقل في الفريق الآخر\n"
                    "• هذا يضمن مباريات متوازنة ومثيرة!",
                    inline=False)

    await text_channel.send(embed=embed)

    # Delete the queue message when queue is full
    try:
        if queue_message and hasattr(queue_message, 'delete'):
            await queue_message.delete()
            print(f"✅ Queue message deleted from channel")
        else:
            print(f"❌ Could not delete queue message - message not found")

    except Exception as e:
        print(f"❌ Error deleting queue message: {e}")

    # Send notifications to players
    for player in players:
        try:
            # Determine which team the player is in
            team_info = ""
            if player in team1:
                teammate = team1[1] if team1[0] == player else team1[0]
                team_info = f"🔵 **فريقك (Team 1):** أنت و {teammate.display_name}\n📊 **متوسط فريقك:** {team1_avg} MMR"
            else:
                teammate = team2[1] if team2[0] == player else team2[0]
                team_info = f"🟠 **فريقك (Team 2):** أنت و {teammate.display_name}\n📊 **متوسط فريقك:** {team2_avg} MMR"

            await player.send(f"🎮 **تم إنشاء مباراة {match_name}!**\n\n"
                              f"{team_info}\n\n"
                              f"📱 **توجه إلى:** {text_channel.mention}\n"
                              f"⚖️ **التوزيع:** متوازن حسب نقاط MMR\n"
                              f"🏆 **حظ سعيد!**")
        except:
            pass


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to manage queues!')

    # Set bot status
    try:
        await bot.change_presence(status=discord.Status.online,
                                  activity=discord.Activity(
                                      type=discord.ActivityType.playing,
                                      name="Created By Fahad <3"))
        print("Bot status set successfully")
    except Exception as e:
        print(f"Failed to set bot status: {e}")

    # Add persistent views
    bot.add_view(QueueView())
    bot.add_view(AdminView())

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    # Update all player roles on startup
    try:
        for guild in bot.guilds:
            updated_count = await update_all_player_roles(guild)
            print(f"Updated {updated_count} player roles in guild: {guild.name}")
    except Exception as e:
        print(f"Failed to update player roles on startup: {e}")

    # Start timeout checker and leaderboard updater
    check_timeouts.start()
    update_leaderboard.start()


# Timeout checker task
@tasks.loop(minutes=1)
async def check_timeouts():
    """Check for inactive users and remove them from queue"""
    current_time = datetime.now()
    users_to_remove = []

    for user in list(user_queue):
        if user.id in user_last_activity:
            time_diff = (current_time -
                         user_last_activity[user.id]).total_seconds()
            if time_diff > queue_timeout:  # 5 minutes
                users_to_remove.append(user)

    for user in users_to_remove:
        user_queue.remove(user)
        if user.id in user_last_activity:
            del user_last_activity[user.id]
        print(f"Removed {user.display_name} from queue due to timeout")


@check_timeouts.before_loop
async def before_check_timeouts():
    await bot.wait_until_ready()


# Leaderboard auto-update task
@tasks.loop(minutes=10)
async def update_leaderboard():
    """Update leaderboard every 10 minutes with pagination support"""
    global leaderboard_message, leaderboard_channel_id

    if leaderboard_channel_id and leaderboard_message:
        try:
            # Update embed for current page (default to page 1)
            embed, current_page, total_pages = await create_leaderboard_embed(page=1)
            view = LeaderboardView(current_page, total_pages)

            await leaderboard_message.edit(embed=embed, view=view)
            print("Paginated leaderboard updated automatically")
        except Exception as e:
            print(f"Failed to update leaderboard: {e}")
            # Try to send new message if edit fails
            try:
                channel = bot.get_channel(leaderboard_channel_id)
                if channel and hasattr(channel, 'send'):
                    embed, current_page, total_pages = await create_leaderboard_embed(
                        page=1)
                    view = LeaderboardView(current_page, total_pages)
                    leaderboard_message = await channel.send(embed=embed,
                                                             view=view)
                    print("Created new paginated leaderboard message")
            except Exception as e2:
                print(f"Failed to create new leaderboard message: {e2}")
                pass


@update_leaderboard.before_loop
async def before_update_leaderboard():
    await bot.wait_until_ready()


# Slash Commands
@bot.tree.command(name="setup", description="إعداد واجهة الطابور التفاعلية")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def setup_queue(interaction: discord.Interaction):
    """Setup the queue embed with buttons"""
    global queue_message, queue_channel, queue_channel_id

    # Delete existing queue message if it exists in this channel
    if queue_message and queue_channel_id == interaction.channel.id:
        try:
            await queue_message.delete()
        except:
            pass

    # Clear any existing queue messages in this channel
    if hasattr(interaction.channel, 'history'):
        async for message in interaction.channel.history(limit=20):
            if (message.author == bot.user and message.embeds
                    and len(message.embeds) > 0
                    and "HeatSeeker Queue" in str(message.embeds[0].title)):
                try:
                    await message.delete()
                except:
                    pass

    embed = create_queue_embed()
    view = QueueView()

    if not interaction.channel:
        await interaction.response.send_message("❌ لا يمكن تحديد القناة!",
                                                ephemeral=True)
        return

    await interaction.response.send_message("✅ تم إعداد الطابور بنجاح!",
                                            ephemeral=True)
    queue_message = await interaction.followup.send(embed=embed,
                                                    view=view,
                                                    wait=True)
    queue_channel = interaction.channel
    queue_channel_id = interaction.channel.id


@bot.tree.command(name="admin", description="لوحة تحكم إدارة الطابور")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def admin_panel(interaction: discord.Interaction):
    """Show admin panel for queue management"""
    embed = discord.Embed(title="🛠️ لوحة تحكم الطابور",
                          description="أوامر إدارة الطابور للمشرفين",
                          color=0xFF0000)

    embed.add_field(
        name="📊 الإحصائيات الحالية",
        value=
        f"عدد المستخدمين: {len(user_queue)}/{queue_limit}\nنشط منذ: {len(user_last_activity)} مستخدم",
        inline=False)

    view = AdminView()
    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


@bot.tree.command(name="cleanup", description="حذف رسائل الطابور المكررة")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def cleanup_duplicates(interaction: discord.Interaction):
    """Clean up duplicate queue messages"""
    deleted_count = 0

    if hasattr(interaction.channel, 'history'):
        async for message in interaction.channel.history(limit=50):
            if (message.author == bot.user and message.embeds
                    and len(message.embeds) > 0
                    and "HeatSeeker Queue" in str(message.embeds[0].title)):
                try:
                    await message.delete()
                    deleted_count += 1
                except:
                    pass

    await interaction.response.send_message(
        f"✅ تم حذف {deleted_count} رسائل طابور مكررة!", ephemeral=True)


@bot.tree.command(
    name="set_leaderboard",
    description="إنشاء لوحة المتصدرين مع التحديث التلقائي ونظام الصفحات")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def set_leaderboard_channel(interaction: discord.Interaction):
    """Create auto-updating paginated leaderboard (Admin only)"""
    global leaderboard_channel_id, leaderboard_message

    if not interaction.channel:
        await interaction.response.send_message("❌ لا يمكن تحديد القناة!",
                                                ephemeral=True)
        return
    leaderboard_channel_id = interaction.channel.id

    # Send initial paginated leaderboard
    embed, current_page, total_pages = await create_leaderboard_embed(page=1)
    view = LeaderboardView(current_page, total_pages)

    await interaction.response.send_message(
        "✅ تم إنشاء لوحة المتصدرين مع نظام الصفحات والتحديث التلقائي كل 10 دقائق!",
        ephemeral=True)
    leaderboard_message = await interaction.followup.send(embed=embed,
                                                          view=view,
                                                          wait=True)


# Leaderboard command
@bot.tree.command(name="leaderboard", description="عرض لوحة المتصدرين")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def show_leaderboard(interaction: discord.Interaction):
    """Show the leaderboard"""
    embed, current_page, total_pages = await create_leaderboard_embed(page=1)
    view = LeaderboardView(current_page, total_pages)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# My stats command  
@bot.tree.command(name="mystats", description="عرض إحصائياتك الشخصية")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def show_my_stats(interaction: discord.Interaction):
    """Show user's personal statistics"""
    user_id = interaction.user.id
    current_mmr = get_player_points(user_id)
    placement_matches = get_player_placement_matches(user_id)
    is_ranked = placement_matches >= 5

    # Get user stats from database
    cursor.execute("SELECT wins, losses FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    wins = result[0] if result else 0
    losses = result[1] if result else 0
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0

    # Create stats embed
    embed = discord.Embed(
        title=f"📊 إحصائيات {interaction.user.display_name}",
        color=0x00FF00
    )

    if interaction.user.avatar:
        embed.set_thumbnail(url=interaction.user.avatar.url)

    if not is_ranked:
        # Player in placement matches
        embed.add_field(
            name="🆕 مباريات التأهيل",
            value=f"**المباريات المكتملة:** {placement_matches}/5\n**المباريات المتبقية:** {5 - placement_matches}",
            inline=False
        )
        embed.add_field(
            name="ℹ️ معلومات",
            value="أكمل 5 مباريات تأهيلية للحصول على رانك رسمي!",
            inline=False
        )
    else:
        # Ranked player
        rank_name, rank_emoji = get_rank_from_mmr(current_mmr)
        
        embed.add_field(
            name="🏆 الرانك الحالي",
            value=f"{rank_emoji} **{rank_name}**\n`{current_mmr} MMR`",
            inline=True
        )
        
        embed.add_field(
            name="📈 الإحصائيات",
            value=f"**انتصارات:** {wins}\n**خسارات:** {losses}\n**معدل الفوز:** {win_rate:.1f}%",
            inline=True
        )
        
        # Progress to next rank
        next_rank_mmr = 0
        if current_mmr < 1000:
            next_rank_mmr = 1000
            next_rank = "🥉 Bronze I"
        elif current_mmr < 1100:
            next_rank_mmr = 1100
            next_rank = "🥉 Bronze II"
        elif current_mmr < 1200:
            next_rank_mmr = 1200
            next_rank = "🥉 Bronze III"
        elif current_mmr < 1300:
            next_rank_mmr = 1300
            next_rank = "🥈 Silver I"
        elif current_mmr < 1400:
            next_rank_mmr = 1400
            next_rank = "🥈 Silver II"
        elif current_mmr < 1500:
            next_rank_mmr = 1500
            next_rank = "🥈 Silver III"
        elif current_mmr < 1600:
            next_rank_mmr = 1600
            next_rank = "🥇 Gold I"
        elif current_mmr < 1700:
            next_rank_mmr = 1700
            next_rank = "🥇 Gold II"
        elif current_mmr < 1800:
            next_rank_mmr = 1800
            next_rank = "🥇 Gold III"
        elif current_mmr < 1900:
            next_rank_mmr = 1900
            next_rank = "💎 Platinum I"
        elif current_mmr < 2000:
            next_rank_mmr = 2000
            next_rank = "💎 Platinum II"
        elif current_mmr < 2100:
            next_rank_mmr = 2100
            next_rank = "💎 Platinum III"
        elif current_mmr < 2200:
            next_rank_mmr = 2200
            next_rank = "💎 Diamond I"
        elif current_mmr < 2300:
            next_rank_mmr = 2300
            next_rank = "💎 Diamond II"
        elif current_mmr < 2400:
            next_rank_mmr = 2400
            next_rank = "💎 Diamond III"
        elif current_mmr < 2500:
            next_rank_mmr = 2500
            next_rank = "🏆 Champion I"
        elif current_mmr < 2600:
            next_rank_mmr = 2600
            next_rank = "🏆 Champion II"
        elif current_mmr < 2700:
            next_rank_mmr = 2700
            next_rank = "🏆 Champion III"
        
        if next_rank_mmr > 0:
            points_needed = next_rank_mmr - current_mmr
            embed.add_field(
                name="🎯 التقدم للرانك التالي",
                value=f"**الرانك التالي:** {next_rank}\n**النقاط المطلوبة:** {points_needed}",
                inline=False
            )
        else:
            embed.add_field(
                name="👑 مبروك!",
                value="وصلت لأعلى رانك في النظام!",
                inline=False
            )

    embed.set_footer(text="استخدم /leaderboard لرؤية ترتيبك بين اللاعبين")
    embed.timestamp = datetime.now()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Reset database command
@bot.tree.command(name="reset_database", description="إعادة تعيين قاعدة البيانات وضبط النقاط الافتراضية إلى 1300")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def reset_database(interaction: discord.Interaction):
    """Reset the entire database and set default MMR to 1300 (Admin only)"""
    
    # Create confirmation embed
    embed = discord.Embed(
        title="⚠️ تأكيد إعادة تعيين قاعدة البيانات",
        description="**هذا الإجراء خطير وغير قابل للإلغاء!**\n\n"
                   "سيتم حذف:\n"
                   "• جميع نقاط اللاعبين\n"
                   "• جميع الانتصارات والخسارات\n"
                   "• جميع المباريات التأهيلية\n"
                   "• تاريخ جميع المباريات\n\n"
                   "سيتم ضبط النقاط الافتراضية الجديدة إلى: **1300 MMR**",
        color=0xFF0000
    )
    
    embed.add_field(
        name="🔄 ما سيحدث بعد إعادة التعيين",
        value="• جميع اللاعبين سيبدؤون بـ 1300 نقطة\n"
              "• سيحتاج الجميع لعب 5 مباريات تأهيلية جديدة\n"
              "• لوحة المتصدرين ستكون فارغة\n"
              "• تاريخ المباريات سيختفي نهائياً",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ تحذير أخير",
        value="لا يمكن التراجع عن هذا الإجراء!\nتأكد من أنك تريد المتابعة فعلاً.",
        inline=False
    )
    
    view = ResetDatabaseView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Reset placement matches command
@bot.tree.command(name="reset_placements", description="إعادة تعيين المباريات التأهيلية لجميع اللاعبين إلى 0")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def reset_placements(interaction: discord.Interaction):
    """Reset all players' placement matches to 0 (Admin only)"""
    
    # Create confirmation embed
    embed = discord.Embed(
        title="⚠️ تأكيد إعادة تعيين المباريات التأهيلية",
        description="**سيتم إعادة تعيين المباريات التأهيلية لجميع اللاعبين إلى 0**\n\n"
                   "هذا يعني أن:\n"
                   "• جميع اللاعبين المُرتبين سيعودون للمباريات التأهيلية\n"
                   "• سيحتاج الجميع لعب 5 مباريات تأهيلية جديدة\n"
                   "• النقاط والانتصارات/الخسارات ستبقى كما هي\n"
                   "• لوحة المتصدرين ستصبح فارغة مؤقتاً",
        color=0xFFA500
    )
    
    embed.add_field(
        name="ℹ️ الفرق عن إعادة تعيين قاعدة البيانات",
        value="• النقاط والإحصائيات **لن تتغير**\n"
              "• فقط المباريات التأهيلية ستُعاد إلى 0\n"
              "• اللاعبون سيحتاجون 5 مباريات للحصول على رانك مرة أخرى",
        inline=False
    )
    
    view = ResetPlacementsView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Update all player roles command
@bot.tree.command(name="update_roles", description="تحديث جميع أدوار الرانك للاعبين المُرتبين")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def update_all_roles(interaction: discord.Interaction):
    """Update all players' rank roles (Admin only)"""
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.guild:
            await interaction.followup.send("❌ هذا الأمر يعمل في السيرفر فقط!", ephemeral=True)
            return
        
        # Update all roles
        updated_count = await update_all_player_roles(interaction.guild)
        
        # Get rank distribution
        rank_counts = {}
        for rank_name in RANK_ROLES.keys():
            rank_counts[rank_name] = 0
        
        cursor.execute("SELECT user_id, points FROM players WHERE placement_matches >= 5")
        ranked_players = cursor.fetchall()
        
        for user_id, points in ranked_players:
            rank_name, _ = get_rank_from_mmr(points)
            if rank_name in rank_counts:
                rank_counts[rank_name] += 1
        
        embed = discord.Embed(
            title="✅ تم تحديث أدوار الرانك بنجاح",
            description=f"تم تحديث أدوار **{updated_count}** لاعب مُرتب",
            color=0x00FF00
        )
        
        # Show rank distribution
        rank_list = []
        for rank_name, data in RANK_ROLES.items():
            count = rank_counts.get(rank_name, 0)
            if count > 0:
                rank_list.append(f"{data['emoji']} **{rank_name}**: {count} لاعب")
        
        if rank_list:
            embed.add_field(
                name="📊 توزيع الرانكات",
                value="\n".join(rank_list),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ ملاحظة",
            value="• فقط اللاعبين الذين أكملوا 5 مباريات تأهيلية يحصلون على أدوار\n"
                  "• يتم تحديث الأدوار تلقائياً بعد كل مباراة\n"
                  "• استخدم هذا الأمر فقط عند الحاجة لإصلاح مشاكل الأدوار",
            inline=False
        )
        
        embed.set_footer(text=f"تم بواسطة {interaction.user.display_name}")
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"Roles updated by {interaction.user.display_name} - {updated_count} players affected")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ فشل في تحديث الأدوار",
            description=f"حدث خطأ: {str(e)}",
            color=0xFF0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        print(f"Role update failed: {e}")

# Sync commands command
@bot.tree.command(name="sync_commands", description="مزامنة أوامر البوت مع Discord")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def sync_commands(interaction: discord.Interaction):
    """Sync bot commands with Discord (Admin only)"""
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Sync commands
        synced = await bot.tree.sync()
        
        embed = discord.Embed(
            title="✅ تم مزامنة الأوامر بنجاح",
            description=f"تم مزامنة **{len(synced)}** أمر مع Discord",
            color=0x00FF00
        )
        
        # List synced commands
        command_list = []
        for cmd in synced:
            command_list.append(f"• `/{cmd.name}` - {cmd.description}")
        
        if command_list:
            embed.add_field(
                name="📝 الأوامر المُزامنة",
                value="\n".join(command_list[:10]),  # Show first 10
                inline=False
            )
        
        if len(synced) > 10:
            embed.add_field(
                name="📊 المجموع",
                value=f"وأوامر أخرى... المجموع: {len(synced)} أمر",
                inline=False
            )
        
        embed.add_field(
            name="⏰ ملاحظة",
            value="قد يستغرق Discord بضع دقائق لإظهار الأوامر الجديدة",
            inline=False
        )
        
        embed.set_footer(text=f"تم بواسطة {interaction.user.display_name}")
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"Commands synced by {interaction.user.display_name} - {len(synced)} commands")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ فشل في مزامنة الأوامر",
            description=f"حدث خطأ: {str(e)}",
            color=0xFF0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        print(f"Command sync failed: {e}")

@bot.tree.command(name="rank",
                  description="عرض معلومات رانكك ومعلومات التقدم (DM فقط)")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def show_rank_info(interaction: discord.Interaction):
    """Show user rank and progress info (DM only)"""

    # Check if command is used in DM
    if interaction.guild is not None:
        await interaction.response.send_message(
            "❌ هذا الأمر يعمل في الرسائل الخاصة فقط! ارسل `/rank` في رسالة خاصة للبوت.",
            ephemeral=True)
        return

    user_id = interaction.user.id
    current_mmr = get_player_points(user_id)
    placement_matches = get_player_placement_matches(user_id)
    is_ranked = placement_matches >= 5

    # Create profile embed
    embed = discord.Embed(
        title=f"🎮 ملف {interaction.user.display_name} الشخصي", color=0x2F3136)

    # Add user avatar
    if interaction.user.avatar:
        embed.set_thumbnail(url=interaction.user.avatar.url)

    if not is_ranked:
        # Player in placement matches
        embed.add_field(
            name="📋 المباريات التأهيلية",
            value=
            f"**التقدم:** {placement_matches}/5 مباريات\n**MMR الحالي:** {current_mmr}\n**الحالة:** في المباريات التأهيلية",
            inline=False)

        embed.add_field(
            name="📈 ما تحتاجه للحصول على الرانك:",
            value=
            f"• أكمل {5 - placement_matches} مباريات إضافية\n• بعدها ستحصل على رانكك الأول ودور في السيرفر\n• ستظهر في لوحة المتصدرين",
            inline=False)

        # Show what rank they would get
        predicted_rank_name, predicted_rank_emoji = get_rank_from_mmr(
            current_mmr)
        embed.add_field(name="🔮 الرانك المتوقع (حسب MMR الحالي)",
                        value=f"{predicted_rank_emoji} {predicted_rank_name}",
                        inline=False)

    else:
        # Ranked player
        current_rank_name, current_rank_emoji = get_rank_from_mmr(current_mmr)

        embed.add_field(
            name="🎖️ رانكك الحالي",
            value=
            f"{current_rank_emoji} {current_rank_name}\n**MMR:** {current_mmr}",
            inline=False)

        # Find next rank
        next_rank_info = None
        for rank_name, rank_data in RANK_ROLES.items():
            if rank_data["min_mmr"] > current_mmr:
                next_rank_info = (rank_name, rank_data)
                break

        if next_rank_info:
            rank_name, rank_data = next_rank_info
            points_needed = rank_data["min_mmr"] - current_mmr
            embed.add_field(
                name="⬆️ الرانك القادم",
                value=
                f"{rank_data['emoji']} {rank_name}\n**تحتاج:** {points_needed} نقطة إضافية\n**MMR المطلوب:** {rank_data['min_mmr']}",
                inline=False)

            # Calculate wins needed
            wins_needed = max(1, (points_needed + 24) // 25)  # Round up
            embed.add_field(
                name="🏆 للوصول للرانك القادم",
                value=
                f"• انتصارات تقريبية مطلوبة: **{wins_needed}** انتصار\n• كل انتصار = +25 MMR\n• كل هزيمة = -20 MMR",
                inline=False)
        else:
            embed.add_field(
                name="👑 أعلى رانك!",
                value=
                "🎉 تهانينا! وصلت لأعلى رانك في النظام!\n**LEGENDARY SEEKER** هو أقصى رانك متاح.",
                inline=False)

    # Add rank system info
    embed.add_field(
        name="📊 نظام الرانكات",
        value=
        "**UNRANKED** (700-799) → **SILVER SEEKER** (800-949) → **PLATINUM SEEKER** (950-1099) → **CRYSTAL SEEKER** (1100-1249) → **ELITE SEEKER** (1250-1449) → **MASTER SEEKER** (1450-1699) → **LEGENDARY SEEKER** (1700+)",
        inline=False)

    embed.set_footer(text="💡 نصيحة: انضم للطابور في السيرفر لتحسين رانكك!")
    embed.timestamp = datetime.now()

    await interaction.response.send_message(embed=embed)


# Admin result modification command
@bot.tree.command(name="admin_result",
                  description="تعديل نتائج المباراة للمشرفين")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def admin_modify_result(interaction: discord.Interaction):
    """Allow admins to modify match results"""
    # Check if user has admin permissions
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ هذا الأمر يعمل في السيرفر فقط!", ephemeral=True)
        return
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not member.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return

    # Get recent completed matches from database
    cursor.execute("""
        SELECT match_id, team1_player1, team1_player2, team2_player1, team2_player2, 
               winner, created_at 
        FROM matches 
        WHERE completed = 1 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    recent_matches = cursor.fetchall()

    if not recent_matches:
        await interaction.response.send_message(
            "❌ لا توجد مباريات مكتملة للتعديل!", ephemeral=True)
        return

    # Create select menu with recent matches
    options = []
    for match in recent_matches[:10]:  # Limit to 10 matches
        match_id, t1p1, t1p2, t2p1, t2p2, winner, created_at = match

        # Get player names
        try:
            p1 = bot.get_user(t1p1)
            p2 = bot.get_user(t1p2)
            p3 = bot.get_user(t2p1)
            p4 = bot.get_user(t2p2)

            if p1 and p2 and p3 and p4:
                winner_text = "Team 1" if winner == 1 else "Team 2" if winner == 2 else "Cancelled"
                description = f"{p1.display_name} & {p2.display_name} vs {p3.display_name} & {p4.display_name} - {winner_text}"

                options.append(
                    discord.SelectOption(
                        label=f"HSM{match_id}",
                        description=description[:100],  # Discord limit
                        value=str(match_id)))
        except:
            continue

    if not options:
        await interaction.response.send_message(
            "❌ لا يمكن العثور على مباريات صالحة للتعديل!", ephemeral=True)
        return

    view = AdminResultView(options)
    embed = discord.Embed(title="🛠️ تعديل نتائج المباريات",
                          description="اختر المباراة التي تريد تعديل نتيجتها:",
                          color=0xFF6B00)

    embed.add_field(name="⚠️ تنبيه",
                    value="تعديل النتائج سيؤثر على MMR ورانك اللاعبين",
                    inline=False)

    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


# Match result slash command with interactive menu
@bot.tree.command(name="report",
                  description="تسجيل نتيجة المباراة - قائمة تفاعلية")
@app_commands.describe()
@app_commands.default_permissions(administrator=True)
async def match_result(interaction: discord.Interaction):
    """Report match result with interactive menu"""
    await open_result_menu(interaction)


async def open_result_menu(interaction: discord.Interaction):
    """Open result selection menu for match participants"""
    user = interaction.user

    # Find which match this user is in
    user_match = None
    for match_name, match_info in active_matches.items():
        if user in match_info['players']:
            user_match = match_name
            break

    if not user_match:
        # Check if there are any active matches at all
        if not active_matches:
            await interaction.response.send_message(
                "❌ لا توجد مباريات نشطة حالياً!\n🎮 ابدأ كيو جديد لإنشاء مباراة.",
                ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ لست في أي مباراة نشطة!\n🔍 تأكد من أنك أحد اللاعبين في المباراة.",
                ephemeral=True)
        return

    # Check if result already reported for this match
    if user_match in match_results:
        reported_by = match_results[user_match]['reporter']
        await interaction.response.send_message(
            f"❌ تم تسجيل النتيجة مسبقاً بواسطة {reported_by.display_name}!",
            ephemeral=True)
        return

    # Mark that this user is reporting the result (first-come-first-served)
    match_results[user_match] = {'reporter': user, 'processing': True}

    # Get match info for displaying team details
    match_info = active_matches[user_match]
    team1 = match_info['team1']
    team2 = match_info['team2']

    # Create result selection embed
    embed = discord.Embed(
        title=f"🏁 {user_match} - اختر الفريق الفائز",
        description=f"**{user.display_name}** يقوم بتسجيل النتيجة",
        color=0xFFD700)

    # Show actual team members
    team1_text = f"{team1[0].display_name}\n{team1[1].display_name}"
    team2_text = f"{team2[0].display_name}\n{team2[1].display_name}"

    embed.add_field(name="🔵 Team 1 (Blue)", value=team1_text, inline=True)

    embed.add_field(name="🟠 Team 2 (Orange)", value=team2_text, inline=True)

    embed.add_field(
        name="⚠️ تنبيه مهم",
        value=
        "اختيارك نهائي ولا يمكن تغييره!\nسيتم حذف القنوات تلقائياً بعد التأكيد.",
        inline=False)

    view = ResultMenuView(user_match)
    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


async def process_match_result(interaction: discord.Interaction,
                               match_name: str, winner: int, result_text: str):
    """Process the selected match result"""
    user = interaction.user

    if match_name not in active_matches:
        await interaction.response.send_message("❌ المباراة غير موجودة!",
                                                ephemeral=True)
        return

    match_info = active_matches[match_name]

    # Update match results
    match_results[match_name] = {
        'winner': winner,
        'result_text': result_text,
        'reporter': user
    }

    # Create final result embed
    embed = discord.Embed(title=f"🏁 {match_name} - نتيجة المباراة",
                          description=f"**النتيجة:** {result_text}",
                          color=0x00FF00)

    embed.add_field(
        name="📊 معلومات المباراة",
        value=
        f"**Name:** {match_name}\n**Server:** ME Only\n**Mode:** 2v2\n**تم تسجيلها بواسطة:** {user.display_name}",
        inline=False)

    winning_team = match_info['team1'] if winner == 1 else match_info['team2']
    losing_team = match_info['team2'] if winner == 1 else match_info['team1']

    # Calculate MMR changes
    points_gained = 25
    points_lost = 20

    winners_text = ""
    for p in winning_team:
        old_points = get_player_points(p.id)
        placement_matches = get_player_placement_matches(p.id)

        if placement_matches < 5:
            # Placement match - smaller MMR change
            new_points = old_points + 10  # Smaller gain for placement
            winners_text += f"{'🔵' if winner == 1 else '🟠'} {p.display_name}\n`📋 Placement {placement_matches}/5 → {placement_matches + 1}/5`\n"
        else:
            # Ranked match - normal MMR change
            new_points = old_points + points_gained
            old_rank_name, old_rank_emoji = get_rank_from_mmr(old_points)
            new_rank_name, new_rank_emoji = get_rank_from_mmr(new_points)
            rank_change = f" → {new_rank_emoji} {new_rank_name}" if old_rank_name != new_rank_name else ""
            winners_text += f"{'🔵' if winner == 1 else '🟠'} {p.display_name}\n`{old_points} → {new_points} (+{points_gained})`{rank_change}\n"

    losers_text = ""
    for p in losing_team:
        old_points = get_player_points(p.id)
        placement_matches = get_player_placement_matches(p.id)

        if placement_matches < 5:
            # Placement match - smaller MMR change
            new_points = max(0, old_points - 5)  # Smaller loss for placement
            losers_text += f"{'🟠' if winner == 1 else '🔵'} {p.display_name}\n`📋 Placement {placement_matches}/5 → {placement_matches + 1}/5`\n"
        else:
            # Ranked match - normal MMR change
            new_points = max(0, old_points - points_lost)
            old_rank_name, old_rank_emoji = get_rank_from_mmr(old_points)
            new_rank_name, new_rank_emoji = get_rank_from_mmr(new_points)
            rank_change = f" → {new_rank_emoji} {new_rank_name}" if old_rank_name != new_rank_name else ""
            losers_text += f"{'🟠' if winner == 1 else '🔵'} {p.display_name}\n`{old_points} → {new_points} (-{points_lost})`{rank_change}\n"

    embed.add_field(name="🏆 الفائزون", value=winners_text, inline=True)
    embed.add_field(name="💔 الخاسرون", value=losers_text, inline=True)

    # Update player MMR and send DMs
    points_gained = 25
    points_lost = 20

    for player in winning_team:
        old_points = get_player_points(player.id)
        placement_matches = get_player_placement_matches(player.id)

        # Increment placement matches
        increment_placement_matches(player.id)
        new_placement = placement_matches + 1

        if placement_matches < 5:
            # Placement match - smaller MMR change
            new_points = old_points + 10
            update_player_points(player.id, new_points)

            try:
                if new_placement == 5:
                    # Just completed placement matches - show rank and give role
                    rank_name, rank_emoji = get_rank_from_mmr(new_points)

                    # Give rank role
                    if interaction.guild:
                        member = interaction.guild.get_member(player.id)
                        if member:
                            await update_player_rank_role(member, new_points)

                    await player.send(
                        f"🎉 تهانينا! فزت في مباراة {match_name}!\n"
                        f"📋 المباريات التأهيلية: {new_placement}/5 - مكتملة!\n"
                        f"🎖️ رانكك الأول: {rank_emoji} {rank_name}\n"
                        f"📈 MMR: {old_points} → {new_points} (+10)\n"
                        f"🏷️ تم إعطاؤك دور الرانك في السيرفر!")
                else:
                    await player.send(
                        f"🎉 تهانينا! فزت في مباراة {match_name}!\n"
                        f"📋 المباريات التأهيلية: {new_placement}/5\n"
                        f"📈 MMR: {old_points} → {new_points} (+10)")
            except:
                pass
        else:
            # Ranked match - normal MMR change
            new_points = old_points + points_gained
            update_player_points(player.id, new_points)

            try:
                old_rank_name, old_rank_emoji = get_rank_from_mmr(old_points)
                new_rank_name, new_rank_emoji = get_rank_from_mmr(new_points)
                rank_msg = f"\n🎖️ Rank: {old_rank_emoji} {old_rank_name} → {new_rank_emoji} {new_rank_name}" if old_rank_name != new_rank_name else f"\n🎖️ Rank: {old_rank_emoji} {old_rank_name}"

                # Update role if rank changed
                if old_rank_name != new_rank_name:
                    if interaction.guild:
                        member = interaction.guild.get_member(player.id)
                        if member:
                            await update_player_rank_role(member, new_points)
                            rank_msg += "\n🏷️ تم تحديث دور الرانك!"

                await player.send(
                    f"🎉 تهانينا! فزت في مباراة {match_name}!\n"
                    f"📈 MMR: {old_points} → {new_points} (+{points_gained}){rank_msg}"
                )
            except:
                pass

    for player in losing_team:
        old_points = get_player_points(player.id)
        placement_matches = get_player_placement_matches(player.id)

        # Increment placement matches
        increment_placement_matches(player.id)
        new_placement = placement_matches + 1

        if placement_matches < 5:
            # Placement match - smaller MMR change
            new_points = max(0, old_points - 5)
            update_player_points(player.id, new_points)

            try:
                if new_placement == 5:
                    # Just completed placement matches - show rank and give role
                    rank_name, rank_emoji = get_rank_from_mmr(new_points)

                    # Give rank role
                    if interaction.guild:
                        member = interaction.guild.get_member(player.id)
                        if member:
                            await update_player_rank_role(member, new_points)

                    await player.send(
                        f"💪 مباراة {match_name} انتهت. حظ أفضل في المرة القادمة!\n"
                        f"📋 المباريات التأهيلية: {new_placement}/5 - مكتملة!\n"
                        f"🎖️ رانكك الأول: {rank_emoji} {rank_name}\n"
                        f"📉 MMR: {old_points} → {new_points} (-5)\n"
                        f"🏷️ تم إعطاؤك دور الرانك في السيرفر!")
                else:
                    await player.send(
                        f"💪 مباراة {match_name} انتهت. حظ أفضل في المرة القادمة!\n"
                        f"📋 المباريات التأهيلية: {new_placement}/5\n"
                        f"📉 MMR: {old_points} → {new_points} (-5)")
            except:
                pass
        else:
            # Ranked match - normal MMR change
            new_points = max(0, old_points - points_lost)
            update_player_points(player.id, new_points)

            try:
                old_rank_name, old_rank_emoji = get_rank_from_mmr(old_points)
                new_rank_name, new_rank_emoji = get_rank_from_mmr(new_points)
                rank_msg = f"\n🎖️ Rank: {old_rank_emoji} {old_rank_name} → {new_rank_emoji} {new_rank_name}" if old_rank_name != new_rank_name else f"\n🎖️ Rank: {old_rank_emoji} {old_rank_name}"

                # Update role if rank changed
                if old_rank_name != new_rank_name:
                    if interaction.guild:
                        member = interaction.guild.get_member(player.id)
                        if member:
                            await update_player_rank_role(member, new_points)
                            rank_msg += "\n🏷️ تم تحديث دور الرانك!"

                await player.send(
                    f"💪 مباراة {match_name} انتهت. حظ أفضل في المرة القادمة!\n"
                    f"📉 MMR: {old_points} → {new_points} (-{points_lost}){rank_msg}"
                )
            except:
                pass

    # Update match as completed in database
    cursor.execute(
        """
        UPDATE matches 
        SET winner = ?, completed = 1
        WHERE match_id = ?
    """, (winner, match_info['match_id']))
    conn.commit()

    # Send result to the match channel (using followup since response was already used)
    try:
        await interaction.followup.send(embed=embed)
    except:
        # Fallback: send to match text channel directly
        if 'text_channel' in match_info and match_info['text_channel']:
            await match_info['text_channel'].send(embed=embed)

    # Send result notification to results channel
    try:
        results_channel = bot.get_channel(results_channel_id)
        if results_channel and isinstance(results_channel,
                                          discord.TextChannel):
            # Create public results embed
            public_embed = discord.Embed(
                title=f"🏁 {match_name} - Match Results",
                description=
                f"**🏆 Winner:** {result_text}\n⚖️ **Balanced MMR Distribution Applied**",
                color=0x00FF00 if winner == 1 else 0xFF6600)

            # Show teams with MMR changes (get updated points from processing above)
            winning_mmr_text = ""
            losing_mmr_text = ""

            for player in winning_team:
                current_points = get_player_points(
                    player.id)  # Get current points after update
                placement_matches = get_player_placement_matches(player.id)

                if placement_matches <= 5:  # Show placement progress
                    winning_mmr_text += f"{'🔵' if winner == 1 else '🟠'} {player.display_name}\n`{current_points} MMR | Placement: {placement_matches}/5 | +10 MMR`\n"
                else:
                    rank_name, rank_emoji = get_rank_from_mmr(current_points)
                    old_mmr = current_points - points_gained  # Calculate old MMR
                    winning_mmr_text += f"{'🔵' if winner == 1 else '🟠'} {rank_emoji} {player.display_name}\n`{old_mmr} → {current_points} MMR (+{points_gained})`\n"

            for player in losing_team:
                current_points = get_player_points(
                    player.id)  # Get current points after update
                placement_matches = get_player_placement_matches(player.id)

                if placement_matches <= 5:  # Show placement progress
                    losing_mmr_text += f"{'🟠' if winner == 1 else '🔵'} {player.display_name}\n`{current_points} MMR | Placement: {placement_matches}/5 | -5 MMR`\n"
                else:
                    rank_name, rank_emoji = get_rank_from_mmr(current_points)
                    old_mmr = current_points + points_lost  # Calculate old MMR
                    losing_mmr_text += f"{'🟠' if winner == 1 else '🔵'} {rank_emoji} {player.display_name}\n`{old_mmr} → {current_points} MMR (-{points_lost})`\n"

            public_embed.add_field(name="🏆 Winners",
                                   value=winning_mmr_text
                                   if winning_mmr_text else "No winners data",
                                   inline=True)
            public_embed.add_field(
                name="💔 Losers",
                value=losing_mmr_text if losing_mmr_text else "No losers data",
                inline=True)

            # Calculate team averages for display
            winner_avg = sum(get_player_points(p.id)
                             for p in winning_team) // len(winning_team)
            loser_avg = sum(get_player_points(p.id)
                            for p in losing_team) // len(losing_team)

            public_embed.add_field(
                name="📊 Match Info",
                value=
                f"**Mode:** 2v2 Ranked\n**Server:** ME Only\n**Team Balance:** Winner Avg: `{winner_avg}` | Loser Avg: `{loser_avg}`\n**Reported by:** {user.display_name}",
                inline=False)

            public_embed.set_footer(text=f"Match ID: {match_info['match_id']}")
            public_embed.timestamp = datetime.now()

            await results_channel.send(embed=public_embed)
            print(f"✅ Match results sent to results channel for {match_name}")
            print(f"Winners: {[p.display_name for p in winning_team]}")
            print(f"Losers: {[p.display_name for p in losing_team]}")
    except Exception as e:
        print(f"❌ Error sending to results channel: {e}")
        print(f"Channel ID: {results_channel_id}")
        print(
            f"Channel found: {results_channel is not None if 'results_channel' in locals() else 'Channel not found'}"
        )

    # Clean up match channels after a short delay
    try:
        await asyncio.sleep(10)  # Allow time to read results

        # Delete voice channels first
        if 'team1_voice' in match_info and match_info['team1_voice']:
            try:
                await match_info['team1_voice'].delete()
                print(f"Deleted Team 1 voice channel for {match_name}")
            except:
                pass

        if 'team2_voice' in match_info and match_info['team2_voice']:
            try:
                await match_info['team2_voice'].delete()
                print(f"Deleted Team 2 voice channel for {match_name}")
            except:
                pass

        # Delete text channel
        if 'text_channel' in match_info and match_info['text_channel']:
            try:
                await match_info['text_channel'].delete()
                print(f"Deleted text channel for {match_name}")
            except:
                pass

        # Clean up data
        if match_name in active_matches:
            del active_matches[match_name]
        if match_name in match_results:
            del match_results[match_name]

        print(f"✅ تم حذف جميع قنوات المباراة {match_name} تلقائياً")

    except Exception as e:
        print(f"❌ خطأ في حذف قنوات {match_name}: {e}")


# Error handling
@setup_queue.error
@admin_panel.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")


# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please set your Discord bot token in the .env file")
    else:
        try:
            # Start Flask server in a separate thread for health checks
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            print("✅ HTTP health check server started")

            # Start Discord bot
            print("🚀 Starting HeatSeeker Discord Bot...")
            bot.run(token)
        except discord.LoginFailure:
            print("❌ Error: Invalid Discord token!")
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
