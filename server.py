from fastmcp import FastMCP
from app import GameAnalyticsApp

# MCP Server instance
mcp = FastMCP("Gaming Trend Analytics")

# App instance
app = GameAnalyticsApp()

# MCP Tools

@mcp.tool()
async def get_steam_trending_games() -> dict:
    """Get real trending games from Steam platform with live data from multiple sources."""
    return await app.get_steam_trending_games()

@mcp.tool()
async def get_steam_top_sellers() -> dict:
    """Get real top selling games from Steam platform with live sales data."""
    return await app.get_steam_top_sellers()

@mcp.tool()
async def get_steam_most_played() -> dict:
    """Get real-time most played games from Steam with live player statistics from SteamCharts."""
    return await app.get_steam_most_played()

@mcp.tool()
async def get_epic_free_games() -> dict:
    """Get current and upcoming free games from Epic Games Store with real promotion data."""
    return await app.get_epic_free_games()

@mcp.tool()
async def get_epic_trending_games() -> dict:
    """Get trending games from Epic Games Store."""
    return await app.get_epic_trending_games()

@mcp.tool()
async def get_all_trending_games() -> dict:
    """Get comprehensive real-time gaming data from all platforms (Steam and Epic Games)."""
    return await app.get_all_trending_games()

@mcp.tool()
async def get_api_health() -> dict:
    """Check the health status of the Gaming Trend Analytics API."""
    return app.get_api_health()

if __name__ == "__main__":
    # STDIO modu için (transport ve port belirtilmez)
    mcp.run(transport="stdio")