from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.v1.deps import get_current_user, get_document_service
from app.core.constants import DocumentType
from app.models.user_model import UserModel
from app.schemas.document_schema import DocumentListResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/profile/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    content = await file.read()
    document = await document_service.upload_document(
        user_id=current_user.id,
        document_type=document_type,
        file_name=file.filename,
        mime_type=file.content_type,
        content=content,
    )
    return DocumentResponse(
        id=str(document.id),
        document_type=document.document_type,
        file_name=document.file_name,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        rejection_reason=document.rejection_reason,
        uploaded_at=document.uploaded_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: UserModel = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    documents = await document_service.list_documents(current_user.id)
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=str(d.id),
                document_type=d.document_type,
                file_name=d.file_name,
                mime_type=d.mime_type,
                size_bytes=d.size_bytes,
                status=d.status,
                rejection_reason=d.rejection_reason,
                uploaded_at=d.uploaded_at,
            )
            for d in documents
        ]
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: UserModel = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    await document_service.delete_document(current_user.id, document_id)
    return None
