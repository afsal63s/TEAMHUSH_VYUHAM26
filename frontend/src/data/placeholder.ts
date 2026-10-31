// Static values that do not come from the backend.

/** The signed-in learner shown in the sidebar and composer (the backend has one shared user, no profile). */
export const user = { name: 'Alex Rivera', initials: 'AR' }

/** Self-assessed levels; `key` is what the API takes. */
export const levels = [
  { key: 'novice', name: 'Novice', bars: 1, desc: 'Brand new to this topic. Start from first principles.' },
  { key: 'beginner', name: 'Beginner', bars: 2, desc: 'I know a few basics, but only the surface.' },
  { key: 'intermediate', name: 'Intermediate', bars: 3, desc: 'I can apply the ideas. I want to find what I am missing.' },
  { key: 'advanced', name: 'Advanced', bars: 4, desc: 'I am comfortable with the topic. Test the edges.' },
] as const

export type LevelKey = (typeof levels)[number]['key']
