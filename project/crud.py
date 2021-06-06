from hashlib import pbkdf2_hmac
from random import choice
import string
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
from sqlalchemy import and_
from project import schemas
from project.models.models import users_table as users, tokens_table as tokens
from project.interests.interests_model import interests_table
from project.posts.posts import posts_table as posts
from databases import Database
from uuid import UUID
from os import urandom


def uuid_generate_v4():
    """ Генерируем uuid для токена """
    return UUID(bytes=urandom(16), version=4)


def get_random_string(length=12):
    """ Генерирует случайную строку (соль) """
    return "".join(choice(string.ascii_letters) for _ in range(length))


def hash_password(password: str, salt: str = None):
    """ Хеширует пароль с солью """
    if salt is None:
        salt = get_random_string()
    enc = pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return enc.hex()


def validate_password(password: str, hashed_password: str):
    """ Проверяет, что хеш пароля совпадает с хешем из БД """
    salt, hashed = hashed_password.split("$")
    return hash_password(password, salt) == hashed


def get_user_by_email(db: Database, email: str):
    """ Возвращает информацию о пользователе """
    query = users.select().where(users.c.email == email)
    return db.fetch_one(query)


def get_token_info_by_user_id(db: Database, user_id: int):
    """ Получаем информацию по токену, используя user_id """
    query = tokens.select().where(tokens.c.user_id == user_id)
    return db.fetch_one(query)


def get_interest_by_ui(db: Database, user_id: int):
    """ Получаем информацию по интересам данного пользователя, используя user_id """
    query = interests_table.select().where(interests_table.c.user_id == user_id)
    return db.fetch_one(query)


async def push_post(db: Database, user_id: int, post: schemas.PostsIn):
    """ Пушим в БД пост пользователя """
    now = datetime.now()
    query = posts.insert().values(
        user_id=user_id, created_at=now, title=post.title, content=post.content
    )
    await db.execute(query)
    return {"user_id": user_id, "created_at": str(now), "title": f"{post.title}", "content": f"{post.content}"}


def get_users(db: Database, user_id: int):
    """ Получаем информацию о всех интересах всех пользователей, кроме пользователя с user_id """
    query = interests_table.join(users).select().where(
        and_
        (
            users.c.id != user_id,
            interests_table.c.user_id != user_id
        )
    )
    return db.fetch_all(query)


def get_all_users_for_admin(db: Database, user_id: int):
    query = users.join(tokens).select().where(users.c.id != user_id)
    return db.fetch_all(query)


async def get_admin_all_users(db: Database, admin_id: int):
    users_data = await get_all_users_for_admin(db=db, user_id=admin_id)
    users_json = jsonable_encoder(users_data)
    for item in users_json:
        print(f"item: {item}")

    output_json = []
    counter = 0
    for item in users_json:
        output_json.append({})
        for key, value in item.items():
            if key not in ["token", "expires", "token_type", "created_at", "title", "content"]:
                output_json[counter][f"{key}"] = value
            else:
                output_json[counter]["token"] = {"token": item["token"], "expires": item["expires"],
                                                 "token_type": "bearer"}
        counter += 1

    print(output_json)
    return output_json


def get_posts_of_user_name(db: Database, name: str):
    query = users.join(posts).select().where(users.c.name == name)
    return db.fetch_all(query)


def get_user_by_token(db: Database, token: str):
    """ Возвращает информацию о владельце указанного токена """
    q = tokens.join(users).select().where(
        and_(
            users.c.email == token,
            tokens.c.expires > datetime.now()
        )
    )

    return db.fetch_one(q)


def get_interests_user_by_ui(db: Database, user_id: int):
    """ Получаем пользователя по его user_id """
    query = users.join(interests_table).select().where(
        and_(
            users.c.id == user_id,
            interests_table.c.user_id == user_id
        )
    )
    return db.fetch_one(query)


def get_post_cu(db: Database, user_id: int):
    """ Получаем посты пользователя по его user_id """
    query = posts.select().where(
        posts.c.user_id == user_id
    )
    return db.fetch_all(query)


def get_all_users(db: Database):
    """ Получаем всех пользователей """
    query = tokens.join(users).join(interests_table).select()
    return db.fetch_all(query)


def create_user_token(db: Database, user_id: int):
    """ Создает токен для пользователя с указанным user_id """
    insert_token = str(uuid_generate_v4())
    query = (
        tokens.insert()
            .values(expires=datetime.now() + timedelta(weeks=2), user_id=user_id, token=insert_token)
            .returning(tokens.c.token, tokens.c.expires)
    )

    return db.fetch_one(query)


async def delete_posts(db: Database, user_id: int):
    query = posts.delete().where(posts.c.user_id == user_id)
    return await db.execute(query)


async def delete_cu(db: Database, user_id: int):
    query3 = interests_table.delete().where(interests_table.c.user_id == user_id)
    await delete_posts(db=db, user_id=user_id)
    query = users.delete().where(users.c.id == user_id)
    await db.execute(query3)
    query2 = tokens.delete().where(tokens.c.user_id == user_id)
    await db.execute(query2)
    await db.execute(query)


async def update_cu_interests(db: Database, interest: dict, update: dict):
    uid = int(interest["user_id"])
    for k, v in update.items():
        if k == "interests" and interest[k]:
            interest[k] = update[k]
    query = interests_table.update(). \
        where(interests_table.c.user_id == uid). \
        values(interests=str(interest["interests"]))
    await db.execute(query)


async def update_mine_posts(db: Database, update: list, user_id: int):
    stmt = posts.update().where(and_(
        posts.c.user_id == user_id,
        posts.c.title == update[0]["title"]
    )).values(content=update[0]["content"])

    await db.execute(stmt)


async def create_user(db: Database, user: schemas.UserCreate):
    """ Создает нового пользователя в БД """
    salt = get_random_string()
    hashed_password = hash_password(user.password, salt)

    query = users.insert().values(
        email=user.email, name=user.name, hashed_password=f"{salt}${hashed_password}", is_superuser=False,
    )
    user_id = await db.execute(query)

    query_interests = interests_table.insert().values(
        interests=user.interests, user_id=user_id
    )
    await db.execute(query_interests)

    token = await create_user_token(db=db, user_id=user_id)
    token_dict = dict(token=token["token"], expires=str(token["expires"]), user_id=user_id)
    return {"id": str(user_id), "email": user.email, "name": user.name,
            "interests": user.interests, "token": token_dict}
