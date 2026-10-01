"""Small generic CRUD router used for the plain resources; custom logic gets its own router."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
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
            raise ApiError(status.HTTP_404_NOT_FOUND, "not_found", f"{tag} not found")
        return obj

    def commit(db: Session) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            sqlstate = getattr(exc.orig, "sqlstate", None)
            code, message = {
                "23505": ("duplicate", "a record with these unique values already exists"),
                "23503": ("invalid_reference", "a referenced record does not exist"),
                "23502": ("missing_value", "a required value is missing"),
            }.get(sqlstate or "", ("conflict", "conflicting or invalid data"))
            raise ApiError(status.HTTP_409_CONFLICT, code, message) from exc
        except DataError as exc:
            db.rollback()
            raise ApiError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "invalid_value",
                "a value is too long or malformed",
            ) from exc

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
