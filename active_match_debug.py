#!/usr/bin/env python3
"""
Active Match Debug Script - Investigate why players are still being blocked
"""

import sqlite3
import json
from datetime import datetime

def debug_active_matches():
    """Debug the active match blocking issue"""
    
    print("🔍 ACTIVE MATCH DEBUG INVESTIGATION")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    print("\n📊 DATABASE STATUS")
    print("-" * 50)
    
    # Check active matches in database
    c.execute("""
        SELECT match_id, team1_players, team2_players, winner, created_at, ended_at, cancelled
        FROM matches 
        WHERE winner IS NULL OR winner = 0
        ORDER BY match_id
    """)
    active_db_matches = c.fetchall()
    
    print(f"Active matches in database: {len(active_db_matches)}")
    for match in active_db_matches:
        match_id, team1, team2, winner, created, ended, cancelled = match
        print(f"  Match {match_id}: Team1={team1}, Team2={team2}, Winner={winner}, Cancelled={cancelled}")
    
    # Check all matches
    c.execute("SELECT match_id, team1_players, team2_players, winner, cancelled FROM matches ORDER BY match_id")
    all_matches = c.fetchall()
    
    print(f"\nAll matches in database: {len(all_matches)}")
    for match in all_matches:
        match_id, team1, team2, winner, cancelled = match
        status = "CANCELLED" if cancelled else ("ACTIVE" if winner is None or winner == 0 else "COMPLETED")
        print(f"  Match {match_id}: {status} (Winner={winner})")
    
    print("\n🔍 PLAYER ANALYSIS")
    print("-" * 50)
    
    # Get all players
    c.execute("SELECT id, username, mmr, wins, losses FROM players")
    all_players = c.fetchall()
    
    print(f"Total players: {len(all_players)}")
    for player in all_players:
        player_id, username, mmr, wins, losses = player
        
        # Check if player is in any active match
        in_active_match = False
        for match in active_db_matches:
            team1_ids = match[1].split(',') if match[1] else []
            team2_ids = match[2].split(',') if match[2] else []
            all_match_players = team1_ids + team2_ids
            
            if player_id in all_match_players:
                in_active_match = True
                print(f"  {username} (ID: {player_id}) - IN ACTIVE MATCH {match[0]}")
                break
        
        if not in_active_match:
            print(f"  {username} (ID: {player_id}) - FREE TO JOIN QUEUE")
    
    print("\n🧪 SIMULATED QUEUE JOIN TEST")
    print("-" * 50)
    
    # Simulate the exact check from the bot
    test_user_id = input("Enter your Discord user ID to test: ").strip()
    
    if test_user_id:
        # Simulate active_matches dictionary from database
        simulated_active_matches = {}
        
        for match in active_db_matches:
            match_id, team1_ids, team2_ids, winner, created_at, ended_at, cancelled = match
            
            if team1_ids and team2_ids:
                all_player_ids = team1_ids.split(',') + team2_ids.split(',')
                simulated_active_matches[match_id] = {
                    'players': all_player_ids,
                    'team1_players': team1_ids,
                    'team2_players': team2_ids,
                    'created_at': created_at
                }
        
        print(f"Simulated active_matches: {len(simulated_active_matches)} entries")
        for match_id, match_data in simulated_active_matches.items():
            print(f"  Match {match_id}: Players = {match_data['players']}")
        
        # Run the exact bot check
        is_blocked = any(test_user_id in match['players'] for match in simulated_active_matches.values())
        
        print(f"\nUser {test_user_id} queue join test:")
        print(f"  Result: {'❌ BLOCKED (in active match)' if is_blocked else '✅ ALLOWED'}")
        
        if is_blocked:
            print(f"  Found in matches:")
            for match_id, match_data in simulated_active_matches.items():
                if test_user_id in match_data['players']:
                    print(f"    - Match {match_id}")
    
    print("\n🔧 POTENTIAL SOLUTIONS")
    print("-" * 50)
    print("If players are still being blocked, try these solutions:")
    print()
    print("1. CLEAR ALL ACTIVE MATCHES:")
    print("   UPDATE matches SET winner = -1, cancelled = 1 WHERE winner IS NULL;")
    print()
    print("2. RESET SPECIFIC MATCH:")
    print("   UPDATE matches SET winner = -1, cancelled = 1 WHERE match_id = X;")
    print()
    print("3. DELETE PROBLEMATIC MATCHES:")
    print("   DELETE FROM matches WHERE winner IS NULL;")
    print()
    print("4. RESTART BOT:")
    print("   Kill and restart the bot to reload active_matches from database")
    
    print("\n📋 RECOMMENDED ACTIONS")
    print("-" * 50)
    print("Based on the investigation above:")
    print("1. Check if there are any active matches in the database")
    print("2. If yes, either complete them or cancel them")
    print("3. Restart the bot to reload the active_matches dictionary")
    print("4. Test queue joining again")
    
    conn.close()

if __name__ == "__main__":
    debug_active_matches()