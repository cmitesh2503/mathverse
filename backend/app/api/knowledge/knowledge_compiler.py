from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.knowledge_factory.compiler import (
    KnowledgeCompiler
)

router = APIRouter()

compiler = KnowledgeCompiler()


class KnowledgeCompileRequest(BaseModel):

    bucket_name: str

    blob_name: str

    document_type: str = "curriculum"

@router.post(
    "/compile",
    tags=["Knowledge Factory"]
)
async def compile_knowledge(
    request: KnowledgeCompileRequest
):

    try:

        result = compiler.compile(

            bucket_name=request.bucket_name,

            blob_name=request.blob_name,

            document_type=request.document_type

        )

        if not result["success"]:

            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )

        return result

    except HTTPException:

        raise

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )