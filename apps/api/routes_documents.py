import hashlib
from io import BytesIO
from fastapi import APIRouter, HTTPException, Request
from pypdf import PdfReader
from sqlalchemy import select
from apps.api.deps import DB, User, owned
from apps.api.auth import require_student
from apps.api.schemas import DocumentInput, Confirmation
from apps.api.planning import invalidate
from lattice_core.models import Document, DocumentBlock, FinancialFact, Obligation
from lattice_core.serialization import public
from lattice_ai.extraction.service import extract, confirm
from lattice_core.audit.service import record
from pydantic import ValidationError

router = APIRouter()


@router.post("/documents")
async def upload(request: Request, db: DB, actor: User):
    student = require_student(actor)
    blocks = []
    if "multipart/form-data" in request.headers.get("content-type", ""):
        form = await request.form(max_files=1, max_fields=4, max_part_size=2 * 1024 * 1024)
        upload = form.get("file")
        if not upload or not hasattr(upload, "read"):
            raise HTTPException(422, "File is required")
        data = await upload.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(413, "Maximum upload is 2 MB")
        filename = str(upload.filename).split("/")[-1].split("\\")[-1]
        if filename.lower().endswith(".pdf"):
            try:
                pdf = PdfReader(BytesIO(data))
                if len(pdf.pages) > 20:
                    raise HTTPException(422, "Maximum 20 PDF pages")
                for page_number, page in enumerate(pdf.pages, 1):
                    for line in (page.extract_text() or "").splitlines():
                        blocks.append({"page": page_number, "text": line})
                text = "\n".join(b["text"] for b in blocks)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(422, "Unreadable PDF") from None
        elif filename.lower().endswith(".txt"):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(422, "Text must be UTF-8") from None
        else:
            raise HTTPException(422, "Only text PDFs and .txt files are supported")
        if not text.strip():
            raise HTTPException(
                422, "No extractable text. OCR is not available; provide a text PDF or .txt fixture."
            )
        try:
            parsed = DocumentInput(
                filename=filename,
                text=text,
                trust_level=str(form.get("trust_level", "T3")),
                target_obligation_id=form.get("target_obligation_id") or None,
            )
        except ValidationError as e:
            raise HTTPException(422, str(e)) from None
    else:
        try:
            parsed = DocumentInput.model_validate(await request.json())
        except (ValidationError, ValueError) as e:
            raise HTTPException(422, str(e)) from None
        data = parsed.text.encode()
    if parsed.target_obligation_id:
        owned(db, Obligation, parsed.target_obligation_id, "owner_actor_id", student)
    doc = Document(**parsed.model_dump(), owner_id=student, sha256=hashlib.sha256(data).hexdigest())
    db.add(doc)
    db.flush()
    for index, block in enumerate(blocks):
        db.add(DocumentBlock(document_id=doc.id, page=block["page"], block_index=index, text=block["text"]))
    record(
        db,
        actor.id,
        student,
        "DOCUMENT_UPLOADED",
        "AI",
        {"document_id": doc.id, "sha256": doc.sha256, "trust_level": doc.trust_level},
    )
    return public(doc)


@router.get("/documents")
def documents(db: DB, actor: User):
    return [
        public(d)
        for d in db.scalars(
            select(Document).where(
                Document.owner_id == actor.id
                if actor.role != "ADMIN_DEMO"
                else Document.owner_id.in_(["maya", "father", "sponsor"])
            )
        )
    ]


@router.get("/documents/{id}")
def document(id: str, db: DB, actor: User):
    doc = db.get(Document, id)
    allowed_owners = {"maya", "father", "sponsor"} if actor.role == "ADMIN_DEMO" else {actor.id}
    if not doc or doc.owner_id not in allowed_owners:
        raise HTTPException(404, "Resource not found")
    facts = list(db.scalars(select(FinancialFact).where(FinancialFact.document_id == id)))
    return {**public(doc), "facts": [public(f) for f in facts]}


@router.post("/documents/{id}/extract")
def extraction(id: str, db: DB, actor: User):
    student = require_student(actor)
    doc = owned(db, Document, id, "owner_id", student)
    facts = extract(db, doc, actor.id)
    invalidation = (
        invalidate(db, student, actor.id, "BENEFICIARY_CHANGED", {"document_id": id})
        if doc.security_flags
        else {}
    )
    return {"document": public(doc), "facts": [public(f) for f in facts], **invalidation}


@router.get("/facts")
def facts(db: DB, actor: User):
    owner = "maya" if actor.role == "ADMIN_DEMO" else actor.id
    docs = select(Document.id).where(Document.owner_id == owner)
    return [public(f) for f in db.scalars(select(FinancialFact).where(FinancialFact.document_id.in_(docs)))]


@router.post("/facts/{id}/confirm")
def confirmation(id: str, data: Confirmation, db: DB, actor: User):
    student = require_student(actor)
    fact = db.get(FinancialFact, id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    doc = owned(db, Document, fact.document_id, "owner_id", student)
    result = confirm(db, fact, doc, actor.id)
    if result["updated"]:
        result.update(invalidate(db, student, actor.id, "FACT_CONFIRMED", {"fact_id": id}))
    return {"fact": public(fact), **result}


@router.post("/facts/{id}/reject")
def reject(id: str, db: DB, actor: User):
    student = require_student(actor)
    fact = db.get(FinancialFact, id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    owned(db, Document, fact.document_id, "owner_id", student)
    if fact.verification_status in {"USER_CONFIRMED", "SOURCE_VERIFIED"}:
        raise HTTPException(
            409, "Confirmed fact is retained as evidence. Correct the financial record explicitly."
        )
    fact.verification_status = "REJECTED"
    record(db, actor.id, student, "FACT_REJECTED", "AI", {"fact_id": id})
    return public(fact)
