import asyncio

from src.application.routers.users import *
from src.infra.application.factory import lifespan
from src.application.routers.videos import *
from src.application.routers.authors import *

app = FastAPI(lifespan=lifespan)


app.include_router(user_router)
app.include_router(author_router)
app.include_router(video_router)

