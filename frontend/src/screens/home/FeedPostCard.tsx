import { Link } from 'react-router'
import mark from '../../assets/mark.png'
import { Icon } from '../../components/Icon'
import type { FeedPost, PostStatus } from '../../data/placeholder'
import { reviewLink } from '../../routes'
import { Cover } from './Covers'

const badges: Record<PostStatus, { label: string; className: string }> = {
  progress: { label: 'In progress', className: 'badge badge--progress' },
  review: { label: 'Review due', className: 'badge badge--review' },
  done: { label: 'Completed', className: 'badge badge--done' },
}

export function FeedPostCard({ post }: { post: FeedPost }) {
  const badge = badges[post.status]
  const chat = `/chat/${post.chatId}`

  return (
    <article className="card post">
      <header className="post__header">
        <div className="av post__agent" aria-hidden="true">
          <img src={mark} alt="" />
        </div>
        <div className="post__byline">
          <div className="post__author">
            OnlyNerds Agent
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="11" fill="#0770C9" />
              <path
                d="m7 12.5 3.2 3.2L17 9"
                fill="none"
                stroke="#FFFFFF"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="post__meta">
            {post.topic} · {post.time}
          </div>
        </div>
        <span className={badge.className}>{badge.label}</span>
        <button className="icon-btn" type="button" aria-label="More options">
          <Icon name="more" size={20} />
        </button>
      </header>

      <div className="post__text">{post.text}</div>

      <Link to={chat} className="post__cover" aria-label="Open course">
        <Cover kind={post.cover} />
        <div className="post__pills">
          <span className="pill">
            <Icon name="book" size={14} strokeWidth={2} />
            {post.chapters}
          </span>
          <span className="pill">
            <Icon name="clock" size={14} strokeWidth={2} />
            {post.duration}
          </span>
        </div>
      </Link>

      <div className="post__summary">
        <div className="post__summary-main">
          <h2 className="post__title">{post.title}</h2>
          <div className="post__segments" aria-hidden="true">
            {Array.from({ length: post.totalSegments }, (_, i) => (
              <span key={i} className={i < post.doneSegments ? 'seg seg--done' : 'seg'} />
            ))}
          </div>
          <div className="post__stats">
            <span>{post.progress}</span>
            <span>
              Retention: <strong>{post.retention}</strong>
            </span>
            <span>
              Next review: <strong>{post.next}</strong>
            </span>
          </div>
        </div>
        <Link to={post.status === 'review' ? reviewLink(post.topic) : chat} className="btn btn-soft">
          {post.cta}
        </Link>
      </div>

      <footer className="post__footer">
        <Link to={reviewLink(post.topic)} className="icon-btn" aria-label="Quiz me on this course">
          <Icon name="quiz" />
          Quiz
        </Link>
        <Link to={chat} className="icon-btn" aria-label="Discuss with tutor">
          <Icon name="chat" />
          {post.chats}
        </Link>
        <button className="icon-btn" type="button" aria-label="Schedule a review">
          <Icon name="repeat" />
          Review
        </button>
        <span className="post__spacer" />
        <button className="icon-btn" type="button" aria-label="Save">
          <Icon name="bookmark" />
        </button>
        <button className="icon-btn" type="button" aria-label="Share">
          <Icon name="share" />
        </button>
      </footer>
    </article>
  )
}
