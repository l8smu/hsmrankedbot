#!/usr/bin/env python3
"""
Game Log System Demo - Shows the new comprehensive game log and modification system
"""

import sqlite3
import json
from datetime import datetime

def main():
    """Demonstrate the new game log system"""
    print("📋 GAME LOG SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    print("1. 🔍 VIEWING COMPLETE GAME HISTORY")
    print("-" * 40)
    
    # Get all matches from database
    c.execute("""
        SELECT match_id, team1_players, team2_players, winner, created_at, ended_at, 
               admin_modified, cancelled
        FROM matches 
        ORDER BY match_id DESC
    """)
    all_matches = c.fetchall()
    
    print(f"Found {len(all_matches)} total matches in database:")
    
    if not all_matches:
        print("❌ No matches found - game log would show empty state")
        print("Players need to use /queue to create matches first")
        return
    
    # Process each match
    for i, match in enumerate(all_matches, 1):
        match_id, team1_ids, team2_ids, winner, created_at, ended_at, admin_modified, cancelled = match
        
        # Get team names
        team1_names = []
        team2_names = []
        
        if team1_ids:
            for player_id in team1_ids.split(','):
                c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
                result = c.fetchone()
                if result:
                    team1_names.append(result[0])
        
        if team2_ids:
            for player_id in team2_ids.split(','):
                c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
                result = c.fetchone()
                if result:
                    team2_names.append(result[0])
        
        # Status indicators
        status = "🔴 Active"
        if cancelled:
            status = "🚫 Cancelled"
        elif winner == 1:
            status = "🏆 Team 1 Won"
        elif winner == 2:
            status = "🏆 Team 2 Won"
        elif winner == 0:
            status = "🤝 Tie"
        
        if admin_modified:
            status += " (Admin Modified)"
        
        print(f"\n  Match #{match_id}: {status}")
        print(f"    Team 1: {', '.join(team1_names)}")
        print(f"    Team 2: {', '.join(team2_names)}")
        print(f"    Created: {created_at[:19] if created_at else 'N/A'}")
        if ended_at:
            print(f"    Ended: {ended_at[:19]}")
    
    print("\n2. 📊 MATCH STATISTICS SUMMARY")
    print("-" * 40)
    
    completed_matches = [m for m in all_matches if m[3] is not None]
    active_matches_count = len(all_matches) - len(completed_matches)
    cancelled_matches = [m for m in all_matches if m[7] == 1]
    
    team1_wins = len([m for m in completed_matches if m[3] == 1])
    team2_wins = len([m for m in completed_matches if m[3] == 2])
    ties = len([m for m in completed_matches if m[3] == 0])
    admin_modified = len([m for m in all_matches if m[6] == 1])
    
    print(f"Total Matches: {len(all_matches)}")
    print(f"Completed: {len(completed_matches)}")
    print(f"Active: {active_matches_count}")
    print(f"Cancelled: {len(cancelled_matches)}")
    print(f"Team 1 Wins: {team1_wins}")
    print(f"Team 2 Wins: {team2_wins}")
    print(f"Ties: {ties}")
    print(f"Admin Modified: {admin_modified}")
    
    print("\n3. 🔍 DETAILED MATCH VIEW EXAMPLE")
    print("-" * 40)
    
    # Show detailed view of first match
    if all_matches:
        match_data = all_matches[0]  # Most recent match
        match_id, team1_ids, team2_ids, winner, created_at, ended_at, admin_modified, cancelled = match_data
        
        print(f"Detailed view of Match #{match_id}:")
        
        # Get team player details
        team1_details = []
        team2_details = []
        
        if team1_ids:
            for player_id in team1_ids.split(','):
                c.execute("SELECT username, mmr, wins, losses FROM players WHERE id = ?", (player_id,))
                result = c.fetchone()
                if result:
                    username, mmr, wins, losses = result
                    team1_details.append({
                        'id': player_id,
                        'username': username,
                        'mmr': mmr,
                        'wins': wins,
                        'losses': losses
                    })
        
        if team2_ids:
            for player_id in team2_ids.split(','):
                c.execute("SELECT username, mmr, wins, losses FROM players WHERE id = ?", (player_id,))
                result = c.fetchone()
                if result:
                    username, mmr, wins, losses = result
                    team2_details.append({
                        'id': player_id,
                        'username': username,
                        'mmr': mmr,
                        'wins': wins,
                        'losses': losses
                    })
        
        # Status
        status = "🔴 Active"
        if cancelled:
            status = "🚫 Cancelled"
        elif winner == 1:
            status = "🏆 Team 1 Victory"
        elif winner == 2:
            status = "🏆 Team 2 Victory"
        elif winner == 0:
            status = "🤝 Tie Game"
        
        if admin_modified:
            status += " (Admin Modified)"
        
        print(f"  Status: {status}")
        print(f"  Match ID: #{match_id}")
        print(f"  Created: {created_at[:19] if created_at else 'N/A'}")
        if ended_at:
            print(f"  Ended: {ended_at[:19]}")
        
        # Team 1 details
        if team1_details:
            team1_avg_mmr = sum(p['mmr'] for p in team1_details) / len(team1_details)
            print(f"\n  🔴 Team 1 (Avg MMR: {team1_avg_mmr:.0f}):")
            for player in team1_details:
                total_games = player['wins'] + player['losses']
                winrate = (player['wins'] / total_games * 100) if total_games > 0 else 0
                print(f"    {player['username']}")
                print(f"    MMR: {player['mmr']} | W/L: {player['wins']}/{player['losses']} ({winrate:.1f}%)")
        
        # Team 2 details
        if team2_details:
            team2_avg_mmr = sum(p['mmr'] for p in team2_details) / len(team2_details)
            print(f"\n  🔵 Team 2 (Avg MMR: {team2_avg_mmr:.0f}):")
            for player in team2_details:
                total_games = player['wins'] + player['losses']
                winrate = (player['wins'] / total_games * 100) if total_games > 0 else 0
                print(f"    {player['username']}")
                print(f"    MMR: {player['mmr']} | W/L: {player['wins']}/{player['losses']} ({winrate:.1f}%)")
    
    print("\n4. 📝 PLAYER EDITOR SYSTEM")
    print("-" * 40)
    
    # Show player editor functionality
    c.execute("SELECT id, username, mmr, wins, losses FROM players ORDER BY mmr DESC")
    players = c.fetchall()
    
    print(f"Player Editor would show {len(players)} players:")
    
    for i, player in enumerate(players[:10], 1):  # Show top 10
        player_id, username, mmr, wins, losses = player
        total_games = wins + losses
        winrate = (wins / total_games * 100) if total_games > 0 else 0
        
        print(f"  {i}. {username}")
        print(f"     MMR: {mmr} | W/L: {wins}/{losses} ({winrate:.1f}%)")
        print(f"     Available actions: Set MMR, Set Wins, Set Losses, Reset Stats")
    
    print("\n5. 🎮 MODIFICATION ACTIONS AVAILABLE")
    print("-" * 40)
    
    print("Match Modifications:")
    print("  🏆 Set Team 1 Winner - Update match winner to Team 1")
    print("  🏆 Set Team 2 Winner - Update match winner to Team 2")
    print("  🤝 Set Tie - Mark match as tie (no MMR changes)")
    print("  🚫 Cancel Match - Cancel match entirely")
    print("  📝 Edit Players - Access player modification system")
    
    print("\nPlayer Modifications:")
    print("  ⚡ Set MMR - Change player's MMR value (0-5000)")
    print("  🏆 Set Wins - Change player's win count")
    print("  💔 Set Losses - Change player's loss count")
    print("  🔄 Reset Stats - Reset to default (1000 MMR, 0-0 W/L)")
    
    print("\n6. 🛡️ ADMIN FEATURES")
    print("-" * 40)
    
    print("Security Features:")
    print("  ✅ Admin-only access (@app_commands.default_permissions(administrator=True))")
    print("  ✅ Comprehensive logging of all modifications")
    print("  ✅ Real-time database updates with error handling")
    print("  ✅ Input validation (MMR 0-5000, non-negative wins/losses)")
    print("  ✅ Ephemeral messages for privacy")
    print("  ✅ Auto-cleanup of active matches when modified")
    
    print("\nData Integrity:")
    print("  ✅ Database transactions with commit/rollback")
    print("  ✅ Proper foreign key handling")
    print("  ✅ Admin modification tracking")
    print("  ✅ Timestamp logging for all changes")
    
    conn.close()
    
    print("\n🎉 GAME LOG SYSTEM DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("✅ The /game_log command provides:")
    print("   • Complete match history with all details")
    print("   • Player statistics and win/loss records")
    print("   • Match modification capabilities")
    print("   • Player stat editing system")
    print("   • Admin-only access with full security")
    print("   • Real-time database updates")
    
    print("\n📊 COMMAND SUMMARY:")
    print("=" * 60)
    print("🔧 /game_log - Main command (Admin only)")
    print("   └── Match Selection Dropdown")
    print("       └── Detailed Match View")
    print("           ├── 🏆 Set Team 1 Winner")
    print("           ├── 🏆 Set Team 2 Winner")
    print("           ├── 🤝 Set Tie")
    print("           ├── 🚫 Cancel Match")
    print("           └── 📝 Edit Players")
    print("               └── Player Selection Dropdown")
    print("                   └── Player Modification Panel")
    print("                       ├── ⚡ Set MMR (Modal)")
    print("                       ├── 🏆 Set Wins (Modal)")
    print("                       ├── 💔 Set Losses (Modal)")
    print("                       └── 🔄 Reset Stats")
    
    print("\n🤖 Try running /game_log in Discord to access the full system!")

if __name__ == "__main__":
    main()