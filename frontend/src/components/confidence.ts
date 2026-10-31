// Confidence picker values shared by the assessment and lesson questions.

export const CONFIDENCE_LABELS = ['Not sure', 'Fairly sure', 'Certain'] as const
/** Confidence button index -> API value. */
export const CONFIDENCE_VALUES = ['low', 'medium', 'high'] as const

/** API confidence value -> button index (for AnswerReview). */
export const confidenceIndex = (c: string | null | undefined) => {
  const i = CONFIDENCE_VALUES.indexOf(c as (typeof CONFIDENCE_VALUES)[number])
  return i < 0 ? undefined : i
}

/** Shared pick/confidence update: a new answer clears confidence; re-clicking the chosen confidence clears it. */
export function nextConfidence(
  prevPicked: number | undefined,
  prevConfidence: number | undefined,
  option: number,
  confidence: number | undefined,
) {
  const same = prevPicked === option
  if (confidence === undefined) return same ? prevConfidence : undefined
  return same && prevConfidence === confidence ? undefined : confidence
}
