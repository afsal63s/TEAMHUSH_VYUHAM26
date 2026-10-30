import type { CoverKind } from '../../data/placeholder'

// Decorative course covers from the design reference (640x230, cropped to fill).
const svgProps = {
  viewBox: '0 0 640 230',
  preserveAspectRatio: 'xMidYMid slice',
  width: '100%',
  height: 230,
  'aria-hidden': true,
  style: { display: 'block' },
} as const

function NeuralNet() {
  return (
    <svg {...svgProps}>
      <g stroke="#9CC7EE" strokeWidth="1.5">
        <path d="M150 50 L320 40M150 50 L320 115M150 50 L320 190M150 115 L320 40M150 115 L320 115M150 115 L320 190M150 180 L320 40M150 180 L320 115M150 180 L320 190M320 40 L490 80M320 115 L490 80M320 190 L490 80M320 40 L490 150M320 115 L490 150M320 190 L490 150" />
      </g>
      <g fill="#0770C9">
        <circle cx="150" cy="50" r="13" />
        <circle cx="150" cy="115" r="13" />
        <circle cx="150" cy="180" r="13" />
      </g>
      <g fill="#3D9AE8">
        <circle cx="320" cy="40" r="13" />
        <circle cx="320" cy="115" r="13" />
        <circle cx="320" cy="190" r="13" />
      </g>
      <g fill="#0A4C8A">
        <circle cx="490" cy="80" r="13" />
        <circle cx="490" cy="150" r="13" />
      </g>
    </svg>
  )
}

function Matrix() {
  return (
    <svg {...svgProps}>
      <g fill="#CFE4F8">
        <rect x="110" y="50" width="56" height="56" rx="8" />
        <rect x="174" y="50" width="56" height="56" rx="8" />
        <rect x="110" y="114" width="56" height="56" rx="8" />
        <rect x="174" y="114" width="56" height="56" rx="8" />
      </g>
      <g fill="#3D9AE8">
        <rect x="300" y="50" width="56" height="56" rx="8" />
        <rect x="364" y="114" width="56" height="56" rx="8" />
      </g>
      <g fill="#0770C9">
        <rect x="364" y="50" width="56" height="56" rx="8" />
        <rect x="300" y="114" width="56" height="56" rx="8" />
      </g>
      <path
        d="M250 110h30m-10-10 10 10-10 10"
        fill="none"
        stroke="#0A4C8A"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <g fill="#0A4C8A">
        <rect x="480" y="50" width="56" height="56" rx="8" />
        <rect x="544" y="114" width="56" height="56" rx="8" />
      </g>
    </svg>
  )
}

function Code() {
  return (
    <svg {...svgProps}>
      <rect x="110" y="34" width="420" height="162" rx="12" fill="#FFFFFF" stroke="#CFE4F8" />
      <g fill="#CFE4F8">
        <circle cx="134" cy="56" r="5" />
        <circle cx="152" cy="56" r="5" />
        <circle cx="170" cy="56" r="5" />
      </g>
      <g strokeLinecap="round" strokeWidth="9">
        <path d="M140 90h70" stroke="#0770C9" />
        <path d="M222 90h120" stroke="#9CC7EE" />
        <path d="M160 116h100" stroke="#3D9AE8" />
        <path d="M272 116h60" stroke="#CFE4F8" />
        <path d="M160 142h140" stroke="#9CC7EE" />
        <path d="M140 168h90" stroke="#0A4C8A" />
      </g>
    </svg>
  )
}

function Attention() {
  return (
    <svg {...svgProps}>
      <g fill="#0770C9">
        <rect x="120" y="150" width="56" height="30" rx="8" />
        <rect x="200" y="150" width="56" height="30" rx="8" />
        <rect x="280" y="150" width="56" height="30" rx="8" />
        <rect x="360" y="150" width="56" height="30" rx="8" />
        <rect x="440" y="150" width="56" height="30" rx="8" />
      </g>
      <g fill="none" stroke="#3D9AE8" strokeWidth="3" strokeLinecap="round">
        <path d="M388 148C388 70 228 70 228 148" />
        <path d="M388 148C388 100 308 100 308 148" stroke="#9CC7EE" />
        <path d="M388 148C388 40 148 40 148 148" stroke="#CFE4F8" />
        <path d="M388 148C388 108 468 108 468 148" stroke="#0A4C8A" />
      </g>
    </svg>
  )
}

export function Cover({ kind }: { kind: CoverKind }) {
  switch (kind) {
    case 'nn':
      return <NeuralNet />
    case 'matrix':
      return <Matrix />
    case 'code':
      return <Code />
    case 'attention':
      return <Attention />
  }
}
