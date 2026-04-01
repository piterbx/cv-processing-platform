import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.core.config import settings
from src.schemas.candidate import (
    ApprovedCandidateData,
    CandidateReviewDraft,
    SkillApproveSchema,
    WorkExperienceApproveSchema,
)
from src.schemas.document import DocumentReviewResponse, DocumentUpload
from src.services.queue import queue_service
from src.services.storage import storage_service

from common import S3UploadError
from common.models import Application, Candidate, Document, Skill, WorkExperience
from common.schemas import GenerateEmbeddingsTask, ParseCVTask

logger = logging.getLogger(__name__)


class DocumentService:
    async def get_all_documents(self, db: AsyncSession, skip: int, limit: int):
        query = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def create_document(
        self, db: AsyncSession, upload_data: DocumentUpload
    ) -> Document:
        file = upload_data.file

        # streaming hash calculation (8KB chunks)
        sha256_hash = hashlib.sha256()
        while chunk := await file.read(8192):
            sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()

        await file.seek(0)

        query = select(Document).where(Document.file_hash == file_hash)
        existing_doc = (await db.execute(query)).scalar_one_or_none()

        if existing_doc:
            logger.info(
                f"Reusing existing document ID {existing_doc.id} for hash {file_hash}"
            )
            return existing_doc

        # prepare metadata and DB record for a new document
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        s3_key = f"{uuid.uuid4()}.{file_ext}"

        new_doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            s3_key=s3_key,
            status="PENDING",
            file_hash=file_hash,
        )

        try:
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
        except IntegrityError:
            # race condition catch: Another concurrent request just committed this hash
            await db.rollback()
            logger.info(
                f"Race condition mitigated: "
                f"Reusing newly created document for {file_hash}"
            )
            # if race condition happened, fetch the one that was just created
            race_doc = (
                await db.execute(
                    select(Document).where(Document.file_hash == file_hash)
                )
            ).scalar_one()
            return race_doc
        except Exception as e:
            logger.error(f"Database error during creation: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Database error") from e

        # upload to S3
        try:
            await storage_service.upload_file(file.file, s3_key, file.content_type)
        except S3UploadError as e:
            logger.error(f"Failed to upload to S3. Error: {e}")
            new_doc.status = "FAILED"
            await db.commit()
            raise HTTPException(
                status_code=500, detail="Failed to upload file to S3"
            ) from e

        new_doc.status = "UPLOADED"
        await db.commit()

        # enqueue task with cleanup fallback
        try:
            await self._enqueue_parsing_task(db, new_doc)
        except HTTPException as e:
            logger.warning(f"Queueing failed for doc {new_doc.id}. Cleaning up S3.")
            try:
                await storage_service.delete_file(s3_key)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up S3 file {s3_key}: {cleanup_error}")
            raise e

        return new_doc

    async def get_document_by_id(self, db: AsyncSession, doc_id: int) -> Document:
        query = select(Document).where(Document.id == doc_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        return doc

    async def reprocess_document(self, db: AsyncSession, doc_id: int) -> Document:
        """
        Resets the document state and dispatches it to the background worker
        for a fresh AI extraction. Prevents reprocessing of active or
        completed documents.
        """
        query = select(Document).where(Document.id == doc_id).with_for_update()
        doc = (await db.execute(query)).scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        invalid_states = {"PENDING", "UPLOADED", "PROCESSING", "COMPLETED"}
        if doc.status in invalid_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reprocess document in current state: {doc.status}",
            )

        doc.status = "UPLOADED"
        doc.parsed_json = None
        doc.embedding = None

        try:
            await db.commit()
            await db.refresh(doc)
        except Exception as e:
            logger.error(f"Database error during document reset for doc {doc_id}: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500, detail="Database error while resetting document"
            ) from e

        await self._enqueue_parsing_task(db, doc)

        logger.info("Successfully enqueued document %s for reprocessing.", doc.id)
        return doc

    async def get_document_for_review(
        self, db: AsyncSession, document_id: int
    ) -> DocumentReviewResponse:
        """
        Retrieves a document and its AI-parsed data, mapping it safely
        into the schema required by the frontend for the approval form.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            logger.warning(
                f"Review requested for non-existent document ID: {document_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )

        if doc.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already approved and processing is completed.",
            )

        raw_data = doc.parsed_json or {}

        personal_info = raw_data.get("personal_info", {})
        hard_facts = raw_data.get("hard_facts", {})
        keywords = raw_data.get("keywords", {})
        semantic_text = raw_data.get("semantic_text", {})

        raw_experiences = raw_data.get("experience", [])
        mapped_experiences = [
            WorkExperienceApproveSchema(
                company=exp.get("company") or "Unknown",
                position=exp.get("position") or "Unknown",
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                description=exp.get("description"),
            )
            for exp in raw_experiences
        ]

        mapped_skills = [
            SkillApproveSchema(name=skill_name)
            for skill_name in keywords.get("skills", [])
        ]

        draft_data = CandidateReviewDraft(
            first_name=personal_info.get("first_name"),
            last_name=personal_info.get("last_name"),
            email=personal_info.get("email"),
            phone=personal_info.get("phone"),
            location=hard_facts.get("location"),
            total_experience_years=hard_facts.get("total_experience_years", 0),
            summary=semantic_text.get("professional_summary"),
            skills=mapped_skills,
            experiences=mapped_experiences,
            job_offer_id=getattr(doc, "job_offer_id", None),
        )

        return DocumentReviewResponse(
            document_id=doc.id,
            status=doc.status,
            candidate_id=doc.candidate_id,
            extracted_data=draft_data,
        )

    async def approve_document(
        self, db: AsyncSession, doc_id: int, data: ApprovedCandidateData
    ) -> dict:
        query = select(Document).where(Document.id == doc_id).with_for_update()
        doc = (await db.execute(query)).scalar_one_or_none()

        if not doc or doc.status != "AWAITING_REVIEW":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document not found or already processed.",
            )

        try:
            # atomic UPSERT for Candidate
            cand_data = data.model_dump(
                exclude={"experiences", "skills", "job_offer_id"}
            )
            cand_stmt = (
                pg_insert(Candidate)
                .values(**cand_data)
                .on_conflict_do_update(
                    index_elements=["email"],
                    set_={k: v for k, v in cand_data.items() if v is not None},
                )
                .returning(Candidate.id)
            )
            candidate_id = (await db.execute(cand_stmt)).scalar_one()

            # fetch candidate with skills loaded for M2M update
            candidate = await db.get(
                Candidate, candidate_id, options=[selectinload(Candidate.skills)]
            )

            # sync Work Experience
            await db.execute(
                delete(WorkExperience).where(
                    WorkExperience.candidate_id == candidate_id
                )
            )

            if data.experiences:
                new_experiences = [
                    WorkExperience(
                        candidate_id=candidate_id,
                        company=exp.company,
                        position=exp.position,
                        start_date=exp.start_date,
                        end_date=exp.end_date,
                        description=exp.description,
                    )
                    for exp in data.experiences
                ]
                db.add_all(new_experiences)

            # batch Sync Skills
            if data.skills:
                skill_names = {s.name.strip().lower() for s in data.skills}

                await db.execute(
                    pg_insert(Skill)
                    .values([{"name": name} for name in skill_names])
                    .on_conflict_do_nothing()
                )

                skills_query = select(Skill).where(Skill.name.in_(skill_names))
                candidate.skills = list(
                    (await db.execute(skills_query)).scalars().all()
                )
            else:
                candidate.skills = []

            # link Document and Application
            doc.candidate_id = candidate_id
            doc.status = "APPROVED"

            app_query = select(Application).where(Application.document_id == doc.id)
            application = (await db.execute(app_query)).scalar_one_or_none()

            if application:
                application.candidate_id = candidate_id
                application.status = "NEW"
            elif data.job_offer_id:
                db.add(
                    Application(
                        candidate_id=candidate_id,
                        job_offer_id=data.job_offer_id,
                        document_id=doc.id,
                        status="NEW",
                    )
                )

            await db.commit()
            await db.refresh(doc)

        except Exception as e:
            logger.error(
                f"Database error during document approval for doc {doc_id}: {e}"
            )
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while approving the document.",
            ) from e

        # background Task Trigger
        await self._enqueue_embedding_task(db, doc)

        return {
            "message": "Candidate approved successfully. Vectorization started.",
            "candidate_id": candidate_id,
        }

    async def _enqueue_embedding_task(self, db: AsyncSession, doc: Document) -> None:
        """Creates the embedding task payload and enqueues it.
        Reverts DB state on failure."""
        task = GenerateEmbeddingsTask(document_id=doc.id)

        job = await queue_service.enqueue_generate_embeddings(task.model_dump())

        if not job:
            logger.critical(
                f"FATAL: Redis rejected embedding task for document {doc.id}."
            )
            doc.status = "FAILED"
            try:
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to update status to FAILED for doc {doc.id}: {e}")
                await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Service temporarily unavailable. "
                    "Document approved but vectorization failed."
                ),
            )

    async def get_document_download_stream(self, db: AsyncSession, doc_id: int):
        doc = await self.get_document_by_id(db, doc_id)
        file_stream = storage_service.stream_file(doc.s3_key)
        return file_stream, doc.content_type, doc.filename

    async def delete_document(self, db: AsyncSession, doc_id: int) -> dict:
        """
        Hard delete: Removes the physical file from S3 and the record from the database.
        """
        doc = await self.get_document_by_id(db, doc_id)

        try:
            await storage_service.delete_file(doc.s3_key)
        except Exception as e:
            logger.error(f"S3 deletion failed for doc {doc_id}. Error: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to delete file from S3 storage."
            ) from e

        try:
            await db.delete(doc)
            await db.commit()
            logger.info("Successfully hard-deleted document %s from database.", doc_id)
        except Exception as e:
            logger.error(f"Database error during hard delete for doc {doc_id}: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while deleting the document.",
            ) from e

        return {"message": f"Document {doc_id} has been permanently deleted."}

    async def stream_document_status(self, doc: Document) -> AsyncGenerator[str, None]:
        """
        Subscribes to Redis PubSub and yields SSE-formatted status updates.
        """
        redis_client = None
        pubsub = None
        channel_name = f"document_status_{doc.id}"
        final_statuses = {
            "COMPLETED",
            "FAILED",
            "DUPLICATE",
            "REJECTED",
            "REQUIRES_MANUAL_REVIEW",
        }

        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()

            if doc.status in final_statuses:
                payload = {"status": doc.status, "document_id": doc.id}
                yield f"data: {json.dumps(payload)}\n\n"
                return

            await pubsub.subscribe(channel_name)
            logger.info(f"SSE Subscribed to Redis channel: {channel_name}")

            payload = {"status": doc.status, "document_id": doc.id}
            yield f"data: {json.dumps(payload)}\n\n"

            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"

                    parsed_data = json.loads(data)
                    if parsed_data.get("status") in final_statuses:
                        logger.info(f"Closing SSE connection for doc {doc.id}")
                        break

        except asyncio.CancelledError:
            logger.info(f"Client cleanly disconnected from SSE stream for doc {doc.id}")

        except Exception as e:
            logger.error(f"Unexpected error in SSE stream for doc {doc.id}: {e}")
            yield f"data: {json.dumps({'error': 'Internal stream error'})}\n\n"

        finally:
            if pubsub:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            if redis_client:
                await redis_client.aclose()

    async def _enqueue_parsing_task(self, db: AsyncSession, doc: Document) -> None:
        """Creates the task payload and enqueues it. Reverts DB state on failure."""
        task = ParseCVTask(document_id=doc.id, s3_key=doc.s3_key, filename=doc.filename)
        job = await queue_service.enqueue_parse_cv(task.model_dump())

        if not job:
            logger.critical(f"FATAL: Redis rejected task for document {doc.id}.")
            doc.status = "FAILED"
            try:
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to update status to FAILED for doc {doc.id}: {e}")
                await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": (
                        "Service temporarily unavailable. "
                        "Document saved but not processed."
                    ),
                    "document_id": doc.id,
                },
            )


document_service = DocumentService()
