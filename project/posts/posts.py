import sqlalchemy

from project.models.models import users_table

# Создаём специальную метадату для таблицы posts, где будут храниться посты каждого пользователя.
metadata = sqlalchemy.MetaData()

# Создаём таблицу posts с помощью SQLAlchemy Core
posts_table = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey(users_table.c.id)),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime()),
    sqlalchemy.Column("title", sqlalchemy.String(100)),
    sqlalchemy.Column("content", sqlalchemy.Text()),
)