from typing import List, Tuple

import firebase_admin
from firebase_admin import auth, credentials
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from core.database import get_db  # ここでget_db関数をインポート
from crud import crud
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from migration import models
from schemas import schemas

# from migration import database, models

app = FastAPI(title="社内勉強会の開催を活発にするwebアプリ", description="社内の勉強会の予定を共有するWebアプリケーション")

# Firebaseの初期化
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred)

router = APIRouter()

# CORS対応 (https://qiita.com/satto_sann/items/0e1f5dbbe62efc612a78)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# リクエストボディの定義
class Message(BaseModel):
    name: str


# Bearer認証関数の定義
def get_current_user(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        cred = auth.verify_id_token(cred.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return cred


# getを定義
@app.get("/hello")
def read_root(cred):
    uid = cred.get("uid")
    return {"message": f"Hello, {uid}!"}


# postを定義
@app.post("/hello")
def create_message(message: Message, cred):
    uid = cred.get("uid")
    return {"message": f"Hello, {message.name}! Your uid is [{uid}]"}


def index(request: Request):
    return {"Hello": "World"}


def get_data(request: Request):
    return {"key": "value", "message": "Hello from FastAPI!"}


def get_tec_result(request: Request, tec_id: int):
    return {
        "is_accepted": True,
        "interests": [
            {
                "user_id": tec_id,
                "name": tec_id,
                "icon_url": "http://localhost:3000/logo192.png",
            },
            {
                "user_id": "bbb",
                "name": "いいい",
                "icon_url": "http://localhost:3000/logo192.png",
            },
            {
                "user_id": "ccc",
                "name": "ううう",
                "icon_url": "http://localhost:3000/logo192.png",
            },
        ],
        "expertises": [
            {
                "user_id": "ccc",
                "name": "ううう",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 8,
            },
            {
                "user_id": "ddd",
                "name": "えええ",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 13,
            },
        ],
        "experiences": [
            {
                "user_id": "aaa",
                "name": "あああ",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 1,
            },
            {
                "user_id": "bbb",
                "name": "いいい",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 2,
            },
            {
                "user_id": "ccc",
                "name": "ううう",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 8,
            },
            {
                "user_id": "ddd",
                "name": "えええ",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 13,
            },
            {
                "user_id": "eee",
                "name": "おおお",
                "icon_url": "http://localhost:3000/logo192.png",
                "years": 5,
            },
        ],
    }


def get_trend_tecs(request: Request):
    tmp_tecs = ["TypeScript", "SolidJS", "Three.JS"]
    return {
        "tecs": [{"id": 1, "name": tec_name} for tec_name in tmp_tecs],
    }


def get_suggested_tecs(request: Request, tec_substring):
    tmp_tecs = ["Java", "JavaScript", "SolidJS", "Three.JS", "Golang"]



    return {
        "tecs": [
            {"id": 1, "name": tec_name}
            for tec_name in tmp_tecs
            if tec_substring in tec_name
        ],
    }


# def get_user_by_id(user_id: int, db: Session = Depends(get_db)):


def get_user_by_id(request: Request, user_id: int):
    # データベースセッションを取得
    # ユーザーをデータベースから取得
    user = db.query(models.Users).filter(models.Users.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def create_user(db: Session = Depends(get_db), cred: dict = Depends(get_current_user)):
    user_id = cred.get("uid")
    new_user = models.Users(id=user_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_all_users(db: Session = Depends(get_db)):
    users = crud.get_all_users(db)  # データベース操作関数を呼び出してデータを取得
    return users


def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # プロフィール情報を要求されたフォーマットに整形
    profile_data = {
        "name": user.name,
        "sns_link": user.sns_link,
        "comment": user.comment,
        "join_date": str(user.join_date),
        "department": user.department,
        # "interests": [{"name": interest.name} for interest in user.interests],
        # "expertises": [{"name": expertise.name, "years": expertise.expertise_years} for expertise in user.expertises],
        # "experiences": [{"name": experience.name, "years": experience.experience_years} for experience in user.experiences],
    }
    return profile_data


def update_user_profile(
    user_id: int,
    edited_sns_link: str = Body(..., description="SNSリンク"),
    edited_comment: str = Body(..., description="コメント"),
    edited_join_date: str = Body(..., description="入社日"),
    edited_department: str = Body(..., description="部署"),
    edited_interests: List[int] = Body(..., description="興味のIDリスト"),
    edited_expertises: List[Tuple[int, int]] = Body(..., description="専門性のIDと年数のリスト"),
    edited_experiences: List[Tuple[int, int]] = Body(..., description="経験のIDと年数のリスト"),
    db: Session = Depends(get_db),
):
    # try:
    # ユーザープロファイルの取得
    user_profile = crud.get_user_profile(db, user_id)

    # プロファイル情報の更新
    user_profile.sns_link = edited_sns_link
    user_profile.comment = edited_comment
    user_profile.join_date = edited_join_date
    user_profile.department = edited_department

    # 興味、専門性、経験の更新
    # データベースから関連データを削除し、新しいデータを追加
    db.query(models.UserInterests).filter(
        models.UserInterests.user_id == user_id
    ).delete()
    db.query(models.UserExpertises).filter(
        models.UserExpertises.user_id == user_id
    ).delete()
    db.query(models.UserExperiences).filter(
        models.UserExperiences.user_id == user_id
    ).delete()

    for interest_id in edited_interests:
        user_interest = models.UserInterests(
            user_id=user_id,
            technology_id=interest_id,
            interest_years=1,  # 適切な値を設定してください
        )
        db.add(user_interest)

    for expertise in edited_expertises:
        technology_id, expertise_years = expertise
        user_expertise = models.UserExpertises(
            user_id=user_id,
            technology_id=technology_id,
            expertise_years=expertise_years,
        )
        db.add(user_expertise)

    for experience in edited_experiences:
        technology_id, experience_years = experience
        user_experience = models.UserExperiences(
            user_id=user_id,
            technology_id=technology_id,
            experience_years=experience_years,
        )
        db.add(user_experience)

    try:
        # 既存のコード
        db.commit()
        return {"is_accepted": True}
    except IntegrityError as e:
        db.rollback()  # ロールバック
        raise HTTPException(status_code=400, detail="一意制約違反エラー: {}".format(str(e)))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="データベースエラー: {}".format(str(e)))



def update_like(
    user_id: int,
    study_session_id: int,
    db: Session = Depends(get_db)
):
    # Likes モデルの新しいインスタンスを作成し、必要な値を設定します
    new_like = models.Likes(user_id=user_id, study_session_id=study_session_id)

    # データベースに新しいレコードを追加
    db.add(new_like)
    db.commit()

    # レスポンスなどの適切な処理を行います
    return {"message": "Liked successfully"}


def update_not_like(
    user_id: int,
    study_session_id: int,
    db: Session = Depends(get_db)
):
    # Likes テーブルから削除対象のレコードをクエリ
    like_to_delete = db.query(models.Likes).filter_by(user_id=user_id, study_session_id=study_session_id).first()

    if like_to_delete:
        # レコードが見つかった場合、削除
        db.delete(like_to_delete)
        db.commit()
        return {"message": "Not liked successfully"}
    else:
        # レコードが見つからなかった場合、エラーレスポンスなど適切な処理を行う
        return {"message": "Like not found"}


def timeline(db: Session = Depends(get_db)):
    # StudySessionsテーブルの全てのレコードを取得
    sessions = db.query(models.StudySessions).all()
    return sessions

def get_trend(db: Session = Depends(get_db)):
    # technology_idごとにカウントを取得し、降順でソート
    trend_result = (
        db.query(models.UserInterests.technology_id, func.count(models.UserInterests.technology_id).label('count'))
        .group_by(models.UserInterests.technology_id)
        .order_by(desc('count'))
        .limit(3)
        .all()
    )

    # クエリ結果からtechnology_idだけのリストを取得
    top_technologies = [result.technology_id for result in trend_result]

    return top_technologies

def get_tech_users(tec_id: int, db: Session = Depends(get_db)):
    # 1. 指定された tec_id で各テーブルから情報を取得
    interests = db.query(models.UserInterests).options(joinedload(models.UserInterests.user)).filter_by(technology_id=tec_id).all()
    expertises = db.query(models.UserExpertises).options(joinedload(models.UserExpertises.user)).filter_by(technology_id=tec_id).all()
    experiences = db.query(models.UserExperiences).options(joinedload(models.UserExperiences.user)).filter_by(technology_id=tec_id).all()

    # 2. user_detail から情報を取得
    interest_data = [{"user_id": item.user_id, "name": item.user.name, "icon_image": item.user.icon_image, "interest_years": item.interest_years} for item in interests]
    expertise_data = [{"user_id": item.user_id, "name": item.user.name, "icon_image": item.user.icon_image, "expertise_years": item.expertise_years} for item in expertises]
    experience_data = [{"user_id": item.user_id, "name": item.user.name, "icon_image": item.user.icon_image, "experience_years": item.experience_years} for item in experiences]

    # 3. 結果を整形して返す
    return {
        "interests": interest_data,
        "expertises": expertise_data,
        "experiences": experience_data
    }
