from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from typing import List
import time
from fastapi.responses import JSONResponse
from . import crud
from . import schemas
import databases
from .config import SQLALCHEMY_DATABASE_URL
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from templates import success_page, main_page
from fastapi.responses import HTMLResponse


# Класс для обработки ошибок по параметрам
class UnicornException(Exception):
    def __init__(self, content: str, code_status: int):
        self.content = content
        self.status = code_status


# Объявление движка приложения
app = FastAPI()


# Создадим промежуточное ПО по http
# считаем время запросов ( для тестов )
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"Time of current request: {process_time}")
    return response


# Конфигурации роута /api/user/...
user_router = APIRouter(
    prefix="/api/user",
    tags=["user"],
    responses={404: {"description": " Not found :("}},
)

# Конфигурация роута /api/user/auth/update_posts/...
user_posts_router = APIRouter(
    prefix="/api/user/auth/update_posts",
    tags=["posts"],
    responses={404: {"description": "Jessica can't found u post :( "}},
)

# Конфигурация роута /api/admin/...
admin_router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "My Dear, dont take mistakes there !"}},
)

# Инициализация БД
database = databases.Database(SQLALCHEMY_DATABASE_URL)


# Обработчик ошибок внутри приложения app
@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    """ Обработчик ошибок типа UnicornException """
    return JSONResponse(
        status_code=exc.status,
        content={"message": f"Oops! {exc.content}"},
    )


# Роут аунтетификации
@app.post("/auth")
async def auth(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await crud.get_user_by_email(db=database, email=form_data.username)
    if not user:
        raise UnicornException(code_status=400, content="Incorrect email or password")
    if not crud.validate_password(
            password=form_data.password, hashed_password=user["hashed_password"]
    ):
        raise UnicornException(code_status=400, content="Incorrect email or password")

    return {"access_token": form_data.username, "token_type": "bearer"}


# Роут регистрации
@user_router.post("/sign-up", response_model=schemas.User, response_model_exclude_unset=True)
async def create_user(user: schemas.UserCreate):
    """ Проверка на наличие уже зарегистрированного пользователя """
    db_user = await crud.get_user_by_email(db=database, email=user.email)
    if db_user:
        raise UnicornException(code_status=418, content="Email already registered")
    return await crud.create_user(db=database, user=user)


# Объявляем применяемую зависимость для аунтетифицированных пользователей
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")


async def get_mine_interests(token: str = Depends(oauth2_scheme)):
    cu = await crud.get_user_by_token(db=database, token=token)
    user_id = int(cu["user_id"])
    return await crud.get_interests_user_by_ui(db=database, user_id=user_id)


@app.get("/api/user/auth/my_page/interests", response_model=schemas.InterestsBase, response_model_exclude_unset=True)
async def get_my_interest(my_interests: schemas.InterestsBase = Depends(get_mine_interests)):
    return my_interests


# С помщью запроса PATCH, пользователь может изменять свой список интересов.
@app.patch("/api/user/auth/my_page/update_interests")
async def update_cu_interests(update: schemas.InterestsUpdate,
                              interests: schemas.InterestsBase = Depends(get_mine_interests)):
    update = jsonable_encoder(update)
    interests = jsonable_encoder(interests)
    await crud.update_cu_interests(db=database, interest=interests, update=update)
    return success_page.success_letter(letter="Success!")


# Вспомогательный функция-зависимость. Для текущего аунт. юзера возвращает информацию о нём согласно полям схемы User.
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await crud.get_user_by_token(db=database, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


@user_posts_router.get("/get_posts/{name}", response_model=List[schemas.PostsUpdate])
async def get_posts_of_user_use_name(name: str, cu: schemas.User = Depends(get_current_user)):
    return await crud.get_posts_of_user_name(db=database, name=name)


@app.delete("/api/user/auth/my_page/delete_my_page")
async def delete_my_page(cu: schemas.User = Depends(get_current_user)):
    uid = int(jsonable_encoder(cu)["id"])
    await crud.delete_cu(db=database, user_id=uid)
    return success_page.success_letter(letter="Success!")


# Функция получения всех постов текущего пользователя.
async def get_me_posts(current_user: schemas.User = Depends(get_current_user)):
    cu = dict(current_user)
    user_id = cu["user_id"]
    update_user = await crud.get_post_cu(db=database, user_id=user_id)

    return update_user


@user_posts_router.delete("/delete")
async def delete_my_posts(cu: schemas.User = Depends(get_current_user)):
    uid = int(jsonable_encoder(cu)["id"])
    await crud.delete_posts(db=database, user_id=uid)
    return success_page.success_letter(letter="Success!")


# Пушим посты в базу данных для дальнейшего вывода их в ЛК пользователя.
@user_posts_router.post("/", response_model=schemas.PostsBase, response_model_exclude_unset=True)
async def create_new_posts(post: schemas.PostsIn, current_user: schemas.User = Depends(get_current_user)):
    try:
        cu = dict(current_user)
        user_id = cu["user_id"]
        return await crud.push_post(db=database, user_id=user_id, post=post)
    except Exception as E:
        print(E)


# Сделаем частичный update, с помощью метода PATCH. По названию поста.
@user_posts_router.patch("/patch_mine_post/{title}")
async def update_mine_posts(cp: schemas.PostsUpdate,
                            current_user: schemas.User = Depends(get_current_user)):
    json_enc = jsonable_encoder(current_user)
    uid = json_enc["user_id"]

    posts_cu = await crud.get_post_cu(db=database, user_id=uid)
    posts_cu = jsonable_encoder(posts_cu)
    print(f"The type of posts_cu: {type(posts_cu)}")
    cp = jsonable_encoder(cp)
    title = cp['title']
    for item in posts_cu:
        if item['title'] == title and item['user_id'] == uid:
            item[title] = cp["content"]
        elif item["user_id"] != uid:
            raise UnicornException(code_status=401, content="Not available!")
        else:
            continue
    print(posts_cu)
    await crud.update_mine_posts(db=database, update=posts_cu, user_id=int(uid))
    return {"Success": "!"}


# Функция, которая возвращает результат join-а interests с users и даёт нам всю необходимую информацию о каждом юзере,
# кроме того юзера, user_id которого мы передали.
@app.get("/secret/auth/users/get_all_ui", response_model=List[schemas.User])
async def get_users_interests(user_id: int):
    return await crud.get_users(db=database, user_id=user_id)


# Функция-зависимость. Возвращает такой json для юзера, который имеет схожие поля интересов.
# Если по-простому, то выводит анкеты людей со схожими интересами.
async def users_with_similar_interests(token: str = Depends(oauth2_scheme)):
    current_user = await crud.get_user_by_token(db=database, token=token)
    user_id = int(current_user["id"])

    cu_interests = await crud.get_interest_by_ui(db=database, user_id=user_id)
    cu_interest = set(cu_interests["interests"].split(", "))

    interests_of_users = await get_users_interests(user_id=user_id)

    # preprocessing data
    support_dct = dict()
    for item in interests_of_users:
        support_dct[item["id"]] = item["interests"].split(", ")

    # Выполняем небольшое преобразование
    for key, value in support_dct.items():
        for item in value:
            if ' ' in item:
                ind = item.index(' ')
                result_item = item[ind + 1:]
                value[1] = result_item
                support_dct[key] = value

    interests_dictionary = dict()
    for item in interests_of_users:
        for key, value in support_dct.items():
            if key == int(item["id"]):
                interests_dictionary[f"{item['name']}"] = set(value)

    copy_of_dict = interests_dictionary.copy()
    for key, value in copy_of_dict.items():
        if len(cu_interest & value) >= 1:
            continue
        else:
            interests_dictionary.pop(key, None)
    return interests_dictionary


# Этот роут работает на зависимости get_current_user, работа которого описана выше.
@app.get("/api/user/auth/my_page")
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user


# Функция использует функцию-зависимость для того, чтобы вернуть все посты/записи пользователю.
@app.get("/api/user/auth/my_page/posts/", response_model_exclude_unset=True)
async def read_users_my_posts(posts: schemas.PostsBase = Depends(get_me_posts)):
    return posts


# Этот роут работает на зависимсоти users_with_similar_interests, работа которого описана выше
@app.get("/api/user/auth/get_me_users")
async def get_users_with_my_interests(users: schemas.User = Depends(users_with_similar_interests)):
    return users


async def get_all_users(tokens: str = Depends(oauth2_scheme)):
    return await crud.get_all_users(db=database)


@app.get("/api/user/auth/get_all_users", response_model=List[schemas.UserBase])
async def get_me_all_users(users: schemas.User = Depends(get_all_users)):
    return users


async def get_admin(token: str = Depends(oauth2_scheme)):
    user = await crud.get_user_by_token(db=database, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    if not user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="U are super, but.. u are not a superuser :("
        )
    return user


@admin_router.get("/all_users", response_model=List[schemas.FullUser], response_model_exclude_unset=True)
async def get_me_all_full_users(admin: schemas.FullUser = Depends(get_admin)):
    ai = int(jsonable_encoder(admin)["id"])
    return await crud.get_admin_all_users(db=database, admin_id=ai)

# Добавляем в скоуп приложения роут router
app.include_router(user_router)
# Добавляем в скоуп приложения роут posts_router
app.include_router(user_posts_router)
# Добавляем в скоуп приложения роут admin_router
app.include_router(admin_router)


# Функции работающие когда приложение запускается и завершается соответственно
@app.on_event("startup")
async def startup():
    """ когда приложение запускается устанавливаем соединение с БД """
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    """ когда приложение останавливается разрываем соединение с БД """
    await database.disconnect()


@app.get("/check")
async def read_root():
    return {"Hello": "World"}


@app.get("/main/")
async def get_main_page():
    return main_page.generate_html_response()