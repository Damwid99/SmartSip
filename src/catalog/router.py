from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, or_, select

from src.catalog.models import Container, DrinkType
from src.catalog.schemas import ContainerCreate, ContainerRead, DrinkTypeRead
from src.core.database import get_session
from src.core.security import get_current_user
from src.users.models import User

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/drinks", response_model=list[DrinkTypeRead])
def list_drink_types(
    session: Annotated[Session, Depends(get_session)],
) -> list[DrinkType]:
    drinks = session.exec(select(DrinkType).order_by(col(DrinkType.name).asc())).all()
    return list(drinks)


@router.get("/containers", response_model=list[ContainerRead])
def list_containers(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[ContainerRead]:
    assert current_user.id is not None

    query = (
        select(Container)
        .where(or_(col(Container.user_id).is_(None), col(Container.user_id) == current_user.id))
        .order_by(col(Container.volume_ml).asc())
    )
    containers = session.exec(query).all()

    result: list[ContainerRead] = []
    for c in containers:
        assert c.id is not None
        result.append(
            ContainerRead(
                id=c.id,
                name=c.name,
                volume_ml=c.volume_ml,
                icon=c.icon,
                user_id=c.user_id,
                is_custom=c.user_id is not None,
                created_at=c.created_at,
            )
        )
    return result


@router.post(
    "/containers",
    response_model=ContainerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_container(
    payload: ContainerCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ContainerRead:
    assert current_user.id is not None

    container = Container(
        name=payload.name,
        volume_ml=payload.volume_ml,
        icon=payload.icon,
        user_id=current_user.id,
    )
    session.add(container)
    session.commit()
    session.refresh(container)

    assert container.id is not None

    return ContainerRead(
        id=container.id,
        name=container.name,
        volume_ml=container.volume_ml,
        icon=container.icon,
        user_id=container.user_id,
        is_custom=True,
        created_at=container.created_at,
    )


@router.delete(
    "/containers/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_custom_container(
    container_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    assert current_user.id is not None

    container = session.get(Container, container_id)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Naczynie nie zostało znalezione",
        )

    if container.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nie można usunąć wbudowanego naczynia systemowego",
        )

    if container.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień do usunięcia tego naczynia",
        )

    session.delete(container)
    session.commit()
