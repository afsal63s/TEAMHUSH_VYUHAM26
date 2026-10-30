STYLE_ORDER = ["contrast", "worked_example", "analogy", "step_by_step"]


def choose_style(avoid_styles: list[str], has_targets: bool) -> str:
    """Deterministic lesson style: the first preferred style the learner has not seen.

    With targeted misconceptions "contrast" is tried first, otherwise "worked_example".
    If every style was used, return the first in the order.
    """
    first = "contrast" if has_targets else "worked_example"
    order = [first] + [s for s in STYLE_ORDER if s != first]
    return next((s for s in order if s not in avoid_styles), order[0])
