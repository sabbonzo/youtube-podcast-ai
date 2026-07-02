# YouTube Podcast AI Auto-Reply

Automatically replies to YouTube comments using Claude AI. Runs on schedule via GitHub Actions.

## Features

- Automatically fetches new comments from your YouTube channel
- Generates intelligent, contextual replies using Claude AI
- Posts replies automatically to YouTube
- Runs on a schedule (every 6 hours by default)
- Tracks replied comments to avoid duplicates
- Comprehensive logging and error handling

## Setup

### 1. Prerequisites

- YouTube channel with comments
- YouTube Data API credentials (API key)
- Claude API key from Anthropic
- GitHub repository with Actions enabled

### 2. API Configuration

#### YouTube API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable YouTube Data API v3
4. Create an API key credential
5. Store the API key as `YOUTUBE_API_KEY` secret in GitHub

#### Claude API Setup

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Store it as `CLAUDE_API_KEY` secret in GitHub

### 3. GitHub Secrets

Add the following secrets to your GitHub repository:

| Secret Name | Description |
|------------|-------------|
| `YOUTUBE_API_KEY` | YouTube Data API key |
| `CLAUDE_API_KEY` | Anthropic Claude API key |
| `CHANNEL_ID` | Your YouTube channel ID (optional, defaults to UCip-bKC2h087GNd7HDqhacw) |

**To add secrets:**
1. Go to your repository Settings
2. Click "Secrets and variables" > "Actions"
3. Click "New repository secret"
4. Add each secret with its value

### 4. Deployment

The workflow is automatically configured to:
- Run every 6 hours via cron schedule
- Can be manually triggered via GitHub Actions
- Process recent videos and their comments
- Generate AI replies and post them

## Workflow Details

- **File**: `.github/workflows/youtube_auto_reply.yml`
- **Schedule**: Every 6 hours (0, 6, 12, 18 UTC)
- **Python Version**: 3.11
- **Dependencies**: google-auth, google-api-python-client, anthropic

## Script Details

- **File**: `scripts/youtube_comment_ai.py`
- **Fetches**: Recent video comments from your channel
- **Filters**: Avoids replying to obvious spam/bot comments
- **Tracking**: Maintains log of replied comments to prevent duplicates
- **Rate Limiting**: Built-in delays to respect API quotas

## Local Testing

```bash
# Install dependencies
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client anthropic python-dotenv

# Set environment variables
export YOUTUBE_API_KEY="your_key_here"
export CLAUDE_API_KEY="your_key_here"
export CHANNEL_ID="your_channel_id"

# Run the script
python scripts/youtube_comment_ai.py
```

## Monitoring

Check the GitHub Actions tab to:
- View workflow run history
- See logs from each execution
- Monitor for errors or failures
- Manually trigger runs

## Environment Variables

```
YOUTUBE_API_KEY=your_youtube_api_key
CLAUDE_API_KEY=your_claude_api_key
CHANNEL_ID=UCip-bKC2h087GNd7HDqhacw
```

## Notes

- First run processes recent comments only
- Rate limiting prevents API throttling
- Replied comments are logged to avoid duplicates
- Claude Haiku 3.5 model is used for cost efficiency
- All replies are logged for audit purposes

## Troubleshooting

**Workflow not running?**
- Check that secrets are properly set
- Verify GitHub Actions are enabled in repository
- Check workflow syntax in `.github/workflows/youtube_auto_reply.yml`

**API errors?**
- Verify API keys are correct and have proper permissions
- Check API quotas in Google Cloud and Anthropic consoles
- Ensure YouTube API is enabled in Google Cloud project

**No replies being posted?**
- Script may need OAuth2 setup for posting (currently logs what would be posted)
- Check logs in GitHub Actions for detailed error messages
- Verify channel permissions and API key scopes

## License

MIT
