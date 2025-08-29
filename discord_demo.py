#!/usr/bin/env python3
"""
Discord Bot Demo - Shows what the /rank and /top commands would display
"""

# Sample player data that would be in the database
players_data = [
    {'id': '123456789', 'username': 'PlayerOne', 'mmr': 1200, 'wins': 15, 'losses': 5},
    {'id': '987654321', 'username': 'TopGamer', 'mmr': 1450, 'wins': 25, 'losses': 8},
    {'id': '456789123', 'username': 'SkillMaster', 'mmr': 1350, 'wins': 20, 'losses': 12},
    {'id': '789123456', 'username': 'ProPlayer', 'mmr': 1100, 'wins': 18, 'losses': 15},
    {'id': '321654987', 'username': 'GameChamp', 'mmr': 1300, 'wins': 22, 'losses': 10},
    {'id': '654321789', 'username': 'EliteGamer', 'mmr': 1500, 'wins': 30, 'losses': 5},
    {'id': '147258369', 'username': 'RankClimber', 'mmr': 1250, 'wins': 16, 'losses': 9},
    {'id': '963852741', 'username': 'CompetitivePro', 'mmr': 1400, 'wins': 28, 'losses': 7},
    {'id': '258741963', 'username': 'StrategyMaster', 'mmr': 1180, 'wins': 14, 'losses': 11},
    {'id': '741852963', 'username': 'LeaderboardKing', 'mmr': 1600, 'wins': 35, 'losses': 3}
]

def show_rank_command(user_id='123456789'):
    """Simulate the /rank command"""
    player = next((p for p in players_data if p['id'] == user_id), None)
    
    if not player:
        # Add new player with default stats
        player = {'id': user_id, 'username': 'NewPlayer', 'mmr': 1000, 'wins': 0, 'losses': 0}
    
    total_games = player['wins'] + player['losses']
    win_rate = (player['wins'] / total_games * 100) if total_games > 0 else 0
    
    print("🏆 YOUR RANK")
    print("=" * 30)
    print(f"Player: {player['username']}")
    print(f"MMR: {player['mmr']}")
    print(f"Wins: {player['wins']}")
    print(f"Losses: {player['losses']}")
    print(f"Total Games: {total_games}")
    print(f"Win Rate: {win_rate:.1f}%")
    print()

def show_top_command():
    """Simulate the /top command"""
    # Sort players by MMR descending
    top_players = sorted(players_data, key=lambda x: x['mmr'], reverse=True)[:10]
    
    print("🏆 TOP 10 PLAYERS LEADERBOARD")
    print("=" * 50)
    
    for i, player in enumerate(top_players):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        total_games = player['wins'] + player['losses']
        win_rate = (player['wins'] / total_games * 100) if total_games > 0 else 0
        
        print(f"{medal} {player['username']} - {player['mmr']} MMR")
        print(f"    W: {player['wins']} | L: {player['losses']} | WR: {win_rate:.1f}%")
        print()

def main():
    print("🤖 DISCORD BOT COMMAND DEMONSTRATION")
    print("=" * 60)
    print("This shows what you would see when using the bot commands in Discord")
    print()
    
    print("When you type /rank in Discord, you'll see:")
    print("-" * 40)
    show_rank_command()
    
    print("When you type /top in Discord, you'll see:")
    print("-" * 40)
    show_top_command()
    
    print("=" * 60)
    print("TO USE THE ACTUAL BOT IN DISCORD:")
    print("1. Create a Discord bot at https://discord.com/developers/applications")
    print("2. Get your bot token")
    print("3. Replace 'YOUR_BOT_TOKEN_HERE' in discord_bot.py")
    print("4. Run: python3 discord_bot.py")
    print("5. Add the bot to your Discord server")
    print("6. Use /rank and /top commands in your server!")
    print()
    print("The bot will automatically create your player profile")
    print("and you can start tracking your MMR and stats!")

if __name__ == "__main__":
    main()