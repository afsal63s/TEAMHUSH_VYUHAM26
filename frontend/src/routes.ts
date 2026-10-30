// Link builders shared by the screens.

/** Spaced-review quiz on a topic (same assessment screen, review wording). */
export const reviewLink = (topic: string) =>
  `/assessment?mode=review&topic=${encodeURIComponent(topic)}`

/** Diagnostic for a new topic at a level; `courseId` ties the result to a built course. */
export const diagnosticLink = (topic: string, level: string, courseId?: string) =>
  `/assessment?topic=${encodeURIComponent(topic)}&level=${encodeURIComponent(level)}` +
  (courseId ? `&course=${encodeURIComponent(courseId)}` : '')

/** Course-building screen shown after New chat. */
export const buildLink = (topic: string, levelKey: string) =>
  `/build?topic=${encodeURIComponent(topic)}&level=${encodeURIComponent(levelKey)}`
