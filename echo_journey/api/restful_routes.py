import json

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

router = APIRouter()

@router.get("/titles")
async def get_title(deviceId: str = Query(default=None)):
    return [{
      "name": '瓜瓜',
      "description": '今天有什么想聊的话题？',
      "scene": 'talk',
      "update": False,
    },
    {
      "name": '斗斗',
      "description": '奖励你一大挑战？',
      "scene": 'exercises',
      "update": False,
    }]