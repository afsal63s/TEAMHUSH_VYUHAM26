// Link builders shared by the screens.

/** The first (diagnostic) assessment of a course. */
export const diagnosticLink = (courseId: string) => `/assessment?course=${encodeURIComponent(courseId)}`

/** A spaced review: the backend picks the concept (GET .../next). */
export const reviewLink = (courseId: string) => `/assessment?mode=review&course=${encodeURIComponent(courseId)}`

/** Create a course for a topic and level, then watch it build. */
export const buildLink = (topic: string, levelKey: string) =>
  `/build?topic=${encodeURIComponent(topic)}&level=${encodeURIComponent(levelKey)}`

/** Watch an existing course build (or show it ready). */
export const buildCourseLink = (courseId: string) => `/build?course=${encodeURIComponent(courseId)}`

export const chatLink = (courseId: string) => `/chat/${encodeURIComponent(courseId)}`
