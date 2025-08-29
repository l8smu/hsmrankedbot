import discord
from discord.ext import commands
import sqlite3
import asyncio
import random
from datetime import datetime

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Global variables for queue and match system
player_queue = []
active_matches = {}
match_id_counter = 1

# Channel configuration - set this to your dedicated 2v2 channel name
QUEUE_CHANNEL_NAME = "2v2-queue"  # Change this to your channel name

# Database setup
conn = sqlite3.connect("players.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    username TEXT,
    mmr INTEGER DEFAULT 1000,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0
)''')

# Create matches table
c.execute('''CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    team1_players TEXT,
    team2_players TEXT,
    winner INTEGER,
    created_at TEXT,
    ended_at TEXT,
    channel_id TEXT
)''')
conn.commit()

# Add sample data for demonstration
def add_sample_data():
    """Add sample players for demonstration"""
    sample_players = [
        ('123456789', 'PlayerOne', 1200, 15, 5),
        ('987654321', 'TopGamer', 1450, 25, 8),
        ('456789123', 'SkillMaster', 1350, 20, 12),
        ('789123456', 'ProPlayer', 1100, 18, 15),
        ('321654987', 'GameChamp', 1300, 22, 10),
        ('654321789', 'EliteGamer', 1500, 30, 5),
        ('147258369', 'RankClimber', 1250, 16, 9),
        ('963852741', 'CompetitivePro', 1400, 28, 7),
        ('258741963', 'StrategyMaster', 1180, 14, 11),
        ('741852963', 'LeaderboardKing', 1600, 35, 3)
    ]
    
    for player_id, username, mmr, wins, losses in sample_players:
        c.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        if not c.fetchone():
            c.execute("INSERT INTO players (id, username, mmr, wins, losses) VALUES (?, ?, ?, ?, ?)",
                     (player_id, username, mmr, wins, losses))
    conn.commit()

# Add or update player
def add_or_update_player(user):
    c.execute("SELECT * FROM players WHERE id = ?", (str(user.id),))
    result = c.fetchone()
    if not result:
        c.execute("INSERT INTO players (id, username) VALUES (?, ?)", (str(user.id), user.name))
        conn.commit()

def is_queue_channel(ctx):
    """Check if the command is being used in the correct channel"""
    return ctx.channel.name == QUEUE_CHANNEL_NAME

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    add_sample_data()
    print("Sample data added to database")
    print(f"Queue system will only work in channel: #{QUEUE_CHANNEL_NAME}")
    
    # Check if the queue channel exists in any guild
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name=QUEUE_CHANNEL_NAME)
        if channel:
            # Send a startup message to the queue channel
            embed = discord.Embed(
                title="🤖 HeatSeeker Bot Online!",
                description=f"2v2 Queue system is now active in #{QUEUE_CHANNEL_NAME}",
                color=discord.Color.green()
            )
            embed.add_field(name="Available Commands", 
                          value="`/queue` - Join queue\n`/leave` - Leave queue\n`/status` - Check queue", 
                          inline=False)
            embed.add_field(name="Setup Complete", 
                          value="Players can now start queuing for 2v2 matches!", 
                          inline=False)
            await channel.send(embed=embed)

# Rank command
@bot.command(name='rank')
async def rank(ctx):
    """Display your current rank and stats"""
    add_or_update_player(ctx.author)
    c.execute("SELECT mmr, wins, losses FROM players WHERE id = ?", (str(ctx.author.id),))
    result = c.fetchone()
    
    if result:
        mmr, wins, losses = result
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        embed = discord.Embed(
            title=f"🏆 {ctx.author.name}'s Rank",
            color=discord.Color.blue()
        )
        embed.add_field(name="MMR", value=f"**{mmr}**", inline=True)
        embed.add_field(name="Wins", value=f"**{wins}**", inline=True)
        embed.add_field(name="Losses", value=f"**{losses}**", inline=True)
        embed.add_field(name="Win Rate", value=f"**{win_rate:.1f}%**", inline=True)
        embed.add_field(name="Total Games", value=f"**{total_games}**", inline=True)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Error retrieving your stats. Please try again.")

# Top command
@bot.command(name='top')
async def top(ctx):
    """Display top 10 players by MMR"""
    c.execute("SELECT username, mmr, wins, losses FROM players ORDER BY mmr DESC LIMIT 10")
    top_players = c.fetchall()
    
    if top_players:
        embed = discord.Embed(
            title="🏆 Top 10 Players Leaderboard",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        for i, (username, mmr, wins, losses) in enumerate(top_players):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            leaderboard_text += f"{medal} **{username}** - {mmr} MMR\n"
            leaderboard_text += f"     W: {wins} | L: {losses} | WR: {win_rate:.1f}%\n\n"
        
        embed.description = leaderboard_text
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ No players found in the leaderboard.")

# Stats command
@bot.command(name='stats')
async def stats(ctx, member: discord.Member = None):
    """Display stats for a specific player"""
    target_user = member or ctx.author
    
    c.execute("SELECT username, mmr, wins, losses FROM players WHERE id = ?", (str(target_user.id),))
    result = c.fetchone()
    
    if result:
        username, mmr, wins, losses = result
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 {username}'s Statistics",
            color=discord.Color.green()
        )
        embed.add_field(name="MMR", value=f"**{mmr}**", inline=True)
        embed.add_field(name="Wins", value=f"**{wins}**", inline=True)
        embed.add_field(name="Losses", value=f"**{losses}**", inline=True)
        embed.add_field(name="Total Games", value=f"**{total_games}**", inline=True)
        embed.add_field(name="Win Rate", value=f"**{win_rate:.1f}%**", inline=True)
        
        # Calculate rank position
        c.execute("SELECT COUNT(*) FROM players WHERE mmr > ?", (mmr,))
        rank_position = c.fetchone()[0] + 1
        embed.add_field(name="Rank", value=f"**#{rank_position}**", inline=True)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ No stats found for {target_user.mention}. Use `/rank` to initialize your profile.")

# Help command
@bot.command(name='help')
async def help_command(ctx):
    """Display available commands"""
    embed = discord.Embed(
        title="🤖 HeatSeeker Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📊 Player Stats",
        value="`/rank` - Display your current MMR and statistics\n" +
              "`/top` - Show the top 10 players leaderboard\n" +
              "`/stats @user` - Display statistics for a specific player",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Queue System",
        value="`/queue` - Join the 2v2 queue\n" +
              "`/leave` - Leave the queue\n" +
              "`/status` - Show current queue status",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Match System",
        value="`/win 1` or `/win 2` - Report the winning team\n" +
              "`/cancel` - Cancel an active match",
        inline=False
    )
    
    embed.add_field(
        name="/help",
        value="Show this help message",
        inline=False
    )
    
    embed.set_footer(text="Join the queue to start competitive 2v2 matches!")
    await ctx.send(embed=embed)

# Queue system commands
@bot.command(name='queue')
async def queue(ctx):
    """Join the 2v2 queue"""
    # Check if command is used in correct channel
    if not is_queue_channel(ctx):
        await ctx.send(f"❌ Please use queue commands in #{QUEUE_CHANNEL_NAME} channel!")
        return
    
    add_or_update_player(ctx.author)
    user_id = str(ctx.author.id)
    
    # Check if player is already in queue
    if any(player['id'] == user_id for player in player_queue):
        await ctx.send("❌ You are already in the queue!")
        return
    
    # Check if player is in an active match
    if any(user_id in match['players'] for match in active_matches.values()):
        await ctx.send("❌ You are currently in an active match!")
        return
    
    # Add player to queue
    c.execute("SELECT username, mmr FROM players WHERE id = ?", (user_id,))
    result = c.fetchone()
    if result:
        username, mmr = result
        player_queue.append({'id': user_id, 'username': username, 'mmr': mmr, 'user': ctx.author})
        
        embed = discord.Embed(
            title="🎮 Joined Queue",
            description=f"{ctx.author.mention} joined the 2v2 queue!",
            color=discord.Color.green()
        )
        embed.add_field(name="Players in Queue", value=f"{len(player_queue)}/4", inline=True)
        embed.add_field(name="Your MMR", value=f"{mmr}", inline=True)
        
        await ctx.send(embed=embed)
        
        # Check if we have 4 players to start a match
        if len(player_queue) >= 4:
            await start_match(ctx)

@bot.command(name='leave')
async def leave_queue(ctx):
    """Leave the queue"""
    # Check if command is used in correct channel
    if not is_queue_channel(ctx):
        await ctx.send(f"❌ Please use queue commands in #{QUEUE_CHANNEL_NAME} channel!")
        return
    
    user_id = str(ctx.author.id)
    
    # Remove player from queue
    global player_queue
    player_queue = [p for p in player_queue if p['id'] != user_id]
    
    embed = discord.Embed(
        title="🚪 Left Queue",
        description=f"{ctx.author.mention} left the queue.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Players in Queue", value=f"{len(player_queue)}/4", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='status')
async def queue_status(ctx):
    """Show current queue status"""
    # Check if command is used in correct channel
    if not is_queue_channel(ctx):
        await ctx.send(f"❌ Please use queue commands in #{QUEUE_CHANNEL_NAME} channel!")
        return
    
    if not player_queue:
        embed = discord.Embed(
            title="📋 Queue Status",
            description="Queue is empty. Use `/queue` to join!",
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="📋 Queue Status",
            description=f"Players in queue: {len(player_queue)}/4",
            color=discord.Color.blue()
        )
        
        queue_text = ""
        for i, player in enumerate(player_queue, 1):
            queue_text += f"{i}. {player['username']} ({player['mmr']} MMR)\n"
        
        embed.add_field(name="Players", value=queue_text, inline=False)
    
    await ctx.send(embed=embed)

async def start_match(ctx):
    """Start a 2v2 match with balanced teams"""
    global match_id_counter, player_queue
    
    # Get 4 players from queue
    match_players = player_queue[:4]
    player_queue = player_queue[4:]
    
    # Create balanced teams based on MMR
    teams = create_balanced_teams(match_players)
    team1, team2 = teams
    
    # Create match record
    match_id = match_id_counter
    match_id_counter += 1
    
    # Store match data
    active_matches[match_id] = {
        'team1': team1,
        'team2': team2,
        'players': [p['id'] for p in match_players],
        'channel_id': str(ctx.channel.id),
        'created_at': datetime.now().isoformat()
    }
    
    # Save to database
    team1_ids = ','.join([p['id'] for p in team1])
    team2_ids = ','.join([p['id'] for p in team2])
    c.execute("""INSERT INTO matches (match_id, team1_players, team2_players, created_at, channel_id) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (match_id, team1_ids, team2_ids, datetime.now().isoformat(), str(ctx.channel.id)))
    conn.commit()
    
    # Create match announcement
    embed = discord.Embed(
        title="🏆 MATCH FOUND!",
        description=f"Match #{match_id} is ready to start!",
        color=discord.Color.gold()
    )
    
    # Team 1
    team1_mentions = ' '.join([p['user'].mention for p in team1])
    team1_info = '\n'.join([f"{p['username']} ({p['mmr']} MMR)" for p in team1])
    embed.add_field(name="🔴 Team 1", value=f"{team1_mentions}\n{team1_info}", inline=True)
    
    # Team 2
    team2_mentions = ' '.join([p['user'].mention for p in team2])
    team2_info = '\n'.join([f"{p['username']} ({p['mmr']} MMR)" for p in team2])
    embed.add_field(name="🔵 Team 2", value=f"{team2_mentions}\n{team2_info}", inline=True)
    
    # Average MMR
    avg_mmr = sum(p['mmr'] for p in match_players) / 4
    embed.add_field(name="📊 Average MMR", value=f"{avg_mmr:.0f}", inline=False)
    
    embed.add_field(name="📝 Report Results", 
                   value=f"Use `/win 1` or `/win 2` to report the winning team\nMatch ID: {match_id}", 
                   inline=False)
    
    await ctx.send(embed=embed)

def create_balanced_teams(players):
    """Create balanced teams based on MMR"""
    # Sort players by MMR
    sorted_players = sorted(players, key=lambda x: x['mmr'], reverse=True)
    
    # Try different combinations to find the most balanced
    best_diff = float('inf')
    best_teams = None
    
    # Generate all possible team combinations
    from itertools import combinations
    for team1_combo in combinations(sorted_players, 2):
        team1 = list(team1_combo)
        team2 = [p for p in sorted_players if p not in team1]
        
        team1_mmr = sum(p['mmr'] for p in team1)
        team2_mmr = sum(p['mmr'] for p in team2)
        diff = abs(team1_mmr - team2_mmr)
        
        if diff < best_diff:
            best_diff = diff
            best_teams = (team1, team2)
    
    return best_teams

@bot.command(name='win')
async def report_win(ctx, team_number: int):
    """Report the winning team (1 or 2)"""
    # Check if command is used in correct channel
    if not is_queue_channel(ctx):
        await ctx.send(f"❌ Please use match commands in #{QUEUE_CHANNEL_NAME} channel!")
        return
    
    if team_number not in [1, 2]:
        await ctx.send("❌ Please specify team 1 or 2. Example: `/win 1`")
        return
    
    # Find active match in this channel
    match_id = None
    for mid, match_data in active_matches.items():
        if match_data['channel_id'] == str(ctx.channel.id):
            match_id = mid
            break
    
    if not match_id:
        await ctx.send("❌ No active match found in this channel!")
        return
    
    match_data = active_matches[match_id]
    
    # Check if user is part of the match
    user_id = str(ctx.author.id)
    if user_id not in match_data['players']:
        await ctx.send("❌ You can only report results for matches you're participating in!")
        return
    
    # Update match result
    winning_team = match_data['team1'] if team_number == 1 else match_data['team2']
    losing_team = match_data['team2'] if team_number == 1 else match_data['team1']
    
    # Calculate MMR changes
    mmr_changes = calculate_mmr_changes(winning_team, losing_team)
    
    # Update player stats
    for player in winning_team:
        c.execute("UPDATE players SET wins = wins + 1, mmr = mmr + ? WHERE id = ?", 
                 (mmr_changes['winners'], player['id']))
    
    for player in losing_team:
        c.execute("UPDATE players SET losses = losses + 1, mmr = mmr + ? WHERE id = ?", 
                 (mmr_changes['losers'], player['id']))
    
    # Update match record
    c.execute("UPDATE matches SET winner = ?, ended_at = ? WHERE match_id = ?", 
             (team_number, datetime.now().isoformat(), match_id))
    conn.commit()
    
    # Create result embed
    embed = discord.Embed(
        title="🏆 MATCH COMPLETED!",
        description=f"Match #{match_id} has ended!",
        color=discord.Color.green()
    )
    
    winner_mentions = ' '.join([p['user'].mention for p in winning_team])
    loser_mentions = ' '.join([p['user'].mention for p in losing_team])
    
    embed.add_field(name="🎉 Winners", value=f"{winner_mentions}\n+{mmr_changes['winners']} MMR", inline=True)
    embed.add_field(name="💔 Losers", value=f"{loser_mentions}\n{mmr_changes['losers']} MMR", inline=True)
    
    await ctx.send(embed=embed)
    
    # Remove match from active matches
    del active_matches[match_id]

def calculate_mmr_changes(winning_team, losing_team):
    """Calculate MMR changes based on team averages"""
    avg_winner_mmr = sum(p['mmr'] for p in winning_team) / len(winning_team)
    avg_loser_mmr = sum(p['mmr'] for p in losing_team) / len(losing_team)
    
    # Basic MMR calculation (can be refined)
    base_change = 25
    mmr_diff = avg_winner_mmr - avg_loser_mmr
    
    if mmr_diff > 0:  # Favorites won
        winner_gain = max(10, base_change - mmr_diff // 10)
        loser_loss = -winner_gain
    else:  # Underdogs won
        winner_gain = min(40, base_change + abs(mmr_diff) // 10)
        loser_loss = -winner_gain
    
    return {'winners': winner_gain, 'losers': loser_loss}

@bot.command(name='cancel')
async def cancel_match(ctx):
    """Cancel an active match"""
    # Check if command is used in correct channel
    if not is_queue_channel(ctx):
        await ctx.send(f"❌ Please use match commands in #{QUEUE_CHANNEL_NAME} channel!")
        return
    
    # Find active match in this channel
    match_id = None
    for mid, match_data in active_matches.items():
        if match_data['channel_id'] == str(ctx.channel.id):
            match_id = mid
            break
    
    if not match_id:
        await ctx.send("❌ No active match found in this channel!")
        return
    
    # Check if user is part of the match
    user_id = str(ctx.author.id)
    if user_id not in active_matches[match_id]['players']:
        await ctx.send("❌ You can only cancel matches you're participating in!")
        return
    
    # Remove match and return players to queue
    match_data = active_matches[match_id]
    all_players = match_data['team1'] + match_data['team2']
    
    # Add players back to queue
    for player in all_players:
        player_queue.append(player)
    
    # Delete from database
    c.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
    conn.commit()
    
    # Remove from active matches
    del active_matches[match_id]
    
    embed = discord.Embed(
        title="❌ Match Cancelled",
        description=f"Match #{match_id} has been cancelled. Players returned to queue.",
        color=discord.Color.red()
    )
    
    await ctx.send(embed=embed)

# Admin setup command
@bot.command(name='setup')
@commands.has_permissions(manage_channels=True)
async def setup_channel(ctx):
    """Create the dedicated 2v2 queue channel (Admin only)"""
    # Check if channel already exists
    existing_channel = discord.utils.get(ctx.guild.channels, name=QUEUE_CHANNEL_NAME)
    if existing_channel:
        embed = discord.Embed(
            title="✅ Channel Already Exists",
            description=f"The #{QUEUE_CHANNEL_NAME} channel already exists!",
            color=discord.Color.orange()
        )
        embed.add_field(name="Channel", value=existing_channel.mention, inline=True)
        await ctx.send(embed=embed)
        return
    
    # Create the channel
    try:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                use_external_emojis=False,
                add_reactions=True
            ),
            ctx.guild.me: discord.PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                manage_messages=True,
                embed_links=True
            )
        }
        
        channel = await ctx.guild.create_text_channel(
            name=QUEUE_CHANNEL_NAME,
            topic="🎮 2v2 Queue System - Use /queue to join matches!",
            overwrites=overwrites
        )
        
        # Send welcome message to new channel
        embed = discord.Embed(
            title="🏆 2v2 Queue System Setup Complete!",
            description=f"Welcome to the dedicated 2v2 queue channel!",
            color=discord.Color.gold()
        )
        embed.add_field(name="How to Use", 
                       value="`/queue` - Join the 2v2 queue\n`/leave` - Leave the queue\n`/status` - Check queue status", 
                       inline=False)
        embed.add_field(name="Match Commands", 
                       value="`/win 1` or `/win 2` - Report winning team\n`/cancel` - Cancel active match", 
                       inline=False)
        embed.add_field(name="Other Commands", 
                       value="`/rank` - Your stats\n`/top` - Leaderboard\n`/help` - All commands", 
                       inline=False)
        embed.set_footer(text="Queue system is now active! 4 players needed to start a match.")
        
        await channel.send(embed=embed)
        
        # Confirmation message
        setup_embed = discord.Embed(
            title="✅ Setup Complete!",
            description=f"Created #{QUEUE_CHANNEL_NAME} channel successfully!",
            color=discord.Color.green()
        )
        setup_embed.add_field(name="Channel Created", value=channel.mention, inline=True)
        setup_embed.add_field(name="Queue Commands", value="Only work in this channel", inline=True)
        await ctx.send(embed=setup_embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create channels!")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Error creating channel: {e}")

@setup_channel.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need 'Manage Channels' permission to use this command!")

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `/help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use `/help` for command usage.")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

# Run the bot
if __name__ == "__main__":
    print("Starting HeatSeeker Bot...")
    print("Make sure to set your bot token!")
    print("Available commands: /rank, /top, /stats, /help, /queue, /leave, /status, /win, /cancel")
    
    # Replace with your actual bot token
    bot.run("YOUR_BOT_TOKEN_HERE")