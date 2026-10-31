import type { CourseSummary } from '../../api/types'

export type PostStatus = 'progress' | 'review' | 'done'

/** Home filter bucket (guide: Review if overdue; Done if everything mastered; else In progress). */
export function postStatus(c: CourseSummary): PostStatus {
  if ((c.overdue_count ?? 0) > 0) return 'review'
  if ((c.concept_count ?? 0) > 0 && c.mastered === c.concept_count) return 'done'
  return 'progress'
}
