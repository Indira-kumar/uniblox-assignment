"""Declarative base shared by persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
