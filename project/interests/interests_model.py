import sqlalchemy
from ..models.models import users_table

# Создаём метадату для таблицы interests
metadata = sqlalchemy.MetaData()

# Создаём таблицу interests с помощью SQLAlchemy Core
interests_table = sqlalchemy.Table(
    "interests",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("interests", sqlalchemy.Text(), nullable=False),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey(users_table.c.id)),
)