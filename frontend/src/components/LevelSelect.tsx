import { useEffect, useRef, useState } from 'react'
import { levels, type LevelKey } from '../data/placeholder'
import { Icon } from './Icon'
import './LevelSelect.css'

// "Level: X" chip that opens a menu of the four levels.
export function LevelSelect({ value, onChange }: { value: LevelKey; onChange: (level: LevelKey) => void }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const current = levels.find((l) => l.key === value)!

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [open])

  return (
    <div className="level-select" ref={root}>
      <button
        type="button"
        className="chip level-select__button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="bars" size={16} strokeWidth={1.8} />
        Level: {current.name}
        <Icon name="chevronDown" size={14} strokeWidth={2} />
      </button>
      {open && (
        <ul className="level-select__menu" role="listbox" aria-label="Your level">
          {levels.map((l) => (
            <li key={l.key} role="option" aria-selected={l.key === value}>
              <button
                type="button"
                className={`level-select__option${l.key === value ? ' level-select__option--on' : ''}`}
                onClick={() => {
                  onChange(l.key)
                  setOpen(false)
                }}
              >
                <span className="lvl__bars" aria-hidden="true">
                  {[5, 8, 12, 16].map((h, i) => (
                    <span key={h} className={i < l.bars ? 'lvl__bar lvl__bar--on' : 'lvl__bar'} style={{ height: h }} />
                  ))}
                </span>
                <span className="level-select__text">
                  <span className="level-select__name">{l.name}</span>
                  <span className="level-select__desc">{l.desc}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
