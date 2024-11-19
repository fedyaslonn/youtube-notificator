from fastapi import FastAPI, APIRouter, Request, status, Depends, HTTPException, Query

from src.domain.videos.models import VideoCreateRequestBody, VideoPublic, Video
from src.infra.database.uow import get_unit_of_work, UnitOfWork

from typing import Optional, List

video_router = APIRouter(prefix="/videos", tags=["Videos"])

@video_router.post("/create_video", status_code=status.HTTP_201_CREATED)
async def create_video(uow: UnitOfWork = Depends(get_unit_of_work), url: str = Query(...)):
    try:
        async with uow:
            video = await uow.videos.create_video(url=url)
        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.get("/get_video_by_url", response_model=Video, status_code=status.HTTP_200_OK)
async def get_video_by_url(uow: UnitOfWork = Depends(get_unit_of_work), url: str = Query(...)):
    try:
        async with uow:
            video = uow.videos.get_by_url(url=url)
        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.get("/get_video_by_title", response_model=Video, status_code=status.HTTP_200_OK)
async def get_video_by_title(uow: UnitOfWork = Depends(get_unit_of_work), title: str = Query(...)):
    try:
        async with uow:
            video = uow.videos.get_by_title(title=title)
        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.get("/get_video_by_duration", response_model=Video, status_code=status.HTTP_200_OK)
async def get_video_by_duration(uow: UnitOfWork = Depends(get_unit_of_work), duration: str = Query(...)):
    try:
        async with uow:
            video = uow.videos.get_by_duration(duration=duration)
        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.get("/get_by_published_date", response_model=Video, status_code=status.HTTP_200_OK)
async def get_by_published_date(uow: UnitOfWork = Depends(get_unit_of_work), published_date: str = Query(...)):
    try:
        async with uow:
            video = uow.videos.get_by_date(date=published_date)

        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.get("/sort_all_videos_by_author_by_publication_date", response_model=List[Video], status_code=status.HTTP_200_OK)
async def sort_all_videos_by_author_by_publication_date(uow: UnitOfWork = Depends(get_unit_of_work), author_id: int = Query(...)):
    try:
        async with uow:
            videos = uow.videos.sort_all_videos_by_author_by_publication_date(author_id=author_id)
        return videos

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.post("/create_video", response_model=Video, status_code=status.HTTP_200_OK)
async def create_video(uow: UnitOfWork = Depends(get_unit_of_work), url: str = Query(...), title: str = Query(...), duration: str = Query(...), published_at: str = Query(...), author_id: int = Query(...), user_id: int = Query(...)):
    try:
        async with uow:
            video = uow.videos.create_video(url=url, title=title, duration=duration, published_at=published_at, author_id=author_id, user_id=user_id)
        return video

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@video_router.delete("/delete_video/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(id: int, uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            video_deleted = uow.videos.delete_video(video_id=id)

            if not video_deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось найти видео для удаления")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Не удалось удалить видео {str(e)}")


