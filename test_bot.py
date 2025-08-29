#!/usr/bin/env python3
"""
Test Discord Bot - Run this to test the bot functionality locally
"""

import sqlite3
import os

# Create and setup database
def setup_database():
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        username TEXT,
        mmr INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )''')
    
    # Add sample data
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
    conn.close()

def show_top_players():
    """Show top 10 players"""
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    c.execute("SELECT username, mmr, wins, losses FROM players ORDER BY mmr DESC LIMIT 10")
    top_players = c.fetchall()
    conn.close()
    
    print("🏆 TOP 10 PLAYERS LEADERBOARD")
    print("=" * 50)
    
    for i, (username, mmr, wins, losses) in enumerate(top_players):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        print(f"{medal} {username} - {mmr} MMR")
        print(f"    Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
        print()

def show_player_rank(user_id="123456789", username="TestPlayer"):
    """Show rank for a specific player"""
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    # Add player if not exists
    c.execute("SELECT * FROM players WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO players (id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    
    # Get player stats
    c.execute("SELECT username, mmr, wins, losses FROM players WHERE id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        username, mmr, wins, losses = result
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        # Get rank position
        c.execute("SELECT COUNT(*) FROM players WHERE mmr > ?", (mmr,))
        rank_position = c.fetchone()[0] + 1
        
        print(f"📊 {username}'s RANK & STATISTICS")
        print("=" * 40)
        print(f"MMR: {mmr}")
        print(f"Rank: #{rank_position}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Total Games: {total_games}")
        print(f"Win Rate: {win_rate:.1f}%")
        print()
    
    conn.close()

def main():
    """Main function to demonstrate bot commands"""
    print("🤖 HEATSEEKER BOT - COMMAND DEMONSTRATION")
    print("=" * 60)
    
    # Setup database
    setup_database()
    print("✅ Database setup complete with sample data")
    print()
    
    # Show available commands
    print("AVAILABLE COMMANDS:")
    print("/rank - Show your MMR and statistics")
    print("/top - Display top 10 players")
    print("/stats - Show detailed player statistics")
    print("/help - Show available commands")
    print()
    
    # Demonstrate /rank command
    print("DEMONSTRATING /rank COMMAND:")
    print("-" * 30)
    show_player_rank()
    
    # Demonstrate /top command
    print("DEMONSTRATING /top COMMAND:")
    print("-" * 30)
    show_top_players()
    
    print("=" * 60)
    print("🎮 TO USE IN DISCORD:")
    print("1. Get your bot token from Discord Developer Portal")
    print("2. Replace 'YOUR_BOT_TOKEN_HERE' in discord_bot.py")
    print("3. Run: python3 discord_bot.py")
    print("4. Add bot to your server and use commands!")
    print()
    print("Then you can use /rank and /top in your Discord server!")

if __name__ == "__main__":
    main()