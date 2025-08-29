# HeatSeeker Discord Bot

## Overview

HeatSeeker Discord Bot is a comprehensive Discord bot for queue management and player ranking in HeatSeeker, built with Python and Discord.py. It provides an advanced leaderboard system with MMR tracking, player placement mechanics, real-time player statistics, and 2v2 match management with automatic team balancing. The bot also includes HTTP health check endpoints for Autoscale deployment compatibility.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The HeatSeeker Discord Bot follows a modern Python architecture with deployment compatibility:

-   **Core Bot**: Python 3.11 with Discord.py for Discord integration, utilizing slash commands for all functionalities. Features include MMR tracking (8-tier system with placement matches), a 2v2 queue system, and match management with automated team balancing (random or captain draft). Includes automated DM notifications and an admin control panel for match management and data modification.
-   **Admin Commands**: All slash commands restricted to administrator permissions only (`@app_commands.default_permissions(administrator=True)`). Includes database management commands (`/reset_database`, `/reset_placements`) and queue management tools.
-   **UI/UX**: Professional, button-based queue system, automated voice and text channels per match, professional embeds with team info and statistics, and a paginated leaderboard with interactive navigation.
-   **Database**: SQLite for persistent player data, match history, and placement match tracking. Default starting MMR: 1300 points.
-   **Web Server**: Flask HTTP server for health checks, enabling Autoscale deployment compatibility. Provides `/` and `/health` endpoints.
-   **Threading**: Multi-threaded architecture running the Discord bot and web server concurrently.
-   **Command Sync**: Automatic command synchronization on bot startup with manual sync command available.
-   **Logging**: Comprehensive logging system with categorized event logging (QUEUE, MATCH, ADMIN, PLAYER) and an audit trail for admin actions.

## External Dependencies

-   **Discord.py**: Python library for interacting with the Discord API.
-   **Flask**: Python web framework for the HTTP health check server.
-   **SQLite**: Embedded database used for persistent data storage (`hsm_players.db`).