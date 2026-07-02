#!/usr/bin/env python3
"""
YouTube Auto Reply with Claude AI
Automatically replies to YouTube comments using Claude API
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from anthropic import Anthropic

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
YOUTUBE_API_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
CHANNEL_ID = os.getenv('CHANNEL_ID', 'UCip-bKC2h087GNd7HDqhacw')
CREDENTIALS_FILE = 'youtube_credentials.json'
TOKEN_FILE = 'youtube_token.json'
REPLIES_LOG_FILE = 'replied_comments.json'

class YouTubeCommentAIReply:
    """Handle YouTube comments and generate AI replies"""

    def __init__(self):
        self.youtube_service = None
        self.claude_client = Anthropic()
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.replied_comments = self._load_replied_comments()

    def _load_replied_comments(self) -> set:
        """Load list of already replied comments"""
        if os.path.exists(REPLIES_LOG_FILE):
            try:
                with open(REPLIES_LOG_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get('replied_ids', []))
            except Exception as e:
                logger.warning(f"Could not load replied comments log: {e}")
        return set()

    def _save_replied_comment(self, comment_id: str):
        """Save replied comment ID to avoid duplicates"""
        self.replied_comments.add(comment_id)
        try:
            with open(REPLIES_LOG_FILE, 'w') as f:
                json.dump({
                    'replied_ids': list(self.replied_comments),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save replied comment: {e}")

    def _authenticate_youtube(self) -> bool:
        """Authenticate with YouTube API using API key"""
        try:
            self.youtube_service = build(
                'youtube',
                'v3',
                developerKey=self.api_key
            )
            logger.info("YouTube authentication successful")
            return True
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False

    def _get_channel_videos(self, max_results: int = 10) -> List[str]:
        """Get recent video IDs from the channel"""
        try:
            request = self.youtube_service.search().list(
                part='id',
                channelId=CHANNEL_ID,
                order='date',
                maxResults=max_results,
                type='video'
            )
            response = request.execute()
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]
            logger.info(f"Found {len(video_ids)} recent videos")
            return video_ids
        except HttpError as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []

    def _get_video_comments(self, video_id: str, max_results: int = 20) -> List[Dict]:
        """Get comments from a video"""
        try:
            request = self.youtube_service.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(max_results, 100),
                textFormat='plainText',
                order='relevance'
            )
            response = request.execute()

            comments = []
            for item in response.get('items', []):
                comment_snippet = item['snippet']['topLevelComment']['snippet']
                comment_data = {
                    'id': item['id'],
                    'video_id': video_id,
                    'author': comment_snippet['authorDisplayName'],
                    'text': comment_snippet['textDisplay'],
                    'likes': comment_snippet['likeCount'],
                    'time': comment_snippet['publishedAt'],
                    'reply_count': item['snippet']['totalReplyCount']
                }
                comments.append(comment_data)

            logger.info(f"Found {len(comments)} comments in video {video_id}")
            return comments
        except HttpError as e:
            logger.error(f"Error fetching comments for video {video_id}: {e}")
            return []

    def _generate_reply(self, comment_text: str, video_title: str = "") -> Optional[str]:
        """Generate AI reply using Claude API"""
        try:
            system_prompt = """You are a helpful YouTube channel manager AI assistant.
Your job is to generate thoughtful, engaging, and professional replies to YouTube comments.
- Keep replies concise (1-3 sentences max)
- Be friendly and appreciative of the comment
- Avoid generic responses
- Address the commenter by name when possible
- Add value to the conversation"""

            user_message = f"""Please generate a brief, engaging reply to this YouTube comment:

Comment: "{comment_text}"
{"Video: " + video_title if video_title else ""}

Generate ONLY the reply text, without any additional explanation or formatting."""

            message = self.claude_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            reply_text = message.content[0].text.strip()
            logger.info(f"Generated reply: {reply_text[:100]}...")
            return reply_text
        except Exception as e:
            logger.error(f"Error generating reply with Claude: {e}")
            return None

    def _post_reply(self, comment_id: str, reply_text: str, video_id: str) -> bool:
        """Post reply to YouTube comment"""
        try:
            request = self.youtube_service.comments().insert(
                part='snippet',
                body={
                    'snippet': {
                        'parentId': comment_id,
                        'textOriginal': reply_text
                    }
                }
            )
            response = request.execute()
            logger.info(f"Successfully posted reply to comment {comment_id}")
            self._save_replied_comment(comment_id)
            return True
        except HttpError as e:
            if e.resp.status == 403:
                logger.warning("YouTube API permission denied - likely needs OAuth authentication")
            else:
                logger.error(f"Error posting reply: {e}")
            return False

    def _should_reply(self, comment: Dict) -> bool:
        """Determine if a comment should get an auto-reply"""
        # Don't reply if already replied
        if comment['id'] in self.replied_comments:
            return False

        # Don't reply to very short comments (likely spam)
        if len(comment['text']) < 5:
            return False

        # Don't reply to comments from bot accounts (heuristic)
        if any(word in comment['author'].lower() for word in ['bot', 'spam', 'ads']):
            return False

        return True

    def process_comments(self):
        """Main process: get comments and reply with AI"""
        logger.info("Starting YouTube Auto Reply process...")

        if not self._authenticate_youtube():
            logger.error("Failed to authenticate with YouTube")
            return False

        processed_count = 0
        replied_count = 0

        try:
            # Get recent videos
            videos = self._get_channel_videos(max_results=5)

            for video_id in videos:
                comments = self._get_video_comments(video_id, max_results=20)

                for comment in comments:
                    processed_count += 1

                    if not self._should_reply(comment):
                        continue

                    logger.info(f"Processing comment from {comment['author']}: {comment['text'][:80]}...")

                    # Generate AI reply
                    reply_text = self._generate_reply(comment['text'])

                    if reply_text:
                        # Post the reply (this will require OAuth in real deployment)
                        # For now, we log what would be posted
                        logger.info(f"Would reply: {reply_text}")
                        # Uncomment below when OAuth is properly configured:
                        # if self._post_reply(comment['id'], reply_text, video_id):
                        #     replied_count += 1
                        self._save_replied_comment(comment['id'])
                        replied_count += 1

                    # Rate limiting to avoid API throttling
                    time.sleep(1)

                # Small delay between videos
                time.sleep(2)

            logger.info(f"Process complete. Processed: {processed_count}, Replied: {replied_count}")
            return True

        except Exception as e:
            logger.error(f"Error during comment processing: {e}")
            return False

def main():
    """Main entry point"""
    try:
        bot = YouTubeCommentAIReply()
        success = bot.process_comments()

        if success:
            logger.info("YouTube Auto Reply workflow completed successfully")
            return 0
        else:
            logger.error("YouTube Auto Reply workflow failed")
            return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
