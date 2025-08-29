#!/usr/bin/env python3
"""
Admin Match Fix Demo - Shows the fix for the /admin_match command
"""

import sqlite3
import json
from datetime import datetime

def main():
    """Main demonstration of the admin match fix"""
    print("🔧 ADMIN MATCH COMMAND FIX DEMONSTRATION")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    print("1. 🔍 CHECKING DATABASE FOR ACTIVE MATCHES")
    print("-" * 40)
    
    # Check for active matches in database
    c.execute("SELECT match_id, team1_players, team2_players, created_at, channel_id FROM matches WHERE winner IS NULL OR winner = 0")
    db_matches = c.fetchall()
    
    print(f"Found {len(db_matches)} active matches in database:")
    for match in db_matches:
        print(f"  Match {match[0]}: Team1={match[1]}, Team2={match[2]}")
    
    if not db_matches:
        print("❌ No active matches found in database")
        print("The /admin_match command will show 'No active matches' message")
        return
    
    print("\n2. 🔄 SIMULATING MATCH RESTORATION ON BOT STARTUP")
    print("-" * 40)
    
    # Simulate the restore_active_matches() function
    active_matches = {}
    restored_count = 0
    
    for match_id, team1_ids, team2_ids, created_at, channel_id in db_matches:
        print(f"\nProcessing match {match_id}...")
        
        # Parse team player IDs
        team1_player_ids = team1_ids.split(',') if team1_ids else []
        team2_player_ids = team2_ids.split(',') if team2_ids else []
        
        # Get player data for each team
        team1 = []
        team2 = []
        
        for player_id in team1_player_ids:
            c.execute("SELECT username, mmr FROM players WHERE id = ?", (player_id,))
            result = c.fetchone()
            if result:
                username, mmr = result
                team1.append({'id': player_id, 'username': username, 'mmr': mmr})
        
        for player_id in team2_player_ids:
            c.execute("SELECT username, mmr FROM players WHERE id = ?", (player_id,))
            result = c.fetchone()
            if result:
                username, mmr = result
                team2.append({'id': player_id, 'username': username, 'mmr': mmr})
        
        # Only restore if we have complete team data
        if len(team1) == 2 and len(team2) == 2:
            active_matches[match_id] = {
                'team1': team1,
                'team2': team2,
                'players': team1_player_ids + team2_player_ids,
                'channel_id': channel_id,
                'hsm_number': match_id,
                'distribution_method': 'Restored',
                'created_at': created_at
            }
            restored_count += 1
            
            team1_names = [p['username'] for p in team1]
            team2_names = [p['username'] for p in team2]
            print(f"  ✅ Restored match {match_id}: HSM{match_id}")
            print(f"     Team 1: {', '.join(team1_names)}")
            print(f"     Team 2: {', '.join(team2_names)}")
        else:
            print(f"  ❌ Incomplete team data - skipping")
    
    print(f"\n✅ Successfully restored {restored_count} active matches!")
    
    print("\n3. 🎮 SIMULATING /admin_match COMMAND")
    print("-" * 40)
    
    if not active_matches:
        print("❌ No active matches - command would show 'No active matches' message")
        return
    
    # Simulate the admin_match command logic
    print(f"Admin match command would show:")
    print(f"  Title: Admin Match Control Panel")
    print(f"  Description: {len(active_matches)} active match(es) found")
    
    # Create dropdown options
    options = []
    for match_id, match_data in active_matches.items():
        team1_names = [p['username'] for p in match_data['team1']]
        team2_names = [p['username'] for p in match_data['team2']]
        hsm_number = match_data.get('hsm_number', 'N/A')
        
        description = f"HSM{hsm_number}: {', '.join(team1_names)} vs {', '.join(team2_names)}"
        option = {
            'label': f"Match #{match_id}",
            'description': description[:100],  # Discord limit
            'value': str(match_id)
        }
        options.append(option)
        
        print(f"  Dropdown Option: {option['label']} - {option['description']}")
    
    print("\n4. 🎯 SIMULATING MATCH SELECTION")
    print("-" * 40)
    
    # Test selecting the first match
    first_match_id = list(active_matches.keys())[0]
    match_data = active_matches[first_match_id]
    
    team1_names = [p['username'] for p in match_data['team1']]
    team2_names = [p['username'] for p in match_data['team2']]
    
    team1_mmr = sum(p['mmr'] for p in match_data['team1']) / len(match_data['team1'])
    team2_mmr = sum(p['mmr'] for p in match_data['team2']) / len(match_data['team2'])
    
    print(f"Selected Match #{first_match_id} would show:")
    print(f"  Title: Admin Control - Match #{first_match_id}")
    print(f"  HSM Number: HSM{match_data['hsm_number']}")
    print(f"  Team 1: {', '.join(team1_names)} (Avg MMR: {team1_mmr:.0f})")
    print(f"  Team 2: {', '.join(team2_names)} (Avg MMR: {team2_mmr:.0f})")
    print(f"  Available Actions:")
    print(f"    🏆 Team 1 Wins")
    print(f"    🏆 Team 2 Wins")
    print(f"    🤝 Tie/Draw")
    print(f"    🚫 Cancel Match")
    
    print("\n5. 🏆 SIMULATING ADMIN ACTION (Team 1 Wins)")
    print("-" * 40)
    
    winning_team = match_data['team1']
    losing_team = match_data['team2']
    
    # Calculate MMR changes
    team1_avg = sum(p['mmr'] for p in winning_team) / len(winning_team)
    team2_avg = sum(p['mmr'] for p in losing_team) / len(losing_team)
    
    mmr_diff = team2_avg - team1_avg
    base_change = 25
    mmr_change = min(50, max(10, int(base_change + mmr_diff * 0.04)))
    
    print(f"Action: Team 1 Wins")
    print(f"Winner: {', '.join([p['username'] for p in winning_team])}")
    print(f"Loser: {', '.join([p['username'] for p in losing_team])}")
    print(f"MMR Changes: +{mmr_change} / -{mmr_change}")
    
    # Show what would happen
    print(f"\nDatabase Updates:")
    print(f"  UPDATE matches SET winner = 1, ended_at = '{datetime.now().isoformat()}', admin_modified = 1 WHERE match_id = {first_match_id}")
    
    for player in winning_team:
        print(f"  UPDATE players SET wins = wins + 1, mmr = mmr + {mmr_change} WHERE id = '{player['id']}'")
    
    for player in losing_team:
        print(f"  UPDATE players SET losses = losses + 1, mmr = mmr + {-mmr_change} WHERE id = '{player['id']}'")
    
    print(f"\nOther Actions:")
    print(f"  ✅ Send DM notifications to all 4 players")
    print(f"  ✅ Update admin panel with results")
    print(f"  ✅ Clean up match channels")
    print(f"  ✅ Remove match from active_matches dict")
    
    conn.close()
    
    print("\n🎉 ADMIN MATCH COMMAND FIX COMPLETE!")
    print("=" * 60)
    print("✅ The /admin_match command should now work properly!")
    print("✅ Key fixes implemented:")
    print("   • Added restore_active_matches() function")
    print("   • Fixed database query column order")
    print("   • Added function call to on_ready() event")
    print("   • Active matches are now restored on bot startup")
    print("   • Admin command can find and manage active matches")
    print("\n🤖 Try running /admin_match in Discord now!")

if __name__ == "__main__":
    main()