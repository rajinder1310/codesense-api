import logging
from fastapi import APIRouter, HTTPException, status
from models.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from services.code_analyzer import analyze_code

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Analysis"],
    responses={
        422: {"model": ErrorResponse, "description": "Code has syntax errors"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.post("/analyze", response_model=AnalyzeResponse, status_code=200, summary="Analyze Python source code")
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Parses submitted Python code and returns quality metrics."""

    if request.language.lower() != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{request.language}' is not supported. Only 'python' is accepted.",
        )

    try:
        result = await analyze_code(request.code)
    except SyntaxError as exc:
        logger.warning("Syntax error in submitted code: %s", exc)
        raise HTTPException(status_code=422, detail=f"Syntax error in submitted code: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(status_code=500, detail="Internal error while analysing code.") from exc

    return AnalyzeResponse(
        complexity_score=result.complexity_score,
        edge_cases_missing=result.edge_cases_missing,
        quality_score=result.quality_score,
        suggestions=result.suggestions,
        lines_of_code=result.lines_of_code,
    )
