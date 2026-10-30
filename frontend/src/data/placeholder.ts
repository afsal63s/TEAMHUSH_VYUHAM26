// Placeholder content from design_reference/OnlyNerds.html until screens are wired to the API.

export type PostStatus = 'progress' | 'review' | 'done'
export type CoverKind = 'nn' | 'matrix' | 'code' | 'attention'

export interface FeedPost {
  id: string
  chatId: string
  status: PostStatus
  topic: string
  time: string
  text: string
  title: string
  chapters: string
  duration: string
  totalSegments: number
  doneSegments: number
  progress: string
  retention: string
  next: string
  cta: string
  chats: string
  cover: CoverKind
}

export const user = { name: 'Alex Rivera', initials: 'AR' }

export interface Chat {
  id: string
  title: string
  meta: string
  topic: string
  level: string
  courseTitle: string
  /** A spaced review is due now: the tutor chat offers the quiz. */
  reviewDue: boolean
  nextCheck: { month: string; day: string; when: string; what: string }
}

export const previousChats: Chat[] = [
  {
    id: 'backprop',
    title: 'Backpropagation diagnostic',
    meta: 'Now · Neural Networks',
    topic: 'Neural Networks',
    level: 'Intermediate',
    courseTitle: 'Backpropagation, from the chain rule up',
    reviewDue: false,
    nextCheck: { month: 'NOV', day: '3', when: 'In 3 days', what: 'Re-check: chain rule and vanishing gradients' },
  },
  {
    id: 'eigenvectors',
    title: 'Why eigenvectors matter',
    meta: 'Yesterday · Linear Algebra',
    topic: 'Linear Algebra',
    level: 'Beginner',
    courseTitle: 'Eigenvalues without the mystery',
    reviewDue: false,
    nextCheck: { month: 'NOV', day: '2', when: 'In 2 days', what: 'Re-check: eigenvalues and matrix multiplication' },
  },
  {
    id: 'python-lists',
    title: 'List vs tuple in Python',
    meta: 'Oct 27 · Python',
    topic: 'Python',
    level: 'Beginner',
    courseTitle: 'Python data structures in practice',
    reviewDue: true,
    nextCheck: { month: 'OCT', day: '31', when: 'Due now', what: 'Re-check: list slicing and dictionaries' },
  },
  {
    id: 'ww1',
    title: 'Causes of World War I',
    meta: 'Oct 24 · History',
    topic: 'History',
    level: 'Novice',
    courseTitle: 'The road to 1914',
    reviewDue: false,
    nextCheck: { month: 'NOV', day: '6', when: 'In 6 days', what: 'Re-check: alliances and the July crisis' },
  },
  {
    id: 'light-reactions',
    title: 'Light reactions, simply',
    meta: 'Oct 21 · Biology',
    topic: 'Biology',
    level: 'Novice',
    courseTitle: 'Photosynthesis, step by step',
    reviewDue: false,
    nextCheck: { month: 'NOV', day: '9', when: 'In 9 days', what: 'Re-check: light reactions and ATP' },
  },
  {
    id: 'attention',
    title: 'Attention, one query at a time',
    meta: 'Oct 28 · Transformers',
    topic: 'Transformers',
    level: 'Intermediate',
    courseTitle: 'Attention, one query at a time',
    reviewDue: true,
    nextCheck: { month: 'OCT', day: '31', when: 'Due now', what: 'Re-check: queries, keys and values' },
  },
]

export const findChat = (id: string | undefined): Chat =>
  previousChats.find((c) => c.id === id) ?? previousChats[0]


export const feedPosts: FeedPost[] = [
  {
    id: 'nn',
    chatId: 'backprop',
    status: 'progress',
    topic: 'Neural Networks',
    time: '12 min ago',
    text: 'From today’s chat: you treated each layer’s gradient as local. I built a short course that rebuilds backprop from the chain rule up.',
    title: 'Backpropagation, from the chain rule up',
    chapters: '4 chapters',
    duration: '38 min',
    totalSegments: 4,
    doneSegments: 1,
    progress: '1 of 4 done',
    retention: '—',
    next: 'Tomorrow',
    cta: 'Continue chapter 2',
    chats: '3',
    cover: 'nn',
  },
  {
    id: 'la',
    chatId: 'eigenvectors',
    status: 'progress',
    topic: 'Linear Algebra',
    time: 'Yesterday',
    text: 'You asked why eigenvectors matter. This course starts from what a matrix does to space, then builds up to eigenvalues.',
    title: 'Eigenvalues without the mystery',
    chapters: '5 chapters',
    duration: '52 min',
    totalSegments: 5,
    doneSegments: 2,
    progress: '2 of 5 done',
    retention: '—',
    next: 'In 3 days',
    cta: 'Continue chapter 3',
    chats: '5',
    cover: 'matrix',
  },
  {
    id: 'tf',
    chatId: 'attention',
    status: 'review',
    topic: 'Transformers',
    time: '3 days ago',
    text: 'Retention on this one has slipped since last week. A 5-minute recall check will bring it back before it fades.',
    title: 'Attention, one query at a time',
    chapters: '4 chapters',
    duration: '41 min',
    totalSegments: 4,
    doneSegments: 4,
    progress: 'Completed',
    retention: '72%',
    next: 'Today',
    cta: 'Start review',
    chats: '2',
    cover: 'attention',
  },
  {
    id: 'py',
    chatId: 'python-lists',
    status: 'done',
    topic: 'Python',
    time: 'Oct 26',
    text: 'You mastered lists, tuples and dictionaries. Strong recall after 7 days, so the next review is spaced further out.',
    title: 'Python data structures in practice',
    chapters: '6 chapters',
    duration: '1 hr 5 min',
    totalSegments: 6,
    doneSegments: 6,
    progress: 'Completed',
    retention: '88%',
    next: 'In 4 days',
    cta: 'Revisit course',
    chats: '4',
    cover: 'code',
  },
]

export const dueReviews = [
  { title: 'Gradient descent', due: 'Due now · 5 min' },
  { title: 'Matrix multiplication', due: 'Due now · 4 min' },
  { title: 'Python dictionaries', due: 'Due today · 3 min' },
  { title: 'Attention mechanism', due: 'Due tomorrow · 5 min' },
]

export const overdueReviews = [
  { title: 'Eigenvectors', late: '2 days overdue · Linear Algebra' },
  { title: 'Python list slicing', late: '4 days overdue · Python' },
  { title: 'Regularisation', late: '5 days overdue · Neural Networks' },
]

// ---- Assessment (the backend's diagnostic serves one question per concept, about 8) ----

export interface AssessmentQuestion {
  topic: string
  text: string
  options: string[]
  correct: number
}

export const assessment = {
  title: 'Backpropagation',
  level: 'Intermediate',
  questions: [
    {
      topic: 'Chain rule',
      text: 'A 3-layer network has loss L. What does ∂L/∂W₁ depend on?',
      options: [
        'Only the activations of layer 1',
        'The gradient of layer 1’s output alone',
        'Every downstream layer’s local gradient, multiplied together',
        'Only the final loss value',
      ],
      correct: 2,
    },
    {
      topic: 'Computational graphs',
      text: 'Why do we keep activations from the forward pass?',
      options: [
        'To speed up the next forward pass',
        'To compute local gradients during the backward pass',
        'To reduce the number of weights',
        'They are only kept for logging',
      ],
      correct: 1,
    },
    {
      topic: 'Vanishing gradients',
      text: 'With sigmoid activations in a deep stack, what typically happens to early-layer gradients?',
      options: ['They grow without bound', 'They stay the same size', 'They shrink toward zero', 'They flip sign at each layer'],
      correct: 2,
    },
    {
      topic: 'Matrix shapes',
      text: 'A layer maps 64 inputs to 32 outputs. What shape is the gradient of its weights?',
      options: [
        'The same shape as the weight matrix',
        'The same shape as the output vector',
        'Always a square matrix',
        'A single number',
      ],
      correct: 0,
    },
    {
      topic: 'Gradient descent',
      text: 'What happens if the learning rate is set too high?',
      options: [
        'Training always converges faster',
        'Updates can overshoot and the loss may diverge',
        'Gradients become exactly zero',
        'The model stops using bias terms',
      ],
      correct: 1,
    },
    {
      topic: 'Chain rule',
      text: 'If y = f(g(x)), what is dy/dx?',
      options: ['f′(x) · g′(x)', 'f′(g(x)) · g′(x)', 'f′(g′(x))', 'f(g(x)) · g′(x)'],
      correct: 1,
    },
    {
      topic: 'Vanishing gradients',
      text: 'Which choice helps reduce vanishing gradients in deep networks?',
      options: [
        'Using ReLU-style activations',
        'Using sigmoid in every layer',
        'Initialising all weights to zero',
        'Using fewer training examples',
      ],
      correct: 0,
    },
    {
      topic: 'Matrix shapes',
      text: 'X has shape (batch, 64) and W has shape (64, 32). What is the shape of X · W?',
      options: ['(64, 32)', '(batch, 64)', '(batch, 32)', '(32, batch)'],
      correct: 2,
    },
  ] satisfies AssessmentQuestion[],
  materialCount: 6,
}

export const levels = [
  { key: 'novice', name: 'Novice', bars: 1, desc: 'Brand new to this topic. Start from first principles.' },
  { key: 'beginner', name: 'Beginner', bars: 2, desc: 'I know a few basics, but only the surface.' },
  { key: 'intermediate', name: 'Intermediate', bars: 3, desc: 'I can apply the ideas. I want to find what I am missing.' },
  { key: 'advanced', name: 'Advanced', bars: 4, desc: 'I am comfortable with the topic. Test the edges.' },
] as const

export type LevelKey = (typeof levels)[number]['key']

// ---- Tutor chat ----

export type MaterialStatus = 'done' | 'now' | 'next'

export const materials: { title: string; kind: 'Article' | 'Video'; source: string; time: string; status: MaterialStatus }[] = [
  { title: 'Derivatives of composed functions', kind: 'Article', source: 'Web', time: '6 min', status: 'done' },
  { title: 'Computational graphs, visualised', kind: 'Video', source: 'YouTube', time: '9 min', status: 'now' },
  { title: 'Walking gradients backward', kind: 'Article', source: 'Web', time: '12 min', status: 'next' },
  { title: 'Why gradients vanish', kind: 'Video', source: 'YouTube', time: '11 min', status: 'next' },
]

export const tutorMastery = {
  pct: 64,
  level: 'Intermediate',
  delta: '+9 pts since last check',
  topics: [
    { name: 'Chain rule', pct: 42 },
    { name: 'Vanishing gradients', pct: 58 },
    { name: 'Computational graphs', pct: 71 },
    { name: 'Matrix shapes', pct: 80 },
  ],
}

// ---- Retention dashboard ----

export const retention = {
  kpis: [
    { icon: 'R', label: 'Retention rate', value: '81%', delta: '+6 pts', good: true, sub: 'Recall after 7+ days' },
    { icon: 'M', label: 'Concepts mastered', value: '38', delta: '+5', good: true, sub: 'Out of 96 tracked' },
    { icon: 'S', label: 'Avg memory strength', value: '74%', delta: '+3 pts', good: true, sub: '17 concepts at risk' },
    { icon: 'T', label: 'Reviews on time', value: '88%', delta: '3 overdue', good: false, sub: '24 done this month' },
  ],
  masteryPct: 68,
  masteryLevel: 'Intermediate',
  masteryDelta: '+4 pts this month',
  masteryNote: '96 concepts tracked across 3 courses',
  levels: [
    { name: 'Mastered', n: 38, color: '#0A4C8A' },
    { name: 'Solid', n: 31, color: '#0770C9' },
    { name: 'Developing', n: 19, color: '#7FB5E6' },
    { name: 'Weak', n: 8, color: '#D97706' },
  ],
  concepts: [
    { name: 'Backpropagation', course: 'Neural Networks', pct: 42, strength: 48 },
    { name: 'Gradient descent', course: 'Neural Networks', pct: 76, strength: 64 },
    { name: 'Regularization', course: 'Neural Networks', pct: 61, strength: 58 },
    { name: 'Activation functions', course: 'Neural Networks', pct: 88, strength: 84 },
    { name: 'Matrix multiplication', course: 'Linear Algebra', pct: 55, strength: 46 },
    { name: 'Eigenvalues', course: 'Linear Algebra', pct: 68, strength: 72 },
    { name: 'Vector spaces', course: 'Linear Algebra', pct: 91, strength: 88 },
    { name: 'List slicing', course: 'Python', pct: 82, strength: 52 },
    { name: 'Dictionaries', course: 'Python', pct: 90, strength: 86 },
  ],
  memory: { strong: 38, fading: 41, atRisk: 17, curveConcept: 'Gradient descent' },
  overdue: [
    { name: 'Matrix multiplication', late: '2 days overdue · Linear Algebra' },
    { name: 'Python list slicing', late: '4 days overdue · Python' },
    { name: 'Regularization', late: '5 days overdue · Neural Networks' },
  ],
  upcoming: [
    { day: 'Today', name: 'Gradient descent', meta: '5 min · Neural Networks' },
    { day: 'Tomorrow', name: 'Eigenvalues', meta: '4 min · Linear Algebra' },
    { day: 'Mon', name: 'Attention mechanism', meta: '5 min · Transformers' },
    { day: 'Wed', name: 'Python dictionaries', meta: '3 min · Python' },
  ],
  attention: [
    { name: 'Backpropagation', course: 'Neural Networks', chatId: 'backprop', reasons: [{ text: 'Strength 48%', warn: true }, { text: 'Recurring misconception', warn: false }] },
    { name: 'Matrix multiplication', course: 'Linear Algebra', chatId: 'eigenvectors', reasons: [{ text: '2 days overdue', warn: true }, { text: 'Strength 46%', warn: true }] },
    { name: 'Regularization', course: 'Neural Networks', chatId: 'backprop', reasons: [{ text: '5 days overdue', warn: true }, { text: 'Mixed up with dropout', warn: false }] },
    { name: 'Python list slicing', course: 'Python', chatId: 'python-lists', reasons: [{ text: '4 days overdue', warn: true }, { text: 'Strong understanding, weak recall', warn: false }] },
  ],
  misconceptions: {
    active: 5,
    resolvedThisMonth: 3,
    items: [
      { concept: 'Backpropagation', chatId: 'backprop', recurring: true, title: 'Treating each layer’s gradient as local', detail: 'You tend to compute a weight’s gradient from its own layer only. The chain rule carries effects from every layer after it.', seen: 'Seen 4 times in 3 sessions' },
      { concept: 'Regularization', chatId: 'backprop', recurring: false, title: 'Confusing regularization with dropout', detail: 'You described both as the same technique. Dropout is one way to regularize, alongside weight penalties.', seen: 'Seen 2 times, down from 4' },
      { concept: 'Matrix multiplication', chatId: 'eigenvectors', recurring: true, title: 'Assuming multiplication order does not matter', detail: 'You swapped the order of two matrices and kept the same shape. Order changes both the result and which shapes are valid.', seen: 'Seen 3 times in 2 sessions' },
    ],
  },
}
