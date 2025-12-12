from sqlalchemy import select, exists
from cctracker.db import with_db, models

stmt = select(exists().where(models.Event.slug == "test"))
