
import time
import json
import re
from datetime import datetime, timezone
from fraud_investigation.agents.investigator import SYSTEM_INSTRUCTION
import uuid
from fraud_investigation.rag.policy_retriever import (
    search_investigation_and_disposition_policies
)

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from fraud_investigation.observability.telemetry import get_tracer

from fraud_investigation.governance.guardrails import (
    validate_investigation,
    validate_policy_search,
    sanitize_trace,
)

from google.genai import types

from llm import client, DEFAULT_MODEL
from fraud_investigation.tools.transaction_analysis import analyze_transactions


# Declare the tool's interface to Gemini
ANALYSIS_TOOL = types.FunctionDeclaration(
    name="analyze_transactions",
    description=(
        "Retrieve historical transaction behaviour and analyse "
        "transactions associated with a specific AML alert."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "customer_id": {"type": "STRING"},
            "alert_id": {"type": "STRING"},
        },
        "required": ["customer_id", "alert_id"],
    },
)


POLICY_TOOL = types.FunctionDeclaration(
    name="search_aml_policy",
    description=(
            "Search AML policies relevant to suspicious transaction patterns, "
            "including rapid movement of funds, structuring, unusual transaction "
            "volumes, international transfers, customer due diligence, "
            "investigation procedures, and escalation requirements. "
            "Generate a focused query based on the specific alert and "
            "available transaction evidence."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Natural-language policy search query"
            },
            "top_k": {
                "type": "INTEGER",
                "description": "Number of policy sections to retrieve (1-6)"
            },
        },
        "required": ["query"],
    },
)


tracer = get_tracer()

def _run_investigation_impl(customer_id: str, alert_id: str) -> dict:
    """Multi-tool AML investigation with controlled execution and tracing."""

    validation = validate_investigation(customer_id, alert_id)

    if "error" in validation:
        return {
            "error": validation["error"],
            "trace": [{
                "event": "guardrail_blocked",
                "details": {"reason": validation["error"]}
            }]
        }    


    trace_id = str(uuid.uuid4())
    trace = []
    started = time.perf_counter()
    analysis = None
    retrieved_policies = []
    policy_diagnostics = None

    def log_event(event: str, details: dict):
        trace.append({
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": sanitize_trace(details),
        })

    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[
            ANALYSIS_TOOL,
            POLICY_TOOL
        ])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        system_instruction=(
            SYSTEM_INSTRUCTION
            + "\nInvestigate the AML alert using available tools. "
            "First obtain transaction evidence and identify the specific "
            "suspicious patterns. Then formulate focused AML policy search "
            "queries using those findings. Retrieve policies relevant to "
            "the observed behaviour, not just generic escalation procedures. "
            "Use policy evidence to support the final assessment and cite "
            "retrieved policy IDs. Never invent evidence or policy references."
        ),
        temperature=0.2,
    )

    chat = client.chats.create(model=DEFAULT_MODEL, config=config)

    log_event("investigation_started", {
        "customer_id": customer_id,
        "alert_id": alert_id
    })

    try:
        with tracer.start_as_current_span("gemini.initial_investigation"):
            response = chat.send_message(
                f"Investigate AML alert {alert_id} for customer {customer_id}. "
                "Prepare a concise, evidence-grounded investigation report."
            )

        # Allow multiple tool-calling rounds
        for round_number in range(1, 7):
            calls = response.function_calls or []

            if not calls:
                if analysis is None:
                    return {
                        "error": "Investigation completed without transaction evidence.",
                        "trace": trace
                    }

                log_event("investigation_completed", {
                    "total_duration_ms": round(
                        (time.perf_counter() - started) * 1000, 2
                    ),
                    "tool_rounds": round_number - 1
                })

                report = response.text or "No report generated."
                recommended_action = extract_recommendation(report)
                
                return {
                    "report": report,
                    "recommended_action": recommended_action,
                    "analysis": analysis,
                    "retrieved_policies": retrieved_policies,
                    "policy_diagnostics": policy_diagnostics,
                    "trace": trace,
                    "trace_id": trace_id,
                }

            tool_responses = []

            for call in calls:
                args = dict(call.args or {})

                log_event("tool_requested", {
                    "tool": call.name,
                    "arguments": args,
                    "round": round_number
                })

                tool_started = time.perf_counter()

                if call.name == "analyze_transactions":
                    if args != {
                        "customer_id": customer_id,
                        "alert_id": alert_id
                    }:
                        result = {"error": "Invalid customer or alert arguments"}
                    else:
                        with tracer.start_as_current_span("tool.analyze_transactions") as span:
                            span.set_attribute("tool.name", "analyze_transactions")
                            result = analyze_transactions(customer_id, alert_id)
                            span.set_attribute("tool.success", "error" not in result)


                        if "error" not in result:
                            analysis = result

                elif call.name == "search_aml_policy":
                    query = args.get("query", "")
                    top_k = args.get("top_k", 3)


                    validation = validate_policy_search(query, top_k)

                    if "error" in validation:
                        result = {"error": validation["error"]}

                        log_event("guardrail_blocked", {
                            "tool": "search_aml_policy",
                            "reason": validation["error"]
                        })

                    else:
                        with tracer.start_as_current_span("tool.search_aml_policy") as span:
                            span.set_attribute("tool.name", "search_aml_policy")
                            span.set_attribute("rag.top_k", top_k)

                            result = search_investigation_and_disposition_policies(investigation_query=query, top_k=top_k)
                            span.set_attribute("tool.success", "error" not in result)

                        if "error" not in result:
                            retrieved_policies.extend(result["results"])
                            policy_diagnostics = result

                else:
                    result = {"error": "Tool not permitted"}

                log_event("tool_completed", {
                    "tool": call.name,
                    "duration_ms": round(
                        (time.perf_counter() - tool_started) * 1000, 2
                    ),
                    "success": "error" not in result,
                    "result_summary": (
                        list(result.keys()) if isinstance(result, dict) else []
                    )
                })

                log_event("preparing_tool_response", {
                    "tool": call.name
                })

                safe_result = json.loads(
                    json.dumps(result, default=str)
                )

                tool_responses.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": safe_result}
                    )
                )

            log_event("sending_tool_responses", {
                "count": len(tool_responses)
            })

            with tracer.start_as_current_span("gemini.process_tool_results") as span:
                span.set_attribute("agent.round", round_number)
                span.set_attribute("agent.tool_response_count", len(tool_responses))
                response = chat.send_message(tool_responses)

            log_event("gemini_response_received", {
                "round": round_number
            })                

                

        return {
            "error": "Maximum tool-calling rounds exceeded.",
            "trace": trace
        }

    except Exception as exc:
        import traceback

        error_details = traceback.format_exc()
        
        log_event("investigation_failed", {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": error_details
        })
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "trace": trace
        }



def run_investigation(customer_id: str, alert_id: str) -> dict:
    """Run an AML investigation inside an OpenTelemetry root span."""

    with tracer.start_as_current_span("aml.investigation") as span:
        span.set_attribute("agent.type", "aml_investigator")

        try:
            result = _run_investigation_impl(customer_id, alert_id)

            if "error" in result:
                span.set_status(
                    Status(StatusCode.ERROR, "Investigation failed")
                )
            else:
                span.set_attribute("agent.completed", True)

            return result

        except Exception:
            span.set_status(
                Status(StatusCode.ERROR, "Unexpected investigation error")
            )
            raise


RECOMMENDATION_CODES = {
    "escalate_case",
    "request_information",
    "close_alert",
}

def extract_recommendation(report: str) -> str | None:
    matches = re.findall(
        r"(?m)^\s*ACTION_CODE:\s*([a-z_]+)\s*$",
        report,
    )

    if len(matches) != 1:
        return None

    action = matches[0]

    return action if action in RECOMMENDATION_CODES else None
