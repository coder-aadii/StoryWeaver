"""Small generic CRUD router used for the plain resources; custom logic gets its own router."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db


def crud_router(
    *,
    model: type[Any],
    create: type[BaseModel] | None,
    update: type[BaseModel] | None,
    read: type[BaseModel],
    prefix: str,
    tag: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def get_or_404(db: Session, item_id: uuid.UUID) -> Any:
        obj = db.get(model, item_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{tag} not found")
        return obj

    def commit(db: Session) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "conflict or invalid reference") from exc

    @router.get("", response_model=list[read])
    def list_items(
        db: Session = Depends(get_db),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> Any:
        stmt = select(model).order_by(model.created_at.desc()).limit(limit).offset(offset)
        return db.scalars(stmt).all()

    @router.get("/{item_id}", response_model=read)
    def get_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
        return get_or_404(db, item_id)

    if create is not None:

        @router.post("", response_model=read, status_code=status.HTTP_201_CREATED)
        def create_item(payload: create, db: Session = Depends(get_db)) -> Any:  # type: ignore[valid-type]
            obj = model(**payload.model_dump())
            db.add(obj)
            commit(db)
            return obj

    if update is not None:

        @router.patch("/{item_id}", response_model=read)
        def update_item(item_id: uuid.UUID, payload: update, db: Session = Depends(get_db)) -> Any:  # type: ignore[valid-type]
            obj = get_or_404(db, item_id)
            for k, v in payload.model_dump(exclude_unset=True).items():
                setattr(obj, k, v)
            commit(db)
            return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
        db.delete(get_or_404(db, item_id))
        commit(db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
