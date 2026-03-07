from agentrag.planner import build_query_plan


def test_query_plan_extracts_code_python_intent():
    plan = build_query_plan("show python function for upsert")
    assert plan.intent == "explain_function"
    assert plan.node_type == "code"
    assert plan.language == "python"
    assert plan.access_level == "internal"


def test_query_plan_extracts_symbol():
    plan = build_query_plan("explain this symbol:calculate_roi in docs")
    assert plan.symbol_name == "calculate_roi"


def test_query_plan_extracts_symbol_from_natural_phrase():
    plan = build_query_plan("please explain function calculate_roi in python")
    assert plan.symbol_name == "calculate_roi"
