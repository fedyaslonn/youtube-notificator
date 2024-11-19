import os

import datetime
from dateutil import parser as dateutil_parser
from googleapiclient.discovery import build
from isodate import parse_duration

from src.domain.authors.models import AuthorPublic, AuthorCreateRequestBody

import logging

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote

import dateparser
import isodate

import pytz

from datetime import timezone, datetime
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

async def get_channel(channel_name: str):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    search_request = youtube.search().list(q=channel_name, type='channel', part='id')
    search_response = search_request.execute()

    if not search_response['items']:
        raise ValueError("Канал не найден.")

    channel_id = search_response['items'][0]['id']['channelId']

    channel_request = youtube.channels().list(part='snippet', id=channel_id)
    channel_response = channel_request.execute()

    author_name = channel_response['items'][0]['snippet']['title']
    author_url = f"https://www.youtube.com/channel/{channel_id}"

    channel_data = AuthorCreateRequestBody(author=author_name, author_url=author_url)
    return channel_data


async def get_last_video_by_channel_name(channel_name: str):

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    search_request = youtube.search().list(q=channel_name, type='channel', part='id, snippet', maxResults=1)
    search_response = search_request.execute()

    if not search_response['items']:
        raise ValueError("Канал не найден")

    channel_id = search_response['items'][0]['id']['channelId']
    logger.info(f"Найден канал {channel_id}")

    search_video_request = youtube.search().list(channelId=channel_id, type='video', part='id, snippet', order='date', maxResults=1)
    search_video_response = search_video_request.execute()

    logger.info(f"Ответ апи: {search_video_response}")

    if not search_video_response['items']:
        raise ValueError("Видео не найдено")

    video_id = search_video_response['items'][0]['id']['videoId']
    video_title = search_video_response['items'][0]['snippet']['title']

    logger.info(f"Последнее видео на канал {channel_id} - {video_title}")

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        'video_url': video_url,
        'video_title': video_title
    }


async def get_last_videos_by_subscription(channel_name: str, last_notified_at: datetime):
    last_notified_at_utc = last_notified_at.astimezone(timezone.utc)

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    logger.info(f"Поиск канала по имени {channel_name}")

    search_request = youtube.search().list(q=channel_name, type='channel', part='id, snippet', maxResults=1)
    search_response = search_request.execute()
    if not search_response['items']:
        logger.error(f"Канал {channel_name} не найден")
        raise ValueError("Канал не найден")
    channel_id = search_response['items'][0]['id']['channelId']

    logger.info(
        f"Поиск новых видео для канала {channel_name} с ID {channel_id}, опубликованных после {last_notified_at_utc.isoformat()}")

    request = youtube.search().list(
        channelId=channel_id,
        part="snippet",
        order="date",
        publishedAfter=last_notified_at_utc.isoformat()
    )
    response = request.execute()

    if not response['items']:
        logger.warning(f"Нет новых видео для канала '{channel_name}' после {last_notified_at_utc.isoformat()}")
        return []

    video_details = []
    for item in response['items']:
        video_id = item['id']['videoId']

        video_request = youtube.videos().list(
            part="contentDetails,snippet",
            id=video_id
        )
        video_response = video_request.execute()
        video_info = video_response['items'][0]

        published_at = date_parser.parse(video_info['snippet']['publishedAt']).astimezone(timezone.utc)

        duration = parse_duration(video_info['contentDetails']['duration'])

        if published_at > last_notified_at_utc:
            video_details.append({
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": video_info['snippet']['title'],
                "published_at": published_at,
                "duration": duration
            })

    return video_details