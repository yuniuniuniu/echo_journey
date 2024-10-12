import logging
from fastapi import APIRouter, Path, WebSocket, WebSocketDisconnect, Query

from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.upward_message_wrapper import unwrap_upward_message_from_bytes
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.common.utils import get_connection_manager
from echo_journey.services.talk_practise_service import TalkPractiseService
from echo_journey.common.utils import session_id_var
logger = logging.getLogger(__name__)

router = APIRouter()
manager = get_connection_manager()

@router.websocket("/ws/hear/{session_id}")
async def websocket_hear_practise(
    websocket: WebSocket,
    session_id: str = Path(...),
    platform: str = Query(default="web"),
):
    await manager.connect(websocket)

    try:
        while True:
            received_data_bytes = await websocket.receive_bytes()
            pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        await manager.disconnect(websocket)
        
        
@router.websocket("/ws/talk/{session_id}")
async def websocket_talk_practise(
    websocket: WebSocket,
    session_id: str = Path(...),
    platform: str = Query(default="web"),
):
    session_id_var.set(session_id)
    await manager.connect(websocket)
    ws_msg_handler = DownwardProtocolHandler(websocket, manager)
    talk_practise_service = TalkPractiseService(session_id, ws_msg_handler)
    await talk_practise_service.initialize()
        
    try:
        while True:
            received_data_bytes = await websocket.receive_bytes()
            upward_message = unwrap_upward_message_from_bytes(received_data_bytes)
            if isinstance(upward_message, StudentMessage):
                await talk_practise_service.process_student_message(upward_message, platform)
            elif isinstance(upward_message, AudioMessage):
                await talk_practise_service.process_audio_message(upward_message, platform)
            else:
                raise ValueError(f"Unknown message type: {upward_message.type}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.exception(f"Caught exception: {e}")
        await manager.disconnect(websocket)