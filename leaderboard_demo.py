#!/usr/bin/env python3
"""
Paginated Leaderboard Demo - Shows the new empty leaderboard that only displays active players
"""

import sqlite3
from datetime import datetime

def setup_demo_database():
    """Create a demo database with mixed player data"""
    conn = sqlite3.connect("demo_players.db")
    c = conn.cursor()
    
    # Create tables
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        mmr INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Clear existing data
    c.execute("DELETE FROM players")
    
    # Add players with NO games played (these should NOT appear in leaderboard)
    inactive_players = [
        ("001", "NewPlayer1", 1000, 0, 0),
        ("002", "NewPlayer2", 1000, 0, 0),
        ("003", "NewPlayer3", 1000, 0, 0),
        ("004", "NewPlayer4", 1000, 0, 0),
        ("005", "NewPlayer5", 1000, 0, 0),
    ]
    
    for player_id, username, mmr, wins, losses in inactive_players:
        c.execute("INSERT INTO players (id, username, mmr, wins, losses) VALUES (?, ?, ?, ?, ?)",
                  (player_id, username, mmr, wins, losses))
    
    # Add players with games played (these SHOULD appear in leaderboard)
    active_players = [
        ("101", "ChampionPlayer", 1450, 12, 3),
        ("102", "SkillMaster", 1380, 10, 5),
        ("103", "ProGamer", 1320, 8, 6),
        ("104", "RankedClimber", 1280, 7, 7),
        ("105", "CompetitivePlayer", 1250, 6, 8),
        ("106", "TournamentWinner", 1220, 5, 9),
        ("107", "LeaguePlayer", 1180, 4, 10),
        ("108", "RankedPlayer", 1150, 3, 11),
        ("109", "MatchPlayer", 1120, 2, 12),
        ("110", "GamePlayer", 1100, 1, 13),
        ("111", "ActivePlayer", 1080, 1, 14),
        ("112", "ParticipantPlayer", 1060, 0, 15),  # Lost all games but still active
        ("113", "FighterPlayer", 1040, 2, 16),
        ("114", "BattlePlayer", 1020, 1, 17),
        ("115", "WarriorPlayer", 1000, 0, 18),  # Lost all games but still active
    ]
    
    for player_id, username, mmr, wins, losses in active_players:
        c.execute("INSERT INTO players (id, username, mmr, wins, losses) VALUES (?, ?, ?, ?, ?)",
                  (player_id, username, mmr, wins, losses))
    
    conn.commit()
    conn.close()
    
    print("✅ Demo database created with:")
    print(f"   • {len(inactive_players)} inactive players (0 wins, 0 losses)")
    print(f"   • {len(active_players)} active players (participated in matches)")
    print()

def show_old_leaderboard():
    """Show what the old leaderboard would look like (includes inactive players)"""
    conn = sqlite3.connect("demo_players.db")
    c = conn.cursor()
    
    c.execute("SELECT username, mmr, wins, losses FROM players ORDER BY mmr DESC LIMIT 10")
    top_players = c.fetchall()
    conn.close()
    
    print("❌ OLD LEADERBOARD (includes inactive players):")
    print("=" * 60)
    
    for i, (username, mmr, wins, losses) in enumerate(top_players):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        print(f"{medal} {username} - {mmr} MMR")
        print(f"    W: {wins} | L: {losses} | WR: {win_rate:.1f}%")
        
        if total_games == 0:
            print("    ⚠️  NEVER PLAYED A MATCH")
        print()

def show_new_leaderboard():
    """Show what the new leaderboard looks like (only active players)"""
    conn = sqlite3.connect("demo_players.db")
    c = conn.cursor()
    
    # Get only players who have played at least one match
    c.execute("""
        SELECT username, mmr, wins, losses 
        FROM players 
        WHERE wins > 0 OR losses > 0 
        ORDER BY mmr DESC 
        LIMIT 10
    """)
    
    top_players = c.fetchall()
    
    # Get total count for pagination info
    c.execute("SELECT COUNT(*) FROM players WHERE wins > 0 OR losses > 0")
    total_active_players = c.fetchone()[0]
    total_pages = (total_active_players + 9) // 10
    
    conn.close()
    
    print("✅ NEW LEADERBOARD (active players only):")
    print("=" * 60)
    print(f"🏆 HeatSeeker Leaderboard")
    print(f"Active Players Only (Page 1/{total_pages})")
    print()
    
    if top_players:
        for i, (username, mmr, wins, losses) in enumerate(top_players):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            print(f"{medal} {username} - {mmr} MMR")
            print(f"     W: {wins} | L: {losses} | WR: {win_rate:.1f}%")
            print()
        
        print(f"Showing {len(top_players)} players • Only players who have played matches are shown")
        print()
        
        if total_active_players > 10:
            print("📄 PAGINATION AVAILABLE:")
            print("• Use ◀️ Previous and ▶️ Next buttons to navigate")
            print("• 10 players per page")
            print(f"• Total {total_active_players} active players across {total_pages} pages")
    else:
        print("**No active players found!**")
        print()
        print("Play some matches to appear on the leaderboard.")
        print("Use `/queue` to join the 2v2 queue and start playing!")
    
    print()

def show_pagination_demo():
    """Demonstrate pagination with multiple pages"""
    conn = sqlite3.connect("demo_players.db")
    c = conn.cursor()
    
    # Get total active players
    c.execute("SELECT COUNT(*) FROM players WHERE wins > 0 OR losses > 0")
    total_active_players = c.fetchone()[0]
    total_pages = (total_active_players + 9) // 10
    
    print("📄 PAGINATION DEMONSTRATION:")
    print("=" * 60)
    
    for page in range(1, total_pages + 1):
        offset = (page - 1) * 10
        c.execute("""
            SELECT username, mmr, wins, losses 
            FROM players 
            WHERE wins > 0 OR losses > 0 
            ORDER BY mmr DESC 
            LIMIT 10 OFFSET ?
        """, (offset,))
        
        page_players = c.fetchall()
        
        print(f"🏆 HeatSeeker Leaderboard (Page {page}/{total_pages})")
        print("-" * 50)
        
        for i, (username, mmr, wins, losses) in enumerate(page_players):
            rank = offset + i + 1
            
            # Special medals for top 3 overall
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"**{rank}.**"
            
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            print(f"{medal} {username} - {mmr} MMR")
            print(f"     W: {wins} | L: {losses} | WR: {win_rate:.1f}%")
        
        print(f"\nShowing {len(page_players)} players on page {page}")
        print()
    
    conn.close()

def main():
    """Main demonstration"""
    print("🎮 HEATSEEKER LEADERBOARD SYSTEM DEMO")
    print("=" * 70)
    print("This demo shows the new paginated leaderboard that only displays")
    print("players who have participated in matches (won or lost at least one game)")
    print()
    
    # Setup demo database
    setup_demo_database()
    
    # Show old vs new leaderboard
    show_old_leaderboard()
    show_new_leaderboard()
    
    # Show pagination demo
    show_pagination_demo()
    
    print("=" * 70)
    print("🔧 KEY FEATURES:")
    print("=" * 70)
    print("✅ **Empty Until Active:** Leaderboard is empty until players play matches")
    print("✅ **Active Players Only:** Only shows players with wins > 0 OR losses > 0")
    print("✅ **Paginated Display:** 10 players per page with navigation buttons")
    print("✅ **Proper Ranking:** Medals (🥇🥈🥉) for top 3 overall, not just per page")
    print("✅ **Navigation Buttons:** ◀️ Previous and ▶️ Next for easy browsing")
    print("✅ **Page Information:** Shows current page and total pages")
    print("✅ **Player Count:** Shows how many active players are displayed")
    print("✅ **Motivational Empty State:** Encourages players to join queue")
    print()
    
    print("🎯 **DISCORD USAGE:**")
    print("• Use `/top` to view the leaderboard")
    print("• Click ◀️ Previous or ▶️ Next to navigate pages")
    print("• Only players who have played matches appear")
    print("• Fresh database shows empty leaderboard with helpful message")
    print()
    
    print("💡 **BENEFITS:**")
    print("• No clutter from inactive players")
    print("• Clear progression system")
    print("• Encourages participation in matches")
    print("• Professional paginated interface")
    print("• Scalable to thousands of players")

if __name__ == "__main__":
    main()