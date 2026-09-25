from sqlalchemy import select
from lattice_core.models import Permission


def has_permission(db, actor_id, resource_type, resource_id, permission_type):
    return (
        db.scalar(
            select(Permission.id).where(
                Permission.target_actor_id == actor_id,
                Permission.resource_type == resource_type,
                Permission.resource_id == resource_id,
                Permission.permission_type == permission_type,
                Permission.revoked_at.is_(None),
            )
        )
        is not None
    )


def can_view_obligation(db, actor, obligation):
    return (
        actor.role == "ADMIN_DEMO"
        or actor.id == obligation.owner_actor_id
        or has_permission(db, actor.id, "OBLIGATION", obligation.id, "VIEW_SHARED_OBLIGATION")
    )


def can_view_funding(db, actor, funding):
    return (
        actor.role == "ADMIN_DEMO"
        or actor.id == funding.owner_actor_id
        or has_permission(db, actor.id, "FUNDING", funding.id, "VIEW_PRIVATE_FINANCES")
        or (
            actor.role == "STUDENT"
            and funding.student_id == actor.id
            and has_permission(db, actor.id, "FUNDING", funding.id, "VIEW_OWN_CONTRIBUTION")
        )
    )
