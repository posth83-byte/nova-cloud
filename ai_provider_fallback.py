"""Budget-aware retries for OpenRouter when the remaining credit cap is too low."""

import time


def is_openrouter_inflight_budget_error(error):
    message = str(error).casefold()
    return (
        ("openrouter api-fel 402" in message or "http 402" in message)
        and (
            "in_flight_budget_exhausted" in message
            or "retry after in-flight requests settle" in message
        )
    )


def is_openrouter_budget_error(error):
    message = str(error).casefold()
    return (
        ("openrouter api-fel 402" in message or "http 402" in message)
        and (
            "weight_exceeds_budget" in message
            or "maximum cost exceeds your available credits" in message
            or is_openrouter_inflight_budget_error(error)
        )
    )


def run_openrouter_with_budget_fallback(
    ask_function,
    message,
    system_prompt,
    max_tokens=2048,
    json_mode=False,
    image_data="",
):
    """Retry only credit-budget 402s, progressively lowering the output cap."""
    try:
        requested = int(max_tokens)
    except (TypeError, ValueError) as error:
        raise ValueError("max_tokens måste vara ett heltal.") from error
    if requested < 1:
        raise ValueError("max_tokens måste vara minst 1.")

    budgets = []
    for candidate in (requested, min(requested, 2048), min(requested, 1024), min(requested, 512)):
        if candidate not in budgets:
            budgets.append(candidate)

    for index, budget in enumerate(budgets):
        inflight_retries = 0
        while True:
            try:
                answer = ask_function(message, system_prompt, budget, json_mode, image_data)
                return answer, budget
            except Exception as error:
                # OpenRouter can temporarily reject a request while concurrent calls
                # reserve the remaining budget. Wait briefly for those calls to settle
                # before lowering the token cap or surfacing the provider error.
                if is_openrouter_inflight_budget_error(error) and inflight_retries < 2:
                    time.sleep(2 ** (inflight_retries + 1))
                    inflight_retries += 1
                    continue
                if not is_openrouter_budget_error(error) or index == len(budgets) - 1:
                    raise
                break

    raise RuntimeError("OpenRouter kunde inte svara inom tillgänglig tokenbudget.")
