from sqlalchemy.orm import Session
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Depends
from echo_journey.common.utils import device_id_var, hash_password
from echo_journey.data.learn_situation import HistoryLearnSituation
from echo_journey.database import database, models, schemas, utils

router = APIRouter()

@router.post("/login")
async def login(user_login: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == user_login.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not utils.verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"message": "Login successful"}
  
@router.post("/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = hash_password(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"username": new_user.username, "id": new_user.id}

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