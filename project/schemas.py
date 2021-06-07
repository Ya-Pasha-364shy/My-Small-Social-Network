from typing import Optional
from pydantic import BaseModel, validator
from datetime import datetime


class TokenBase(BaseModel):

    token: str
    expires: datetime
    token_type: Optional[str] = 'bearer'

    class Config:
        allow_population_by_field_name = True

    @validator("expires")
    def validate_date(cls, v):
        if v is None:
            raise ValueError('~ datetime not be is null ~')
        return v


class UserCreate(BaseModel):
    """ Проверяет sign-up запрос """
    email: str
    name: str
    password: str
    repeating_password: str
    interests: str
    is_superuser: Optional[bool] = False

    @validator('repeating_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('~ passwords do not match ~')
        return v

    @validator('interests')
    def convert_list(cls, stroke):
        lst = stroke.split(",")
        if len(lst) < 2:
            raise ValueError('~ List of interests must be more than one ~')
        perfect_stroke = ', '.join(lst)
        return perfect_stroke

    @validator('email')
    def email_must_contain_a_dog(cls, v):
        if ('@' not in v) or ('.' not in v) or (('com' or 'ru') not in v):
            raise ValueError('~ Please, enter a right email ~')
        return v


class UserBase(BaseModel):
    """ Формирует тело ответа с деталями пользователя """
    id: str
    email: str
    name: str
    interests: str

    @validator('interests')
    def convert_list(cls, stroke):
        lst = stroke.split(",")
        if len(lst) < 2:
            raise ValueError('~ List of interests must be more than one ~')
        perfect_stroke = ', '.join(lst)
        return perfect_stroke


class User(UserBase):
    """ Формирует тело ответа с деталями пользователя и токеном """
    token: TokenBase

    @validator('name')
    def name_must_contain_space(cls, v):
        if ' ' not in v:
            raise ValueError('~ You forgot to enter your last name or first name in the first name field ~')
        return v.title()

    @validator('email')
    def email_must_contain_a_dog(cls, v):
        if ('@' not in v) and ('.' not in v) and ('com' or 'ru' not in v):
            raise ValueError('~ Please, enter a right email ~')
        return v


class PostsIn(BaseModel):
    user_id: Optional[int] = None
    created_at: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None

    @validator('title')
    def title_validator(cls, v):
        if len(v) > 100:
            raise ValueError("~ Your title is so big. Lets make it small ~")


class PostsUpdate(BaseModel):
    title: Optional[str]
    content: Optional[str]


class PostsBase(PostsIn):
    """ Модель (сущность), описывающая посты каждого пользователя """
    id: Optional[str] = None


class UserPosts(UserBase, PostsUpdate):
    interests: Optional[str] = None


class InterestsBase(BaseModel):
    id: Optional[str] = None
    interests: Optional[str]
    user_id: Optional[str] = None


class InterestsUpdate(BaseModel):
    interests: Optional[str]


class FullUser(User):
    id: Optional[str] = None
    interests: Optional[str] = None
