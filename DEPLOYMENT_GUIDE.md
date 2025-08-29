# HeatSeeker Discord Bot - Deployment Guide

## Deployment Issue Resolution

This guide addresses the deployment failures and provides solutions for both Autoscale and Reserved VM Background Worker deployments.

## Issues Fixed

### 1. ❌ Undefined Variable Issue
**Problem**: The run command referenced an undefined variable `$file` (specifically `python heatseeker_bot.py`)
**Solution**: ✅ Fixed workflow to use correct file `python main.py`

### 2. ❌ Missing HTTP Health Check
**Problem**: Autoscale deployments require HTTP health check endpoints
**Solution**: ✅ Added Flask HTTP server with health check endpoints at `/` and `/health`

### 3. ❌ Background Worker Compatibility
**Problem**: Discord bots don't naturally expose HTTP servers
**Solution**: ✅ Created dual-mode architecture supporting both deployment types

## Deployment Options

### Option 1: Autoscale Deployment (Recommended)

**Best for**: Variable usage patterns, cost-effective scaling

**Configuration**:
- **Entry Point**: `python app.py` or `python main.py`
- **Deployment Type**: Autoscale (Cloud Run)
- **Health Check**: HTTP endpoints at `/` and `/health`
- **Port**: Automatically configured via PORT environment variable

**Pros**:
- Automatic scaling based on usage
- Pay-per-use pricing model
- Health monitoring built-in
- Handles traffic spikes automatically

**Cons**:
- May have cold start delays
- HTTP overhead for Discord-only functionality

### Option 2: Reserved VM Background Worker

**Best for**: Consistent high usage, always-on requirements

**Configuration**:
- **Entry Point**: `python main.py`
- **Deployment Type**: Reserved VM Background Worker
- **Health Check**: Not required (optional HTTP server still runs)
- **Always-On**: Dedicated VM instance

**Pros**:
- No cold starts
- Dedicated resources
- Predictable performance
- Simple Discord bot architecture

**Cons**:
- Fixed monthly cost
- Manual scaling required
- No automatic health monitoring

## Environment Variables

### Required
- `DISCORD_TOKEN`: Your Discord bot token

### Optional
- `PORT`: HTTP server port (default: 8080, automatically set by Autoscale)

## Health Check Endpoints

### GET /
Returns bot health status and service information:
```json
{
  "status": "healthy",
  "service": "HeatSeeker Discord Bot",
  "bot_ready": true,
  "timestamp": "2025-07-22T08:08:48.775910"
}
```

### GET /health
Alias for the root endpoint with identical response format.

## File Structure

- `main.py`: Primary Discord bot with integrated HTTP server
- `app.py`: Alternative entry point optimized for HTTP deployments
- `test_health_check.py`: Health endpoint verification script
- `hsm_players.db`: SQLite database (created automatically)

## Testing Health Checks

Run the test script to verify health endpoints:
```bash
python test_health_check.py
```

Expected output:
```
✅ Health check endpoints working correctly!
🚢 Bot is ready for Autoscale deployment!
```

## Deployment Steps

### For Autoscale:
1. Set `DISCORD_TOKEN` environment variable
2. Choose `python app.py` as run command
3. Set deployment type to Autoscale
4. Deploy - health checks will automatically work

### For Reserved VM:
1. Set `DISCORD_TOKEN` environment variable
2. Choose `python main.py` as run command
3. Set deployment type to Reserved VM Background Worker
4. Deploy - HTTP server is optional but will still run

## Troubleshooting

### Health Check Failures
- Verify Flask server starts: Check for "HTTP health check server started" in logs
- Test endpoints locally: Run `python test_health_check.py`
- Check port configuration: Ensure PORT environment variable is set correctly

### Discord Bot Issues
- Verify token: Check DISCORD_TOKEN environment variable
- Check permissions: Ensure bot has necessary Discord permissions
- Review logs: Look for "Starting HeatSeeker Discord Bot" message

### Database Issues
- SQLite file permissions: Ensure write access to directory
- Database corruption: Delete `hsm_players.db` to reset (data will be lost)

## Architecture Benefits

1. **Dual Compatibility**: Works with both deployment types
2. **Zero Configuration**: Automatic health endpoint setup
3. **Preserved Functionality**: All Discord bot features maintained
4. **Cost Optimization**: Choose deployment type based on usage patterns
5. **Monitoring Ready**: Built-in health status reporting

## Support

For deployment issues:
1. Check this guide first
2. Review Replit deployment logs
3. Test health endpoints locally
4. Verify environment variables are set correctly