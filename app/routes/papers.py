"""Paper Lab endpoints: upload a paper, get structured insights + legitimacy report."""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.paper_lab.pipeline import analyze
from app.paper_lab.replication import list_recipes
from app.paper_lab.schema import PaperInsights

router = APIRouter()


@router.get("/papers/recipes")
def recipes():
    """Replication recipes that can be run against a paper's insights."""
    return list_recipes()


@router.post("/papers/analyze")
async def analyze_paper(
    file: UploadFile = File(..., description="Paper PDF (or .txt)"),
    use_llm: bool = Form(True),
    replicate: Optional[str] = Form(None, description="Recipe name, e.g. factor-fluctuation"),
    insights_json: Optional[str] = Form(None, description="Optional curated insights JSON to use instead of extraction"),
):
    """Extract insights, run consistency / citation / methodology checks and (optionally) replicate."""
    suffix = Path(file.filename or "paper.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        ins = PaperInsights.model_validate_json(insights_json) if insights_json else None
        result = await run_in_threadpool(analyze, path, insights=ins, use_llm=use_llm, recipe=replicate)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Paper analysis failed: {e}")
    finally:
        Path(path).unlink(missing_ok=True)

    return {
        "insights": result.insights.model_dump(),
        "legitimacy": result.legitimacy.model_dump(),
        "suggested_recipes": result.suggested_recipes,
        "replication_tables": {k: v.reset_index().astype(str).to_dict(orient="records")
                               for k, v in (result.replication.tables.items() if result.replication else [])
                               if k != "exhibit4_rolling_120m"},
        "report_markdown": result.report_md,
    }
