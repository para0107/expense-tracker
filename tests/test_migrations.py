from alembic.config import Config

from alembic import command


def test_orm_models_match_migrations(migrated_database: None) -> None:
    command.check(Config("alembic.ini"))
