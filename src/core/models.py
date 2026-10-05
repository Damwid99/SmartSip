import datetime

from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )

    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.datetime.now(datetime.UTC)},
        nullable=False,
    )


class Base(TimestampMixin):
    id: int | None = Field(default=None, primary_key=True)
