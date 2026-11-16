
import json

from google.genai import types
from pydantic import BaseModel, Field

from llm import client, DEFAULT_MODEL


class ClaimAssessment(BaseModel):
    claim: str
    supported: bool
    explanation: str


class JudgeResult(BaseModel):
    claims: list[ClaimAssessment]
    recommended_decision: str
    decision_quality_score: float = Field(ge=0, le=1)
    decision_explanation: str


def evaluate_investigation(report, analysis, policies):
    evidence = {
        "transaction_analysis": analysis,
        "retrieved_policies": policies,
    }

    prompt = f"""
You are an independent AML investigation quality evaluator.

Evaluate the investigation report using ONLY the
transaction evidence and AML policies provided.

INVESTIGATION REPORT:
{report}

SUPPORTING EVIDENCE:
{json.dumps(evidence, default=str)}

EVALUATION 1: GROUNDEDNESS
- Identify material factual claims in the report.
- Check each claim against the supporting evidence.
- Mark unsupported, contradicted or unverifiable
  claims as supported=false.
- Do not assume suspicious activity proves a crime.

EVALUATION 2: DECISION QUALITY
- Identify the action recommended in the report.
- Assess whether it is appropriate given the evidence,
  risk indicators and AML policies.
- Consider missed risks, premature closure, unjustified
  escalation and uncertainty.
- If no explicit recommendation exists, explain that
  and assign a low decision quality score.
- Return a score between 0 and 1 with justification.

Do not invent facts, transactions or policy requirements.
"""

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=JudgeResult,
        ),
    )

    result = JudgeResult.model_validate_json(response.text)

    claims = result.claims

    groundedness = (
        sum(claim.supported for claim in claims) / len(claims)
        if claims else 0.0
    )

    return {
        "groundedness_score": round(groundedness, 3),
        "decision_quality_score": result.decision_quality_score,
        "recommended_decision": result.recommended_decision,
        "decision_explanation": result.decision_explanation,
        "claims": [claim.model_dump() for claim in claims],
    }
