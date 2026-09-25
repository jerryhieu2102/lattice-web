from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from lattice_core.db import get_db
from lattice_core.models import Actor
from apps.api.auth import current_actor

DB = Annotated[Session, Depends(get_db)]
User = Annotated[Actor, Depends(current_actor)]


def owned(db, model, id_, owner_field, owner_id):
    obj = db.get(model, id_)
    if not obj or getattr(obj, owner_field) != owner_id:
        raise HTTPException(404, "Resource not found")
    return obj
