"""Create the dedicated demo database if it does not exist."""

import psycopg
from sqlalchemy.engine import make_url

from app.core.config import get_settings


def main() -> None:
    url = make_url(get_settings().database_url)
    if url.database != "checkout_demo":
        raise RuntimeError("Demo setup can only target checkout_demo")

    with psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname="checkout",
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", ("checkout_demo",)
        ).fetchone()
        if exists is None:
            connection.execute("CREATE DATABASE checkout_demo")


if __name__ == "__main__":
    main()
