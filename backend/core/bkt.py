from schemas.learner import BktParams

def bkt_update(
    p: float, 
    correct: bool, 
    params: BktParams, 
    confidence: str | None = None
) -> float:
    """
    Updates the probability of mastery using Bayesian Knowledge Tracing.
    """
    # Handle the confidence rule: low confidence correct = likely guess
    p_guess = params.p_guess
    if correct and confidence == "low":
        p_guess = 0.5 

    if correct:
        # P(L | correct)
        p_given_obs = (p * (1 - params.p_slip)) / (
            p * (1 - params.p_slip) + (1 - p) * p_guess
        )
    else:
        # P(L | incorrect)
        p_given_obs = (p * params.p_slip) / (
            p * params.p_slip + (1 - p) * (1 - p_guess)
        )
        
    # P(L_n+1) = P(L | obs) + (1 - P(L | obs)) * P_learn
    p_next = p_given_obs + (1 - p_given_obs) * params.p_learn
    return p_next