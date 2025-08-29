# Discord Bot Setup Guide

## Quick Start

1. **Get Your Bot Token**
   - Go to https://discord.com/developers/applications
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Copy the bot token

2. **Set Up the Bot**
   - Replace `YOUR_BOT_TOKEN_HERE` in `discord_bot.py` with your actual token
   - Run the bot: `python3 discord_bot.py`

3. **Add Bot to Your Server**
   - Go to "OAuth2" > "URL Generator"
   - Select "bot" scope
   - Select permissions: Send Messages, Use Slash Commands, Read Message History
   - Use the generated URL to add the bot to your server

## Available Commands

### Player Stats
- `/rank` - Show your MMR and stats
- `/top` - Display top 10 players leaderboard
- `/stats @user` - Show stats for a specific player

### Queue System
- `/queue` - Join the 2v2 queue
- `/leave` - Leave the queue
- `/status` - Check current queue status

### Match System
- `/win 1` or `/win 2` - Report the winning team
- `/cancel` - Cancel an active match
- `/help` - Show all available commands

## Features

- **MMR Tracking**: Each player starts with 1000 MMR
- **2v2 Queue System**: Join queue and get matched with 3 other players
- **Fair Team Balancing**: Teams are balanced based on MMR
- **Automatic Match Creation**: When 4 players queue, match starts instantly
- **Win/Loss Records**: Track your game history
- **Leaderboard**: See top 10 players ranked by MMR
- **Statistics**: Detailed stats including win rate
- **Match History**: All matches are tracked in the database
- **Player Mentions**: Bot mentions all players when match starts
- **MMR Adjustments**: Win/lose MMR based on match results

## How the Queue System Works

1. **Join Queue**: Use `/queue` to join the 2v2 queue
2. **Wait for Players**: Queue needs 4 players to start a match
3. **Match Created**: Bot automatically creates balanced teams
4. **Team Assignment**: Players are mentioned and assigned to teams
5. **Play Your Match**: Play your 2v2 game outside Discord
6. **Report Results**: Use `/win 1` or `/win 2` to report winner
7. **MMR Updates**: Winners gain MMR, losers lose MMR

## Example Workflow

```
Player1: /queue
Bot: ✅ Player1 joined the 2v2 queue! (1/4 players)

Player2: /queue
Bot: ✅ Player2 joined the 2v2 queue! (2/4 players)

Player3: /queue
Bot: ✅ Player3 joined the 2v2 queue! (3/4 players)

Player4: /queue
Bot: 🏆 MATCH FOUND!
     🔴 Team 1: @Player1 @Player4
     🔵 Team 2: @Player2 @Player3
     Use /win 1 or /win 2 to report results

After the match:
Player1: /win 1
Bot: 🏆 MATCH COMPLETED!
     🎉 Winners: @Player1 @Player4 (+25 MMR)
     💔 Losers: @Player2 @Player3 (-25 MMR)
```

The bot will automatically create your player profile when you use any command for the first time.