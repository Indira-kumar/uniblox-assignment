"""Create an isolated local scenario database when needed."""

import psycopg
from sqlalchemy.engine import make_url

from app.core.config import get_settings

ALLOWED_DATABASES = frozenset({"checkout_demo", "checkout_load"})


def main() -> None:
    url = make_url(get_settings().database_url)
    database_name = url.database
    if url.host != "db" or database_name not in ALLOWED_DATABASES:
        raise RuntimeError("Scenario setup requires the local Compose db and a scenario database")

    with psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname="checkout",
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
        ).fetchone()
        if exists is None:
            statement = (
                "CREATE DATABASE checkout_demo"
                if database_name == "checkout_demo"
                else "CREATE DATABASE checkout_load"
            )
            connection.execute(statement)


if __name__ == "__main__":
    main()
