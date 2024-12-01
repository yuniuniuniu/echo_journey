from sqlalchemy.orm import Session
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Depends
from echo_journey.common.utils import device_id_var, hash_password
from echo_journey.data.learn_situation import HistoryLearnSituation
from echo_journey.database import database, models, schemas, utils

router = APIRouter()

@router.get("/titles")
async def get_title(deviceId: str = Query(default=None)):
    device_id_var.set(deviceId)
    history_learn_situation = HistoryLearnSituation()
    exercise_title_info, should_update = await history_learn_situation.generate_title_info()
    return [{
      "name": '瓜瓜',
      "description": '今天有什么想聊的话题？',
      "scene": 'talk',
      "update": False,
    },
    {
      "name": '斗斗',
      "description": exercise_title_info,
      "scene": 'exercises',
      "update": should_update,
    }]