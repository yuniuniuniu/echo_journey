import asyncio
import logging.config
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from echo_journey.api.restful_routes import router as restful_router
from echo_journey.api.websocket_routes import router as websocket_router
from echo_journey.common.utils import ConnectionManager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Change to domains if you deploy this to production
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(restful_router)
app.include_router(websocket_router)

ConnectionManager.initialize()
# suppress deprecation warnings
warnings.filterwarnings("ignore", module="whisper")

logger = logging.getLogger(__name__)


def log_exception(loop, context):
    exception = context.get("exception")
    logger.exception(f"Caught exception: {exception}")
    loop.default_exception_handler(context)


loop = asyncio.get_event_loop()
loop.set_exception_handler(log_exception)
