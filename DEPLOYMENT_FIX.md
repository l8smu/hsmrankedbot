# Deployment Fix Guide

## Issue Resolution

Your deployment failed due to:
1. Undefined `$file` variable in run command
2. Discord bot not exposing HTTP endpoints for health checks

## Fixes Applied

### 1. Run Command Configuration

**For Autoscale Deployment (Recommended):**
- **Run Command**: `python app.py`
- **Deployment Type**: Autoscale
- **Port**: Automatically configured via `PORT` environment variable

**For Reserved VM Background Worker:**
- **Run Command**: `python main.py`
- **Deployment Type**: Reserved VM Background Worker
- **Port**: HTTP server runs on port 8080 (optional for this type)

### 2. Environment Variables Required

- `DISCORD_TOKEN`: Your Discord bot token (required)
- `PORT`: HTTP server port (automatically set by Autoscale, defaults to 8080)

### 3. Health Check Endpoints

Your bot now has HTTP endpoints for health checks:

- **GET /**: Returns bot health status and service information
- **GET /health**: Alternative health endpoint (same response)

Response format:
```json
{
  "status": "healthy",
  "service": "HeatSeeker Discord Bot",
  "bot_ready": true,
  "timestamp": "2025-07-25T12:00:00.000000"
}
```

## Deployment Steps

### Option 1: Autoscale (Recommended)

1. Go to your Replit deployment settings
2. Set **Run Command** to: `python app.py`
3. Set **Deployment Type** to: **Autoscale**
4. Add environment variable `DISCORD_TOKEN` with your bot token
5. Deploy

### Option 2: Reserved VM Background Worker

1. Go to your Replit deployment settings
2. Set **Run Command** to: `python main.py`
3. Set **Deployment Type** to: **Reserved VM Background Worker**
4. Add environment variable `DISCORD_TOKEN` with your bot token
5. Deploy

## Testing Health Checks

Run this to test your health endpoints locally:

```bash
python test_health_check.py
```

## Architecture

Your bot now runs with a dual architecture:
- **Discord Bot**: Handles all Discord interactions and commands
- **HTTP Server**: Provides health check endpoints for deployment compatibility
- **Threading**: Both services run concurrently in separate threads

This ensures your Discord bot works with both deployment types while maintaining all its functionality.