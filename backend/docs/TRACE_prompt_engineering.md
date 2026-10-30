# OnlyNerd trace: prompt engineering (beginner)

- Date: 2026-10-30 22:16:10
- Python 3.12.14; fastapi 0.162.0, pydantic 2.14.2, pymongo 4.19.0, langchain-anthropic 1.7.7
- Total elapsed: 3.5 s
- LLM (server, from its log): 0 calls, 0 input + 0 output tokens, estimated $0.0000
- Verdict: **completed with 4 problem(s)**

- Course for 'prompt engineering' (beginner), prompt hash 2296821ab163: already in Mongo (b0dafa63, ready); cached bundle in .cache/.
- Generation skipped: the course was ready at once (reused).
- Reset learner 'trace' from an earlier trace: deleted 1 state and 17 attempt documents.

## Contents

1. [GET /health](#step-1) - ok
2. [POST /courses](#step-2) - ok
3. [GET /courses/{cid}](#step-3) - ok
4. [POST .../start](#step-4) - ok
5. [POST .../attempts (diagnostic)](#step-5) - ok
6. [GET .../state](#step-6) - ok
7. [POST .../attempts (practice)](#step-7) - ok
8. [GET .../state](#step-8) - ok
9. [POST .../advance {days: 1}](#step-9) - ok
10. [GET .../state](#step-10) - ok
11. [GET .../next + POST .../attempts (review, right)](#step-11) - ok
12. [POST .../advance {days: 3}](#step-12) - ok
13. [GET .../state](#step-13) - ok
14. [GET .../next + POST .../attempts (review, wrong)](#step-14) - ok
15. [GET .../state + GET .../next (relearn lesson)](#step-15) - ok
16. [POST .../sessions/new](#step-16) - ok
17. [Unwired and eval routes](#step-17) - ok

<a id="step-1"></a>
## 1. GET /health

**a. What and why.** Confirm the server this script launched is up before tracing anything.

**b. Request**

`GET http://127.0.0.1:8000/health`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 15 ms

```json
{
  "status": "ok"
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

(no learner state yet)

**f. What changed**

nothing

**g. Independent check**

nothing to recompute in this step

**h. Brain decision**

no brain decision in this step

<a id="step-2"></a>
## 2. POST /courses

**a. What and why.** Create (or reuse) the course for the topic; generation runs in the background, so poll until it is ready.

**b. Request**

`POST http://127.0.0.1:8000/courses`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "prompt": "prompt engineering",
  "level": "beginner"
}
```

**c. Response**

status 200, 16 ms

```json
{
  "course_id": "b0dafa63",
  "status": "ready",
  "topic": "prompt engineering",
  "concepts": [
    {
      "id": "language_model_basics",
      "name": "Language model basics",
      "prerequisites": []
    },
    {
      "id": "prompt_structure",
      "name": "Prompt structure",
      "prerequisites": []
    },
    {
      "id": "sampling_temperature",
      "name": "Sampling temperature",
      "prerequisites": []
    },
    {
      "id": "context_window",
      "name": "Context window",
      "prerequisites": [
        "language_model_basics"
      ]
    },
    {
      "id": "clear_instructions",
      "name": "Clear instructions",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "role_prompting",
      "name": "Role prompting",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "few_shot_examples",
      "name": "Few-shot examples",
      "prerequisites": [
        "prompt_structure",
        "clear_instructions"
      ]
    },
    {
      "id": "output_formatting",
      "name": "Output formatting",
      "prerequisites": [
        "clear_instructions"
      ]
    },
    {
      "id": "iterative_refinement",
      "name": "Iterative refinement",
      "prerequisites": [
        "clear_instructions",
        "few_shot_examples"
      ]
    },
    {
      "id": "hallucination_checking",
      "name": "Hallucination checking",
      "prerequisites": [
        "context_window",
        "sampling_temperature"
      ]
    }
  ]
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

(no learner state yet)

**f. What changed**

nothing

**g. Independent check**

nothing to recompute in this step

**h. Brain decision**

No brain decision (course creation).

<a id="step-3"></a>
## 3. GET /courses/{cid}

**a. What and why.** Read the course as the UI sees it: topic and the concept graph with prerequisites.

**b. Request**

`GET http://127.0.0.1:8000/courses/b0dafa63`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "course_id": "b0dafa63",
  "status": "ready",
  "topic": "prompt engineering",
  "concepts": [
    {
      "id": "language_model_basics",
      "name": "Language model basics",
      "prerequisites": []
    },
    {
      "id": "prompt_structure",
      "name": "Prompt structure",
      "prerequisites": []
    },
    {
      "id": "sampling_temperature",
      "name": "Sampling temperature",
      "prerequisites": []
    },
    {
      "id": "context_window",
      "name": "Context window",
      "prerequisites": [
        "language_model_basics"
      ]
    },
    {
      "id": "clear_instructions",
      "name": "Clear instructions",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "role_prompting",
      "name": "Role prompting",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "few_shot_examples",
      "name": "Few-shot examples",
      "prerequisites": [
        "prompt_structure",
        "clear_instructions"
      ]
    },
    {
      "id": "output_formatting",
      "name": "Output formatting",
      "prerequisites": [
        "clear_instructions"
      ]
    },
    {
      "id": "iterative_refinement",
      "name": "Iterative refinement",
      "prerequisites": [
        "clear_instructions",
        "few_shot_examples"
      ]
    },
    {
      "id": "hallucination_checking",
      "name": "Hallucination checking",
      "prerequisites": [
        "context_window",
        "sampling_temperature"
      ]
    }
  ]
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

(no learner state yet)

**f. What changed**

nothing

**g. Independent check**

nothing to recompute in this step

**h. Brain decision**

no brain decision in this step

10 concepts, roots ['language_model_basics', 'prompt_structure', 'sampling_temperature']; 70 questions in the cached bundle.

<a id="step-4"></a>
## 4. POST .../start

**a. What and why.** Create the learner 'trace' with every concept at the prior and get one diagnostic question per concept, without answers.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/start`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "questions": [
    {
      "id": "f707cec4-language_model_basics-d1",
      "concept_id": "language_model_basics",
      "prompt": "What does a language model do when it receives a prompt?",
      "options": [
        "Understands the prompt's meaning the way a person does",
        "Predicts the likely next text given the input",
        "Picks a fixed reply it wrote for that exact prompt",
        "Searches a stored database for the matching answer"
      ]
    },
    {
      "id": "f707cec4-prompt_structure-d1",
      "concept_id": "prompt_structure",
      "prompt": "Which part of a prompt tells the model what task to perform?",
      "options": [
        "Input data",
        "Instruction",
        "Context",
        "Output format"
      ]
    },
    {
      "id": "f707cec4-sampling_temperature-d1",
      "concept_id": "sampling_temperature",
      "prompt": "What does a low sampling temperature mainly change in a model's output?",
      "options": [
        "It makes the model pick its least likely words",
        "It makes word choices more predictable and repeatable",
        "It makes the model's answers more factually accurate",
        "It teaches the model new facts for the reply"
      ]
    },
    {
      "id": "f707cec4-context_window-d1",
      "concept_id": "context_window",
      "prompt": "A user chatted with a model for an hour, then sends a new request containing none of that earlier text. What can the model use to answer?",
      "options": [
        "A saved summary of the earlier chat",
        "Only the last sentence the user typed before",
        "Only the text included in this new request",
        "Everything from the previous hour of chat"
      ]
    },
    {
      "id": "f707cec4-clear_instructions-d1",
      "concept_id": "clear_instructions",
      "prompt": "Which prompt is most likely to get a useful result?",
      "options": [
        "Summarize this article in three bullet points.",
        "Summarize this article for me.",
        "Give me a summary; you'll know the style I want.",
        "Summarize this article, but avoid being too long."
      ]
    },
    {
      "id": "f707cec4-role_prompting-d1",
      "concept_id": "role_prompting",
      "prompt": "What is the main effect of telling a model to act as a nutritionist?",
      "options": [
        "It works the same for any topic you pick",
        "It shifts the tone and focus of its answer",
        "It gives the model new nutrition facts it lacked",
        "It removes the need to describe the question"
      ]
    },
    {
      "id": "f707cec4-few_shot_examples-d1",
      "concept_id": "few_shot_examples",
      "prompt": "You want a model to label reviews as positive or negative, but it returns free-form sentences. What is the best first fix?",
      "options": [
        "Add fifty unlabeled reviews so it sees more text",
        "Add a list of product facts for it to memorize",
        "Add two labeled reviews showing the exact label format",
        "Add two recipe examples to show it variety"
      ]
    },
    {
      "id": "f707cec4-output_formatting-d1",
      "concept_id": "output_formatting",
      "prompt": "Why ask for JSON with fixed keys when your program will read the model's output?",
      "options": [
        "So the answer looks more polished to human readers",
        "So the model will return exactly the same fields every time",
        "So the program can parse each field reliably without manual cleanup",
        "Because a clear task already sets the output structure"
      ]
    },
    {
      "id": "f707cec4-iterative_refinement-d1",
      "concept_id": "iterative_refinement",
      "prompt": "Your first prompt gives a decent answer on one input. What should you do next?",
      "options": [
        "Test it on several different inputs and revise where it falls short.",
        "Submit it, since a first prompt should work perfectly.",
        "Keep it, since a decent answer means the prompt is done.",
        "Rewrite its tone, length, and format together to save time."
      ]
    },
    {
      "id": "f707cec4-hallucination_checking-d1",
      "concept_id": "hallucination_checking",
      "prompt": "A model answers a factual question in a very assured tone. What should you do before trusting it?",
      "options": [
        "Ask it to add citations for support",
        "Trust it, since the tone shows expertise",
        "Accept it, since it sounds certain",
        "Verify the claim against a reliable source"
      ]
    }
  ]
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| prompt_structure | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| sampling_temperature | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| context_window | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| clear_instructions | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| role_prompting | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| few_shot_examples | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| output_formatting | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| iterative_refinement | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |
| hallucination_checking | 0.2 | 0 | 0 | 0 | None | None | 0 | 0 | False | [] |

Misconceptions:

none

session_questions: 0; clock_offset_days: 0
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- clock_offset_days: (absent) -> 0
- concepts.clear_instructions.attempts: (absent) -> 0
- concepts.clear_instructions.explanations_tried: (absent) -> []
- concepts.clear_instructions.failed_rounds: (absent) -> 0
- concepts.clear_instructions.fallbacks: (absent) -> 0
- concepts.clear_instructions.lapses: (absent) -> 0
- concepts.clear_instructions.needs_help: (absent) -> False
- concepts.clear_instructions.p_mastery: (absent) -> 0.2
- concepts.clear_instructions.stability_days: (absent) -> 0
- concepts.context_window.attempts: (absent) -> 0
- concepts.context_window.explanations_tried: (absent) -> []
- concepts.context_window.failed_rounds: (absent) -> 0
- concepts.context_window.fallbacks: (absent) -> 0
- concepts.context_window.lapses: (absent) -> 0
- concepts.context_window.needs_help: (absent) -> False
- concepts.context_window.p_mastery: (absent) -> 0.2
- concepts.context_window.stability_days: (absent) -> 0
- concepts.few_shot_examples.attempts: (absent) -> 0
- concepts.few_shot_examples.explanations_tried: (absent) -> []
- concepts.few_shot_examples.failed_rounds: (absent) -> 0
- concepts.few_shot_examples.fallbacks: (absent) -> 0
- concepts.few_shot_examples.lapses: (absent) -> 0
- concepts.few_shot_examples.needs_help: (absent) -> False
- concepts.few_shot_examples.p_mastery: (absent) -> 0.2
- concepts.few_shot_examples.stability_days: (absent) -> 0
- concepts.hallucination_checking.attempts: (absent) -> 0
- concepts.hallucination_checking.explanations_tried: (absent) -> []
- concepts.hallucination_checking.failed_rounds: (absent) -> 0
- concepts.hallucination_checking.fallbacks: (absent) -> 0
- concepts.hallucination_checking.lapses: (absent) -> 0
- concepts.hallucination_checking.needs_help: (absent) -> False
- concepts.hallucination_checking.p_mastery: (absent) -> 0.2
- concepts.hallucination_checking.stability_days: (absent) -> 0
- concepts.iterative_refinement.attempts: (absent) -> 0
- concepts.iterative_refinement.explanations_tried: (absent) -> []
- concepts.iterative_refinement.failed_rounds: (absent) -> 0
- concepts.iterative_refinement.fallbacks: (absent) -> 0
- concepts.iterative_refinement.lapses: (absent) -> 0
- concepts.iterative_refinement.needs_help: (absent) -> False
- concepts.iterative_refinement.p_mastery: (absent) -> 0.2
- concepts.iterative_refinement.stability_days: (absent) -> 0
- concepts.language_model_basics.attempts: (absent) -> 0
- concepts.language_model_basics.explanations_tried: (absent) -> []
- concepts.language_model_basics.failed_rounds: (absent) -> 0
- concepts.language_model_basics.fallbacks: (absent) -> 0
- concepts.language_model_basics.lapses: (absent) -> 0
- concepts.language_model_basics.needs_help: (absent) -> False
- concepts.language_model_basics.p_mastery: (absent) -> 0.2
- concepts.language_model_basics.stability_days: (absent) -> 0
- concepts.output_formatting.attempts: (absent) -> 0
- concepts.output_formatting.explanations_tried: (absent) -> []
- concepts.output_formatting.failed_rounds: (absent) -> 0
- concepts.output_formatting.fallbacks: (absent) -> 0
- concepts.output_formatting.lapses: (absent) -> 0
- concepts.output_formatting.needs_help: (absent) -> False
- concepts.output_formatting.p_mastery: (absent) -> 0.2
- concepts.output_formatting.stability_days: (absent) -> 0
- concepts.prompt_structure.attempts: (absent) -> 0
- concepts.prompt_structure.explanations_tried: (absent) -> []
- concepts.prompt_structure.failed_rounds: (absent) -> 0
- concepts.prompt_structure.fallbacks: (absent) -> 0
- concepts.prompt_structure.lapses: (absent) -> 0
- concepts.prompt_structure.needs_help: (absent) -> False
- concepts.prompt_structure.p_mastery: (absent) -> 0.2
- concepts.prompt_structure.stability_days: (absent) -> 0
- concepts.role_prompting.attempts: (absent) -> 0
- concepts.role_prompting.explanations_tried: (absent) -> []
- concepts.role_prompting.failed_rounds: (absent) -> 0
- concepts.role_prompting.fallbacks: (absent) -> 0
- concepts.role_prompting.lapses: (absent) -> 0
- concepts.role_prompting.needs_help: (absent) -> False
- concepts.role_prompting.p_mastery: (absent) -> 0.2
- concepts.role_prompting.stability_days: (absent) -> 0
- concepts.sampling_temperature.attempts: (absent) -> 0
- concepts.sampling_temperature.explanations_tried: (absent) -> []
- concepts.sampling_temperature.failed_rounds: (absent) -> 0
- concepts.sampling_temperature.fallbacks: (absent) -> 0
- concepts.sampling_temperature.lapses: (absent) -> 0
- concepts.sampling_temperature.needs_help: (absent) -> False
- concepts.sampling_temperature.p_mastery: (absent) -> 0.2
- concepts.sampling_temperature.stability_days: (absent) -> 0
- roadmap: (absent) -> ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
- session_questions: (absent) -> 0

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| diagnostic order = roadmap | ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking'] | ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking'] | OK |
| every concept starts at p=0.2 | 0.2 | [0.2] | OK |

**h. Brain decision**

no brain decision in this step

<a id="step-5"></a>
## 5. POST .../attempts (diagnostic)

**a. What and why.** Answer the diagnostic with a fixed script (right/wrong and confidence per concept) to exercise BKT, misconception evidence and placement.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/attempts`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "answers": [
    {
      "question_id": "f707cec4-language_model_basics-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-prompt_structure-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-sampling_temperature-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-d1",
      "chosen_index": 0,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-clear_instructions-d1",
      "chosen_index": 0,
      "confidence": "low"
    },
    {
      "question_id": "f707cec4-role_prompting-d1",
      "chosen_index": 0,
      "confidence": "low"
    },
    {
      "question_id": "f707cec4-few_shot_examples-d1",
      "chosen_index": 2,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-output_formatting-d1",
      "chosen_index": 2,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-iterative_refinement-d1",
      "chosen_index": 0,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-hallucination_checking-d1",
      "chosen_index": 3,
      "confidence": "high"
    }
  ]
}
```

**c. Response**

status 200, 16 ms

```json
{
  "graded": [
    {
      "question_id": "f707cec4-language_model_basics-d1",
      "concept_id": "language_model_basics",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-prompt_structure-d1",
      "concept_id": "prompt_structure",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-sampling_temperature-d1",
      "concept_id": "sampling_temperature",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-d1",
      "concept_id": "context_window",
      "correct": false,
      "chosen_tag": "context_window__model_remembers_everything",
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-clear_instructions-d1",
      "concept_id": "clear_instructions",
      "correct": true,
      "chosen_tag": null,
      "confidence": "low"
    },
    {
      "question_id": "f707cec4-role_prompting-d1",
      "concept_id": "role_prompting",
      "correct": false,
      "chosen_tag": "role_prompting__any_role_works_equally",
      "confidence": "low"
    },
    {
      "question_id": "f707cec4-few_shot_examples-d1",
      "concept_id": "few_shot_examples",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-output_formatting-d1",
      "concept_id": "output_formatting",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-iterative_refinement-d1",
      "concept_id": "iterative_refinement",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-hallucination_checking-d1",
      "concept_id": "hallucination_checking",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    }
  ],
  "correct_indices": {
    "f707cec4-role_prompting-d1": 1,
    "f707cec4-sampling_temperature-d1": 1,
    "f707cec4-few_shot_examples-d1": 2,
    "f707cec4-prompt_structure-d1": 1,
    "f707cec4-context_window-d1": 2,
    "f707cec4-iterative_refinement-d1": 0,
    "f707cec4-clear_instructions-d1": 0,
    "f707cec4-language_model_basics-d1": 1,
    "f707cec4-hallucination_checking-d1": 3,
    "f707cec4-output_formatting-d1": 2
  },
  "explanations": {
    "f707cec4-role_prompting-d1": "A role changes the style, focus and perspective of the same model. It does not add knowledge the model already lacks, and the task still has to be stated.",
    "f707cec4-sampling_temperature-d1": "Low temperature concentrates sampling on the highest-probability words, so outputs become more predictable. It does not change accuracy or the model's knowledge.",
    "f707cec4-few_shot_examples-d1": "Examples demonstrate the output pattern, so labeled examples in the exact format teach the model what to return.",
    "f707cec4-prompt_structure-d1": "The instruction states the task, such as summarize or translate. The other parts supply information or shape the reply but do not name the task.",
    "f707cec4-context_window-d1": "The model only sees the text inside the current request's context window. Earlier chats are not available unless they are included again.",
    "f707cec4-iterative_refinement-d1": "A prompt needs testing across varied inputs to show where it works and where it fails. Revising based on those results is the core of iterative refinement.",
    "f707cec4-clear_instructions-d1": "A specific format and count tells the model exactly what output to produce, so it does not have to guess.",
    "f707cec4-language_model_basics-d1": "A language model generates text by predicting which text is likely to come next, based on the input it receives and patterns learned in training.",
    "f707cec4-hallucination_checking-d1": "Confident wording does not indicate accuracy, so claims need checking against reliable sources.",
    "f707cec4-output_formatting-d1": "Fixed structure lets code extract values directly. Format determines whether output can be used by software."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.1774193548387097,
    "clear_instructions": 0.85,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [
    "context_window__model_remembers_everything"
  ],
  "messages": [
    "3 correct in a row.",
    "Placed 8 concepts as already known; I'll check them again within 3 days."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "context_window",
      "target_misconceptions": [
        "context_window__model_remembers_everything"
      ],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "placed as known: language_model_basics, prompt_structure, sampling_temperature, clear_instructions, few_shot_examples, output_formatting, iterative_refinement, hallucination_checking; context_window__model_remembers_everything confirmed, evidence 2; context_window needs it",
    "lesson": {
      "concept_id": "context_window",
      "style": "contrast",
      "explanation": "You may believe the model remembers every conversation you have ever had with it. That belief is wrong. The right idea is that a model only works with the text inside its context window, meaning the text sent in one request. Think of it as a desk with limited space. Whatever is on the desk, the model can read and use. Whatever has been pushed off the desk, or was never placed there, is invisible to it. So when you start a new chat, earlier conversations are not automatically present. The model has no stored memory of your last session unless that text is includ
[truncated, 8237 chars]
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | [] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | confirmed | 2 | 0 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 0
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- concepts.clear_instructions.attempts: 0 -> 1
- concepts.clear_instructions.due_at: None -> 2026-10-31T16:46:13
- concepts.clear_instructions.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.clear_instructions.p_mastery: 0.2 -> 0.85
- concepts.clear_instructions.stability_days: 0 -> 1
- concepts.context_window.attempts: 0 -> 1
- concepts.context_window.explanations_tried: [] -> ['contrast']
- concepts.context_window.failed_rounds: 0 -> 1
- concepts.context_window.p_mastery: 0.2 -> 0.177419
- concepts.few_shot_examples.attempts: 0 -> 1
- concepts.few_shot_examples.due_at: None -> 2026-11-02T16:46:13
- concepts.few_shot_examples.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.few_shot_examples.p_mastery: 0.2 -> 0.85
- concepts.few_shot_examples.stability_days: 0 -> 3
- concepts.hallucination_checking.attempts: 0 -> 1
- concepts.hallucination_checking.due_at: None -> 2026-11-02T16:46:13
- concepts.hallucination_checking.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.hallucination_checking.p_mastery: 0.2 -> 0.85
- concepts.hallucination_checking.stability_days: 0 -> 3
- concepts.iterative_refinement.attempts: 0 -> 1
- concepts.iterative_refinement.due_at: None -> 2026-11-02T16:46:13
- concepts.iterative_refinement.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.iterative_refinement.p_mastery: 0.2 -> 0.85
- concepts.iterative_refinement.stability_days: 0 -> 3
- concepts.language_model_basics.attempts: 0 -> 1
- concepts.language_model_basics.due_at: None -> 2026-11-01T16:46:13
- concepts.language_model_basics.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.language_model_basics.p_mastery: 0.2 -> 0.85
- concepts.language_model_basics.stability_days: 0 -> 2
- concepts.output_formatting.attempts: 0 -> 1
- concepts.output_formatting.due_at: None -> 2026-11-02T16:46:13
- concepts.output_formatting.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.output_formatting.p_mastery: 0.2 -> 0.85
- concepts.output_formatting.stability_days: 0 -> 3
- concepts.prompt_structure.attempts: 0 -> 1
- concepts.prompt_structure.due_at: None -> 2026-11-01T16:46:13
- concepts.prompt_structure.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.prompt_structure.p_mastery: 0.2 -> 0.85
- concepts.prompt_structure.stability_days: 0 -> 2
- concepts.role_prompting.attempts: 0 -> 1
- concepts.role_prompting.failed_rounds: 0 -> 1
- concepts.role_prompting.p_mastery: 0.2 -> 0.177419
- concepts.sampling_temperature.attempts: 0 -> 1
- concepts.sampling_temperature.due_at: None -> 2026-11-01T16:46:13
- concepts.sampling_temperature.last_reviewed_at: None -> 2026-10-30T16:46:13
- concepts.sampling_temperature.p_mastery: 0.2 -> 0.85
- concepts.sampling_temperature.stability_days: 0 -> 2
- misconceptions.context_window__model_remembers_everything.clean_streak: (absent) -> 0
- misconceptions.context_window__model_remembers_everything.evidence: (absent) -> 2
- misconceptions.context_window__model_remembers_everything.status: (absent) -> confirmed
- misconceptions.role_prompting__any_role_works_equally.clean_streak: (absent) -> 0
- misconceptions.role_prompting__any_role_works_equally.evidence: (absent) -> 1
- misconceptions.role_prompting__any_role_works_equally.status: (absent) -> suspected

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| f707cec4-language_model_basics-d1 correct | True | True | OK |
| f707cec4-prompt_structure-d1 correct | True | True | OK |
| f707cec4-sampling_temperature-d1 correct | True | True | OK |
| f707cec4-context_window-d1 correct | False | False | OK |
| f707cec4-context_window-d1 chosen_tag | context_window__model_remembers_everything | context_window__model_remembers_everything | OK |
| f707cec4-clear_instructions-d1 correct | True | True | OK |
| f707cec4-role_prompting-d1 correct | False | False | OK |
| f707cec4-role_prompting-d1 chosen_tag | role_prompting__any_role_works_equally | role_prompting__any_role_works_equally | OK |
| f707cec4-few_shot_examples-d1 correct | True | True | OK |
| f707cec4-output_formatting-d1 correct | True | True | OK |
| f707cec4-iterative_refinement-d1 correct | True | True | OK |
| f707cec4-hallucination_checking-d1 correct | True | True | OK |
| language_model_basics p_mastery (placed (2 d)) | 0.85 | 0.85 | OK |
| language_model_basics stability_days | 2 | 2 | OK |
| language_model_basics lapses | 0 | 0 | OK |
| language_model_basics due_at - last_reviewed_at (days) | 2 | 2 | OK |
| language_model_basics mastery in response = Mongo | 0.85 | 0.85 | OK |
| prompt_structure p_mastery (placed (2 d)) | 0.85 | 0.85 | OK |
| prompt_structure stability_days | 2 | 2 | OK |
| prompt_structure lapses | 0 | 0 | OK |
| prompt_structure due_at - last_reviewed_at (days) | 2 | 2 | OK |
| prompt_structure mastery in response = Mongo | 0.85 | 0.85 | OK |
| sampling_temperature p_mastery (placed (2 d)) | 0.85 | 0.85 | OK |
| sampling_temperature stability_days | 2 | 2 | OK |
| sampling_temperature lapses | 0 | 0 | OK |
| sampling_temperature due_at - last_reviewed_at (days) | 2 | 2 | OK |
| sampling_temperature mastery in response = Mongo | 0.85 | 0.85 | OK |
| context_window p_mastery (BKT only) | 0.177419 | 0.177419 | OK |
| context_window stability_days | 0 | 0 | OK |
| context_window lapses | 0 | 0 | OK |
| context_window mastery in response = Mongo | 0.177419 | 0.177419 | OK |
| clear_instructions p_mastery (placed (1 d)) | 0.85 | 0.85 | OK |
| clear_instructions stability_days | 1 | 1 | OK |
| clear_instructions lapses | 0 | 0 | OK |
| clear_instructions due_at - last_reviewed_at (days) | 1 | 1 | OK |
| clear_instructions mastery in response = Mongo | 0.85 | 0.85 | OK |
| role_prompting p_mastery (BKT only) | 0.177419 | 0.177419 | OK |
| role_prompting stability_days | 0 | 0 | OK |
| role_prompting lapses | 0 | 0 | OK |
| role_prompting mastery in response = Mongo | 0.177419 | 0.177419 | OK |
| few_shot_examples p_mastery (placed (3 d)) | 0.85 | 0.85 | OK |
| few_shot_examples stability_days | 3 | 3 | OK |
| few_shot_examples lapses | 0 | 0 | OK |
| few_shot_examples due_at - last_reviewed_at (days) | 3 | 3 | OK |
| few_shot_examples mastery in response = Mongo | 0.85 | 0.85 | OK |
| output_formatting p_mastery (placed (3 d)) | 0.85 | 0.85 | OK |
| output_formatting stability_days | 3 | 3 | OK |
| output_formatting lapses | 0 | 0 | OK |
| output_formatting due_at - last_reviewed_at (days) | 3 | 3 | OK |
| output_formatting mastery in response = Mongo | 0.85 | 0.85 | OK |
| iterative_refinement p_mastery (placed (3 d)) | 0.85 | 0.85 | OK |
| iterative_refinement stability_days | 3 | 3 | OK |
| iterative_refinement lapses | 0 | 0 | OK |
| iterative_refinement due_at - last_reviewed_at (days) | 3 | 3 | OK |
| iterative_refinement mastery in response = Mongo | 0.85 | 0.85 | OK |
| hallucination_checking p_mastery (placed (3 d)) | 0.85 | 0.85 | OK |
| hallucination_checking stability_days | 3 | 3 | OK |
| hallucination_checking lapses | 0 | 0 | OK |
| hallucination_checking due_at - last_reviewed_at (days) | 3 | 3 | OK |
| hallucination_checking mastery in response = Mongo | 0.85 | 0.85 | OK |
| session_questions after the diagnostic | 0 | 0 | OK |

**h. Brain decision**

Reason: "placed as known: language_model_basics, prompt_structure, sampling_temperature, clear_instructions, few_shot_examples, output_formatting, iterative_refinement, hallucination_checking; context_window__model_remembers_everything confirmed, evidence 2; context_window needs it"

The brain chose **lesson context_window**. Re-derived from the rules: lesson context_window (lowest p x retrievability among unlocked, unmastered concepts): as expected.

<a id="step-6"></a>
## 6. GET .../state

**a. What and why.** Read the dashboard numbers after the diagnostic and check retrievability, due dates and gaps.

**b. Request**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/state`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "clear_instructions",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 1.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-10-31T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "role_prompting",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "few_shot_examples",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "output_formatting",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "iterative_refinement",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "hallucination_checking",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    }
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "confirmed",
      "evidence": 2.0,
      "clean_streak": 0
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-10-31T16:46:13.274000",
  "due": {
    "language_model_basics": "2026-11-01T16:46:13.274000",
    "prompt_structure": "2026-11-01T16:46:13.274000",
    "sampling_temperature": "2026-11-01T16:46:13.274000",
    "clear_instructions": "2026-10-31T16:46:13.274000",
    "few_shot_examples": "2026-11-02T16:46:13.274000",
    "output_formatting": "2026-11-02T16:46:13.274000",
    "iterative_refinement": "2026-11-02T16:46:13.274000",
    "hallucination_checking": "2026-11-02T16:46:13.274000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9999999904248754,
    "prompt_structure": 0.9999999904248754,
    "sampling_temperature": 0.9999999904248754,
    "context_window": 1.0,
    "clear_instructions": 0.999999980849751,
    "role_prompting": 1.0,
    "few_shot_examples": 0.9999999936165835,
    "output_formatting": 0.9999999936165835,
    "iterative_refinement": 0.9999999936165835,
    "hallucination_checking": 0.9999999936165835
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.25
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | [] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | confirmed | 2 | 0 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 0
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| language_model_basics retrievability 0.9^(t/S) | 1 | 1 | OK |
| prompt_structure retrievability 0.9^(t/S) | 1 | 1 | OK |
| sampling_temperature retrievability 0.9^(t/S) | 1 | 1 | OK |
| context_window retrievability 0.9^(t/S) | 1 | 1 | OK |
| clear_instructions retrievability 0.9^(t/S) | 1 | 1 | OK |
| role_prompting retrievability 0.9^(t/S) | 1 | 1 | OK |
| few_shot_examples retrievability 0.9^(t/S) | 1 | 1 | OK |
| output_formatting retrievability 0.9^(t/S) | 1 | 1 | OK |
| iterative_refinement retrievability 0.9^(t/S) | 1 | 1 | OK |
| hallucination_checking retrievability 0.9^(t/S) | 1 | 1 | OK |
| due (concepts with a schedule) | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |
| gaps | ['context_window', 'role_prompting'] | ['context_window', 'role_prompting'] | OK |

**h. Brain decision**

No brain decision in this step (state read only).

<a id="step-7"></a>
## 7. POST .../attempts (practice)

**a. What and why.** Answer the 3 practice questions of the step the brain returned: 2 right, 1 wrong with a tag.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/attempts`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "answers": [
    {
      "question_id": "f707cec4-context_window-p1",
      "chosen_index": 0,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-p2",
      "chosen_index": 3,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-t1",
      "chosen_index": 1,
      "confidence": "medium"
    }
  ]
}
```

**c. Response**

status 200, 0 ms

```json
{
  "graded": [
    {
      "question_id": "f707cec4-context_window-p1",
      "concept_id": "context_window",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-p2",
      "concept_id": "context_window",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-t1",
      "concept_id": "context_window",
      "correct": false,
      "chosen_tag": "context_window__limit_is_only_words",
      "confidence": "medium"
    }
  ],
  "correct_indices": {
    "f707cec4-context_window-p1": 0,
    "f707cec4-context_window-p2": 3,
    "f707cec4-context_window-t1": 0
  },
  "explanations": {
    "f707cec4-context_window-p1": "The window is measured in tokens, and a single word can be split into several tokens. So a word count can understate the token count.",
    "f707cec4-context_window-p2": "Only text inside the window is usable, so sending the most relevant sections in pieces works within the limit. Relying on memory or assuming a fit does not.",
    "f707cec4-context_window-t1": "A new session only includes the text sent in that request. Without the day-one text, the model has no access to the order number."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.4814035218438767,
    "clear_instructions": 0.85,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "Misconception context_window__model_remembers_everything resolved."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "role_prompting",
      "target_misconceptions": [],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "role_prompting: mastery 0.18, lowest among unlocked concepts",
    "lesson": {
      "concept_id": "role_prompting",
      "style": "worked_example",
      "explanation": "Role prompting means telling the model who it should act as before you ask your question, such as a nurse, a copy editor, or a chess coach. The role shapes the tone, the expertise it draws on, and what it chooses to focus on. Let's walk through one small example. Suppose you want advice about a sore back after lifting boxes. Step one: write the plain question, 'My back hurts after moving boxes. What should I do?' Step two: add a role, so the prompt becomes, 'You are a calm physical therapist. My back hurts after moving boxes. What should I do?' Step three: compare the two answers. The plain version may give a generic list. The role version usually sounds more measured, emphasizes rest and gentle movement, and flags when to see a doctor. Your turn: pick a task you care about, like summarizing meeting notes, and write one role-based prompt for it. Then ask yourself whether the role changed the focus, the tone, or both. Keep the role specific, because 'expert' tells the model less than 'an editor who cuts jargon for beginners'.",
      "targets": [],
      "resources": []
    },
    "questions": [
      {
        "id": "f707cec4-role_prompting-p1",
        "concept_id": "role_prompting",
        "prompt": "A prompt says 'You are a tax lawyer' and asks about a student's gig income. Why might the answer still be wrong?",
        "options": [
          "Any professional role would be equally accurate here",
          "The role only changes style; facts can still be wrong",
          "The role gives it current tax law it lacked",
          "The role makes stating the income question unnecessary"
        ]
      },
      {
        "id": "f707cec4-role_prompting-p2",
        "concept_id": "role_prompting",
        "prompt": "You want a critical review of a startup pitch. Which role and task pairing is strongest?",
        "options": [
          "A skeptical investor asked to flag risks",
          "A licensed CPA who audits the numbers",
          "Skeptical reviewer, with the pitch left out",
          "A cheerful children's book author writing praise"
        ]
      },
      {
        "id": "f707cec4-role_prompting-t1",
        "concept_id": "role_prompting",
        "prompt": "Which setup best gets a calm, short reply to an angry customer?",
        "options": [
          "Support agent role, with the complaint omitted",
          "A chemistry professor role for refund rules",
          "Support agent role, complaint text, and length limit",
          "A poet role, since any role fits equally"
        ]
      }
    ]
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 3; clock_offset_days: 0
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- concepts.context_window.attempts: 1 -> 4
- concepts.context_window.failed_rounds: 1 -> 2
- concepts.context_window.p_mastery: 0.177419 -> 0.481404
- concepts.role_prompting.explanations_tried: [] -> ['worked_example']
- misconceptions.context_window__limit_is_only_words.clean_streak: (absent) -> 0
- misconceptions.context_window__limit_is_only_words.evidence: (absent) -> 1
- misconceptions.context_window__limit_is_only_words.status: (absent) -> suspected
- misconceptions.context_window__model_remembers_everything.clean_streak: 0 -> 2
- misconceptions.context_window__model_remembers_everything.evidence: 2 -> 0
- misconceptions.context_window__model_remembers_everything.status: confirmed -> resolved
- session_questions: 0 -> 3

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| f707cec4-context_window-p1 correct | True | True | OK |
| f707cec4-context_window-p2 correct | True | True | OK |
| f707cec4-context_window-t1 correct | False | False | OK |
| f707cec4-context_window-t1 chosen_tag | context_window__limit_is_only_words | context_window__limit_is_only_words | OK |
| context_window p_mastery (BKT only) | 0.481404 | 0.481404 | OK |
| context_window stability_days | 0 | 0 | OK |
| context_window lapses | 0 | 0 | OK |
| context_window mastery in response = Mongo | 0.481404 | 0.481404 | OK |

**h. Brain decision**

Reason: "role_prompting: mastery 0.18, lowest among unlocked concepts"

The brain chose **lesson role_prompting**. Re-derived from the rules: lesson role_prompting (lowest p x retrievability among unlocked, unmastered concepts): as expected.

<a id="step-8"></a>
## 8. GET .../state

**a. What and why.** Read the state after the practice round.

**b. Request**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/state`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "clear_instructions",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 1.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-10-31T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "role_prompting",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "few_shot_examples",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "output_formatting",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "iterative_refinement",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "hallucination_checking",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    }
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-10-31T16:46:13.274000",
  "due": {
    "language_model_basics": "2026-11-01T16:46:13.274000",
    "prompt_structure": "2026-11-01T16:46:13.274000",
    "sampling_temperature": "2026-11-01T16:46:13.274000",
    "clear_instructions": "2026-10-31T16:46:13.274000",
    "few_shot_examples": "2026-11-02T16:46:13.274000",
    "output_formatting": "2026-11-02T16:46:13.274000",
    "iterative_refinement": "2026-11-02T16:46:13.274000",
    "hallucination_checking": "2026-11-02T16:46:13.274000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9999999719209351,
    "prompt_structure": 0.9999999719209351,
    "sampling_temperature": 0.9999999719209351,
    "context_window": 1.0,
    "clear_instructions": 0.9999999438418712,
    "role_prompting": 1.0,
    "few_shot_examples": 0.9999999812806234,
    "output_formatting": 0.9999999812806234,
    "iterative_refinement": 0.9999999812806234,
    "hallucination_checking": 0.9999999812806234
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.625
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 3; clock_offset_days: 0
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| language_model_basics retrievability 0.9^(t/S) | 1 | 1 | OK |
| prompt_structure retrievability 0.9^(t/S) | 1 | 1 | OK |
| sampling_temperature retrievability 0.9^(t/S) | 1 | 1 | OK |
| context_window retrievability 0.9^(t/S) | 1 | 1 | OK |
| clear_instructions retrievability 0.9^(t/S) | 1 | 1 | OK |
| role_prompting retrievability 0.9^(t/S) | 1 | 1 | OK |
| few_shot_examples retrievability 0.9^(t/S) | 1 | 1 | OK |
| output_formatting retrievability 0.9^(t/S) | 1 | 1 | OK |
| iterative_refinement retrievability 0.9^(t/S) | 1 | 1 | OK |
| hallucination_checking retrievability 0.9^(t/S) | 1 | 1 | OK |
| due (concepts with a schedule) | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |
| gaps | ['context_window', 'role_prompting'] | ['context_window', 'role_prompting'] | OK |

**h. Brain decision**

No brain decision in this step (state read only).

<a id="step-9"></a>
## 9. POST .../advance {days: 1}

**a. What and why.** Move the learner's clock 1 day: low-confidence placements become due.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/advance`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "days": 1
}
```

**c. Response**

status 200, 0 ms

```json
{
  "now": "2026-10-31T16:46:13.334069",
  "due_now": [
    "clear_instructions"
  ],
  "next_kind": "review",
  "next_concept_id": "clear_instructions"
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 1
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- clock_offset_days: 0 -> 1
- session_questions: 3 -> 0

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| clock_offset_days | 1 | 1 | OK |
| session_questions reset | 0 | 0 | OK |
| due_now = concepts with due_at <= now | ['clear_instructions'] | ['clear_instructions'] | OK |

**h. Brain decision**

advance stored the decision **review clear_instructions** (served later by GET /next). Re-derived from the rules: review clear_instructions (due review with the lowest retrievability): as expected.

<a id="step-10"></a>
## 10. GET .../state

**a. What and why.** Read the state 1 day later: retrievability falls, due reviews appear.

**b. Request**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/state`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "clear_instructions",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 1.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-10-31T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "role_prompting",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "few_shot_examples",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "output_formatting",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "iterative_refinement",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "hallucination_checking",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    }
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-10-31T16:46:13.274000",
  "due": {
    "language_model_basics": "2026-11-01T16:46:13.274000",
    "prompt_structure": "2026-11-01T16:46:13.274000",
    "sampling_temperature": "2026-11-01T16:46:13.274000",
    "clear_instructions": "2026-10-31T16:46:13.274000",
    "few_shot_examples": "2026-11-02T16:46:13.274000",
    "output_formatting": "2026-11-02T16:46:13.274000",
    "iterative_refinement": "2026-11-02T16:46:13.274000",
    "hallucination_checking": "2026-11-02T16:46:13.274000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9486832551392312,
    "prompt_structure": 0.9486832551392312,
    "sampling_temperature": 0.9486832551392312,
    "context_window": 1.0,
    "clear_instructions": 0.8999999185815677,
    "role_prompting": 1.0,
    "few_shot_examples": 0.9654893554913208,
    "output_formatting": 0.9654893554913208,
    "iterative_refinement": 0.9654893554913208,
    "hallucination_checking": 0.9654893554913208
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.625
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.85 | 1 | 0 | 1 | 2026-10-30T16:46:13 | 2026-10-31T16:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 1
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| language_model_basics retrievability 0.9^(t/S) | 0.9487 | 0.9487 | OK |
| prompt_structure retrievability 0.9^(t/S) | 0.9487 | 0.9487 | OK |
| sampling_temperature retrievability 0.9^(t/S) | 0.9487 | 0.9487 | OK |
| context_window retrievability 0.9^(t/S) | 1 | 1 | OK |
| clear_instructions retrievability 0.9^(t/S) | 0.9 | 0.9 | OK |
| role_prompting retrievability 0.9^(t/S) | 1 | 1 | OK |
| few_shot_examples retrievability 0.9^(t/S) | 0.9655 | 0.9655 | OK |
| output_formatting retrievability 0.9^(t/S) | 0.9655 | 0.9655 | OK |
| iterative_refinement retrievability 0.9^(t/S) | 0.9655 | 0.9655 | OK |
| hallucination_checking retrievability 0.9^(t/S) | 0.9655 | 0.9655 | OK |
| due (concepts with a schedule) | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |
| gaps | ['context_window', 'role_prompting'] | ['context_window', 'role_prompting'] | OK |

**h. Brain decision**

No brain decision in this step (state read only).

<a id="step-11"></a>
## 11. GET .../next + POST .../attempts (review, right)

**a. What and why.** Fetch the review the brain stored at advance time (twice, to show it is idempotent) and pass it: stability should grow 2.5x.

**b. Request (request 1)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/next`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 1)**

status 200, 0 ms

```json
{
  "step": {
    "kind": "review",
    "concept_id": "clear_instructions",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "clear_instructions review due since 2026-10-31; recall now 0.90",
  "lesson": null,
  "questions": [
    {
      "id": "f707cec4-clear_instructions-p1",
      "concept_id": "clear_instructions",
      "prompt": "You want a model to avoid technical terms. Which rewrite is clearest?",
      "options": [
        "Explain this simply; you know what I mean.",
        "Don't use technical terms in your explanation.",
        "Explain this in plain words for a child.",
        "Explain this in a way that is good."
      ]
    },
    {
      "id": "f707cec4-clear_instructions-p2",
      "concept_id": "clear_instructions",
      "prompt": "A prompt says 'Improve this code.' The model only renames variables. What is the best fix?",
      "options": [
        "Make this code better and cleaner overall.",
        "Improve this code; don't change what it does.",
        "Refactor this function to remove duplication.",
        "Improve this code; you know what I'm going for."
      ]
    }
  ]
}
```

**b. Request (request 2)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/next`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 2)**

status 200, 0 ms

```json
{
  "step": {
    "kind": "review",
    "concept_id": "clear_instructions",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "clear_instructions review due since 2026-10-31; recall now 0.90",
  "lesson": null,
  "questions": [
    {
      "id": "f707cec4-clear_instructions-p1",
      "concept_id": "clear_instructions",
      "prompt": "You want a model to avoid technical terms. Which rewrite is clearest?",
      "options": [
        "Explain this simply; you know what I mean.",
        "Don't use technical terms in your explanation.",
        "Explain this in plain words for a child.",
        "Explain this in a way that is good."
      ]
    },
    {
      "id": "f707cec4-clear_instructions-p2",
      "concept_id": "clear_instructions",
      "prompt": "A prompt says 'Improve this code.' The model only renames variables. What is the best fix?",
      "options": [
        "Make this code better and cleaner overall.",
        "Improve this code; don't change what it does.",
        "Refactor this function to remove duplication.",
        "Improve this code; you know what I'm going for."
      ]
    }
  ]
}
```

**b. Request (request 3)**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/attempts`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "answers": [
    {
      "question_id": "f707cec4-clear_instructions-p1",
      "chosen_index": 2,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-clear_instructions-p2",
      "chosen_index": 2,
      "confidence": "medium"
    }
  ]
}
```

**c. Response (request 3)**

status 200, 16 ms

```json
{
  "graded": [
    {
      "question_id": "f707cec4-clear_instructions-p1",
      "concept_id": "clear_instructions",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-clear_instructions-p2",
      "concept_id": "clear_instructions",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    }
  ],
  "correct_indices": {
    "f707cec4-clear_instructions-p2": 2,
    "f707cec4-clear_instructions-p1": 2
  },
  "explanations": {
    "f707cec4-clear_instructions-p2": "Naming the specific change and the constraint tells the model the exact task, rather than leaving 'improve' open to interpretation.",
    "f707cec4-clear_instructions-p1": "Naming the target audience and style describes the desired behavior, which is more actionable than a prohibition or a vague quality request."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.4814035218438767,
    "clear_instructions": 0.9903447815047441,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "Review of clear_instructions passed: next one in 2.5 days."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "role_prompting",
      "target_misconceptions": [],
      "avoid_styles": [
        "worked_example"
      ],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "role_prompting: mastery 0.18, lowest among unlocked concepts",
    "lesson": {
      "concept_id": "role_prompting",
      "style": "contrast",
      "explanation": "Role prompting means telling the model who it should act as, such as a patient math tutor, a senior tax accountant, or a copy editor. Many beginners believe a role is a magic switch that makes the model truly know more, so the answer becomes automatically expert and accurate. That belief breaks here. A role mainly shapes tone, vocabulary, level of detail, and what the model chooses to focus on. Compare two prompts. The wrong version says: You are a world-class doctor, explain this rash. The right version says: You are a doctor explaining to a worried first-time parent, in plain language, and list the three signs that need urgent care. The second prompt works because it pairs the role with a clear audience, a format, and a focus, so the role directs the response instead of just decorating it. The role also cannot replace facts you supply. If you need accurate figures, paste the source material and ask the role to use it. Try writing one role prompt for a task you know well, then compare the output to what you get without a role. Notice what changed in tone and focus, and what did not change.",
      "targets": [],
      "resources": []
    },
    "questions": [
      {
        "id": "f707cec4-role_prompting-p1",
        "concept_id": "role_prompting",
        "prompt": "A prompt says 'You are a tax lawyer' and asks about a student's gig income. Why might the answer still be wrong?",
        "options": [
          "Any professional role would be equally accurate here",
          "The role only changes style; facts can still be wrong",
          "The role gives it current tax law it lacked",
          "The role makes stating the income question unnecessary"
        ]
      },
      {
        "id": "f707cec4-role_prompting-p2",
        "concept_id": "role_prompting",
        "prompt": "You want a critical review of a startup pitch. Which role and task pairing is strongest?",
        "options": [
          "A skeptical investor asked to flag risks",
          "A licensed CPA who audits the numbers",
          "Skeptical reviewer, with the pitch left out",
          "A cheerful children's book author writing praise"
        ]
      },
      {
        "id": "f707cec4-role_prompting-t1",
        "concept_id": "role_prompting",
        "prompt": "Which setup best gets a calm, short reply to an angry customer?",
        "options": [
          "Support agent role, with the complaint omitted",
          "A chemistry professor role for refund rules",
          "Support agent role, complaint text, and length limit",
          "A poet role, since any role fits equally"
        ]
      }
    ]
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 2; clock_offset_days: 1
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- concepts.clear_instructions.attempts: 1 -> 3
- concepts.clear_instructions.due_at: 2026-10-31T16:46:13 -> 2026-11-03T04:46:13
- concepts.clear_instructions.last_reviewed_at: 2026-10-30T16:46:13 -> 2026-10-31T16:46:13
- concepts.clear_instructions.p_mastery: 0.85 -> 0.990345
- concepts.clear_instructions.stability_days: 1 -> 2.5
- concepts.role_prompting.explanations_tried: ['worked_example'] -> ['worked_example', 'contrast']
- session_questions: 0 -> 2

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| GET /next twice returns the same step and questions | identical | identical | OK |
| served_question_ids = the /next questions | ['f707cec4-clear_instructions-p1', 'f707cec4-clear_instructions-p2'] | ['f707cec4-clear_instructions-p1', 'f707cec4-clear_instructions-p2'] | OK |
| f707cec4-clear_instructions-p1 correct | True | True | OK |
| f707cec4-clear_instructions-p2 correct | True | True | OK |
| clear_instructions p_mastery (review success) | 0.990345 | 0.990345 | OK |
| clear_instructions stability_days | 2.5 | 2.5 | OK |
| clear_instructions lapses | 0 | 0 | OK |
| clear_instructions due_at - last_reviewed_at (days) | 2.5 | 2.5 | OK |
| clear_instructions mastery in response = Mongo | 0.990345 | 0.990345 | OK |

**h. Brain decision**

Reason: "role_prompting: mastery 0.18, lowest among unlocked concepts"

The brain chose **lesson role_prompting**. Re-derived from the rules: lesson role_prompting (lowest p x retrievability among unlocked, unmastered concepts): as expected.

GET /next served **review clear_instructions** (reason: "clear_instructions review due since 2026-10-31; recall now 0.90") with questions ['f707cec4-clear_instructions-p1', 'f707cec4-clear_instructions-p2'].

<a id="step-12"></a>
## 12. POST .../advance {days: 3}

**a. What and why.** Move the clock 3 more days so more placed concepts fall due.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/advance`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "days": 3
}
```

**c. Response**

status 200, 15 ms

```json
{
  "now": "2026-11-03T16:46:13.387299",
  "due_now": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "clear_instructions",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "next_kind": "review",
  "next_concept_id": "language_model_basics"
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- clock_offset_days: 1 -> 4
- session_questions: 2 -> 0

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| clock_offset_days | 4 | 4 | OK |
| session_questions reset | 0 | 0 | OK |
| due_now = concepts with due_at <= now | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |

**h. Brain decision**

advance stored the decision **review language_model_basics** (served later by GET /next). Re-derived from the rules: review language_model_basics (due review with the lowest retrievability): as expected.

<a id="step-13"></a>
## 13. GET .../state

**a. What and why.** Read the state 4 days in.

**b. Request**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/state`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 0 ms

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "clear_instructions",
      "p_mastery": 0.9903447815047441,
      "attempts": 3,
      "failed_rounds": 0,
      "stability_days": 2.5,
      "last_reviewed_at": "2026-10-31T16:46:13.369000",
      "due_at": "2026-11-03T04:46:13.369000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "role_prompting",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example",
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "few_shot_examples",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "output_formatting",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "iterative_refinement",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "hallucination_checking",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    }
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-11-01T16:46:13.274000",
  "due": {
    "language_model_basics": "2026-11-01T16:46:13.274000",
    "prompt_structure": "2026-11-01T16:46:13.274000",
    "sampling_temperature": "2026-11-01T16:46:13.274000",
    "clear_instructions": "2026-11-03T04:46:13.369000",
    "few_shot_examples": "2026-11-02T16:46:13.274000",
    "output_formatting": "2026-11-02T16:46:13.274000",
    "iterative_refinement": "2026-11-02T16:46:13.274000",
    "hallucination_checking": "2026-11-02T16:46:13.274000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.809999935048208,
    "prompt_structure": 0.809999935048208,
    "sampling_temperature": 0.809999935048208,
    "context_window": 1.0,
    "clear_instructions": 0.8812335104294008,
    "role_prompting": 1.0,
    "few_shot_examples": 0.8689403996930175,
    "output_formatting": 0.8689403996930175,
    "iterative_refinement": 0.8689403996930175,
    "hallucination_checking": 0.8689403996930175
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.875
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |

session_questions: 0; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| language_model_basics retrievability 0.9^(t/S) | 0.81 | 0.81 | OK |
| prompt_structure retrievability 0.9^(t/S) | 0.81 | 0.81 | OK |
| sampling_temperature retrievability 0.9^(t/S) | 0.81 | 0.81 | OK |
| context_window retrievability 0.9^(t/S) | 1 | 1 | OK |
| clear_instructions retrievability 0.9^(t/S) | 0.8812 | 0.8812 | OK |
| role_prompting retrievability 0.9^(t/S) | 1 | 1 | OK |
| few_shot_examples retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| output_formatting retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| iterative_refinement retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| hallucination_checking retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| due (concepts with a schedule) | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |
| gaps | ['context_window', 'role_prompting'] | ['context_window', 'role_prompting'] | OK |

**h. Brain decision**

No brain decision in this step (state read only).

<a id="step-14"></a>
## 14. GET .../next + POST .../attempts (review, wrong)

**a. What and why.** Fetch the stored review and fail it on purpose (all wrong, high confidence): a lapse.

**b. Request (request 1)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/next`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 1)**

status 200, 0 ms

```json
{
  "step": {
    "kind": "review",
    "concept_id": "language_model_basics",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "language_model_basics review due since 2026-11-01; recall now 0.81",
  "lesson": null,
  "questions": [
    {
      "id": "f707cec4-language_model_basics-p1",
      "concept_id": "language_model_basics",
      "prompt": "A model completes 'The sky is' with 'blue' most of the time. What is the most accurate explanation?",
      "options": [
        "It was told to answer blue and will repeat it exactly",
        "It judged blue to be the true color, as a person would",
        "Blue follows that phrase most often in its training text",
        "It checked a stored fact that the sky is blue"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-p2",
      "concept_id": "language_model_basics",
      "prompt": "Why might running the same prompt twice produce different completions?",
      "options": [
        "Completions are sampled from probabilities, so lower-ranked words can be picked",
        "The model rethinks its earlier answer and changes its mind",
        "The model rewrites its stored answer each time it is queried",
        "The prompt reaches the model in a slightly different form each run"
      ]
    }
  ]
}
```

**b. Request (request 2)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/next`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 2)**

status 200, 0 ms

```json
{
  "step": {
    "kind": "review",
    "concept_id": "language_model_basics",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "language_model_basics review due since 2026-11-01; recall now 0.81",
  "lesson": null,
  "questions": [
    {
      "id": "f707cec4-language_model_basics-p1",
      "concept_id": "language_model_basics",
      "prompt": "A model completes 'The sky is' with 'blue' most of the time. What is the most accurate explanation?",
      "options": [
        "It was told to answer blue and will repeat it exactly",
        "It judged blue to be the true color, as a person would",
        "Blue follows that phrase most often in its training text",
        "It checked a stored fact that the sky is blue"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-p2",
      "concept_id": "language_model_basics",
      "prompt": "Why might running the same prompt twice produce different completions?",
      "options": [
        "Completions are sampled from probabilities, so lower-ranked words can be picked",
        "The model rethinks its earlier answer and changes its mind",
        "The model rewrites its stored answer each time it is queried",
        "The prompt reaches the model in a slightly different form each run"
      ]
    }
  ]
}
```

**b. Request (request 3)**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/attempts`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
```json
{
  "answers": [
    {
      "question_id": "f707cec4-language_model_basics-p1",
      "chosen_index": 0,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-language_model_basics-p2",
      "chosen_index": 1,
      "confidence": "high"
    }
  ]
}
```

**c. Response (request 3)**

status 200, 0 ms

```json
{
  "graded": [
    {
      "question_id": "f707cec4-language_model_basics-p1",
      "concept_id": "language_model_basics",
      "correct": false,
      "chosen_tag": "language_model_basics__same_answer_every_time",
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-language_model_basics-p2",
      "concept_id": "language_model_basics",
      "correct": false,
      "chosen_tag": "language_model_basics__model_understands_like_person",
      "confidence": "high"
    }
  ],
  "correct_indices": {
    "f707cec4-language_model_basics-p2": 0,
    "f707cec4-language_model_basics-p1": 2
  },
  "explanations": {
    "f707cec4-language_model_basics-p2": "Generation samples from a probability distribution over next words, so different runs can select different words even for an identical prompt.",
    "f707cec4-language_model_basics-p1": "The model predicts the most probable continuation, and 'blue' is the most common follow-on for that phrase in its training data."
  },
  "mastery": {
    "language_model_basics": 0.255723006486074,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.4814035218438767,
    "clear_instructions": 0.9903447815047441,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [
    "language_model_basics__same_answer_every_time",
    "language_model_basics__model_understands_like_person"
  ],
  "messages": [
    "You slipped on language_model_basics. This happens, it is why reviews exist."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "language_model_basics",
      "target_misconceptions": [
        "language_model_basics__same_answer_every_time",
        "language_model_basics__model_understands_like_person"
      ],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "relearning language_model_basics first: it was mastered, slipped to 0.26 (lapses 1)",
    "lesson": {
      "concept_id": "language_model_basics",
      "style": "contrast",
      "explanation": "You may believe a language model understands your prompt the way a person does, and that the same prompt always returns the same answer. Both beliefs break down. First, the right idea is that a model predicts which text is statistically likely to come next, one small piece at a time, based on the text it receives. The wrong belief treats it as a thinker grasping meaning, but it has no human-style comprehension. It matches patterns learned from enormous amounts of text. Second, the right idea is that outputs can vary between runs. The wrong belief assumes a fixed lookup that returns one answer, but generation usually samples from several probable continuations, so the same prompt can yield different wording or even different conclusions. Where the wrong beliefs break is at the point of choice: the model is selecting among likely options each time, not retrieving a stored response. So when you test a prompt, run it several times, and expect variation rather than a single guaranteed result.",
      "targets": [
        "language_model_basics__same_answer_every_time",
        "language_model_basics__model_understands_like_person"
      ],
      "resources": []
    },
    "questions": [
      {
        "id": "f707cec4-language_model_basics-t1",
        "concept_id": "language_model_basics",
        "prompt": "A support bot is asked for the refund policy of a company whose documents it never saw, and it writes a convincing policy. What best explains this?",
        "options": [
          "It returns the same policy text on every run, so it repeats itself",
          "It continues learned text patterns, so it can invent plausible policy details",
          "It searched the company's policy page and copied the rule",
          "It understood the question and worked out the rule logically"
        ]
      },
      {
        "id": "f707cec4-language_model_basics-t2",
        "concept_id": "language_model_basics",
        "prompt": "A student says a model's photosynthesis explanation must be correct because the model understands biology. What is the best response?",
        "options": [
          "Its wording reflects likely text patterns, so it can sound confident yet be wrong",
          "Its explanation is fixed, so a second request returns identical words",
          "It grasped the science and chose words a child would follow",
          "It checked its internal knowledge base and confirmed the facts"
        ]
      },
      {
        "id": "f707cec4-language_model_basics-d2",
        "concept_id": "language_model_basics",
        "prompt": "A learner asks the same question twice and gets differently worded answers. What best explains this?",
        "options": [
          "Next-word choices are sampled, so wording can differ between runs",
          "The model looked up a different stored answer each time",
          "The model grasped the question differently on the second try",
          "The model is faulty, since it should return identical text each time"
        ]
      }
    ]
  }
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.255723 | 3 | 1 | 1 | 2026-11-03T16:46:13 | 2026-11-04T16:46:13 | 1 | 0 | False | ['contrast'] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |
| language_model_basics__same_answer_every_time | confirmed | 2 | 0 |
| language_model_basics__model_understands_like_person | confirmed | 2 | 0 |

session_questions: 2; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- concepts.language_model_basics.attempts: 1 -> 3
- concepts.language_model_basics.due_at: 2026-11-01T16:46:13 -> 2026-11-04T16:46:13
- concepts.language_model_basics.explanations_tried: [] -> ['contrast']
- concepts.language_model_basics.failed_rounds: 0 -> 1
- concepts.language_model_basics.lapses: 0 -> 1
- concepts.language_model_basics.last_reviewed_at: 2026-10-30T16:46:13 -> 2026-11-03T16:46:13
- concepts.language_model_basics.p_mastery: 0.85 -> 0.255723
- concepts.language_model_basics.stability_days: 2 -> 1
- misconceptions.language_model_basics__model_understands_like_person.clean_streak: (absent) -> 0
- misconceptions.language_model_basics__model_understands_like_person.evidence: (absent) -> 2
- misconceptions.language_model_basics__model_understands_like_person.status: (absent) -> confirmed
- misconceptions.language_model_basics__same_answer_every_time.clean_streak: (absent) -> 0
- misconceptions.language_model_basics__same_answer_every_time.evidence: (absent) -> 2
- misconceptions.language_model_basics__same_answer_every_time.status: (absent) -> confirmed
- session_questions: 0 -> 2

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| GET /next twice returns the same step and questions | identical | identical | OK |
| served_question_ids = the /next questions | ['f707cec4-language_model_basics-p1', 'f707cec4-language_model_basics-p2'] | ['f707cec4-language_model_basics-p1', 'f707cec4-language_model_basics-p2'] | OK |
| f707cec4-language_model_basics-p1 correct | False | False | OK |
| f707cec4-language_model_basics-p1 chosen_tag | language_model_basics__same_answer_every_time | language_model_basics__same_answer_every_time | OK |
| f707cec4-language_model_basics-p2 correct | False | False | OK |
| f707cec4-language_model_basics-p2 chosen_tag | language_model_basics__model_understands_like_person | language_model_basics__model_understands_like_person | OK |
| language_model_basics p_mastery (lapse) | 0.255723 | 0.255723 | OK |
| language_model_basics stability_days | 1 | 1 | OK |
| language_model_basics lapses | 1 | 1 | OK |
| language_model_basics due_at - last_reviewed_at (days) | 1 | 1 | OK |
| language_model_basics mastery in response = Mongo | 0.255723 | 0.255723 | OK |

**h. Brain decision**

Reason: "relearning language_model_basics first: it was mastered, slipped to 0.26 (lapses 1)"

The brain chose **lesson language_model_basics**. Re-derived from the rules: lesson language_model_basics (relearn first: mastered before, slipped and failed since): as expected.

GET /next served **review language_model_basics** (reason: "language_model_basics review due since 2026-11-01; recall now 0.81") with questions ['f707cec4-language_model_basics-p1', 'f707cec4-language_model_basics-p2'].

<a id="step-15"></a>
## 15. GET .../state + GET .../next (relearn lesson)

**a. What and why.** Read the state after the lapse and show the relearn lesson, also served by GET /next.

**b. Request (request 1)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/state`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 1)**

status 200, 0 ms

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.255723006486074,
      "attempts": 3,
      "failed_rounds": 1,
      "stability_days": 1.0,
      "last_reviewed_at": "2026-11-03T16:46:13.428000",
      "due_at": "2026-11-04T16:46:13.428000",
      "lapses": 1,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-01T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "clear_instructions",
      "p_mastery": 0.9903447815047441,
      "attempts": 3,
      "failed_rounds": 0,
      "stability_days": 2.5,
      "last_reviewed_at": "2026-10-31T16:46:13.369000",
      "due_at": "2026-11-03T04:46:13.369000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "role_prompting",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example",
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "few_shot_examples",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "output_formatting",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "iterative_refinement",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "hallucination_checking",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 3.0,
      "last_reviewed_at": "2026-10-30T16:46:13.274000",
      "due_at": "2026-11-02T16:46:13.274000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    }
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "language_model_basics__same_answer_every_time",
      "concept_id": "language_model_basics",
      "status": "confirmed",
      "evidence": 2.0,
      "clean_streak": 0
    },
    {
      "tag": "language_model_basics__model_understands_like_person",
      "concept_id": "language_model_basics",
      "status": "confirmed",
      "evidence": 2.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-11-01T16:46:13.274000",
  "due": {
    "language_model_basics": "2026-11-04T16:46:13.428000",
    "prompt_structure": "2026-11-01T16:46:13.274000",
    "sampling_temperature": "2026-11-01T16:46:13.274000",
    "clear_instructions": "2026-11-03T04:46:13.369000",
    "few_shot_examples": "2026-11-02T16:46:13.274000",
    "output_formatting": "2026-11-02T16:46:13.274000",
    "iterative_refinement": "2026-11-02T16:46:13.274000",
    "hallucination_checking": "2026-11-02T16:46:13.274000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "language_model_basics",
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9999999757134259,
    "prompt_structure": 0.8099999141068197,
    "sampling_temperature": 0.8099999141068197,
    "context_window": 1.0,
    "clear_instructions": 0.8812334922029765,
    "role_prompting": 1.0,
    "few_shot_examples": 0.868940384716211,
    "output_formatting": 0.868940384716211,
    "iterative_refinement": 0.868940384716211,
    "hallucination_checking": 0.868940384716211
  },
  
[truncated, 6103 chars]
```

**b. Request (request 2)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/next`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 2)**

status 200, 16 ms

```json
{
  "step": {
    "kind": "lesson",
    "concept_id": "language_model_basics",
    "target_misconceptions": [
      "language_model_basics__same_answer_every_time",
      "language_model_basics__model_understands_like_person"
    ],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "relearning language_model_basics first: it was mastered, slipped to 0.26 (lapses 1)",
  "lesson": {
    "concept_id": "language_model_basics",
    "style": "contrast",
    "explanation": "You may believe a language model understands your prompt the way a person does, and that the same prompt always returns the same answer. Both beliefs break down. First, the right idea is that a model predicts which text is statistically likely to come next, one small piece at a time, based on the text it receives. The wrong belief treats it as a thinker grasping meaning, but it has no human-style comprehension. It matches patterns learned from enormous amounts of text. Second, the right idea is that outputs can vary between runs. The wrong belief assumes a fixed lookup that returns one answer, but generation usually samples from several probable continuations, so the same prompt can yield different wording or even different conclusions. Where the wrong beliefs break is at the point of choice: the model is selecting among likely options each time, not retrieving a stored response. So when you test a prompt, run it several times, and expect variation rather than a single guaranteed result.",
    "targets": [
      "language_model_basics__same_answer_every_time",
      "language_model_basics__model_understands_like_person"
    ],
    "resources": []
  },
  "questions": [
    {
      "id": "f707cec4-language_model_basics-t1",
      "concept_id": "language_model_basics",
      "prompt": "A support bot is asked for the refund policy of a company whose documents it never saw, and it writes a convincing policy. What best explains this?",
      "options": [
        "It returns the same policy text on every run, so it repeats itself",
        "It continues learned text patterns, so it can invent plausible policy details",
        "It searched the company's policy page and copied the rule",
        "It understood the question and worked out the rule logically"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-t2",
      "concept_id": "language_model_basics",
      "prompt": "A student says a model's photosynthesis explanation must be correct because the model understands biology. What is the best response?",
      "options": [
        "Its wording reflects likely text patterns, so it can sound confident yet be wrong",
        "Its explanation is fixed, so a second request returns identical words",
        "It grasped the science and chose words a child would follow",
        "It checked its internal knowledge base and confirmed the facts"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-d2",
      "concept_id": "language_model_basics",
      "prompt": "A learner asks the same question twice and gets differently worded answers. What best explains this?",
      "options": [
        "Next-word choices are sampled, so wording can differ between runs",
        "The model looked up a different stored answer each time",
        "The model grasped the question differently on the second try",
        "The model is faulty, since it should return identical text each time"
      ]
    }
  ]
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.255723 | 3 | 1 | 1 | 2026-11-03T16:46:13 | 2026-11-04T16:46:13 | 1 | 0 | False | ['contrast'] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |
| language_model_basics__same_answer_every_time | confirmed | 2 | 0 |
| language_model_basics__model_understands_like_person | confirmed | 2 | 0 |

session_questions: 2; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| language_model_basics retrievability 0.9^(t/S) | 1 | 1 | OK |
| prompt_structure retrievability 0.9^(t/S) | 0.81 | 0.81 | OK |
| sampling_temperature retrievability 0.9^(t/S) | 0.81 | 0.81 | OK |
| context_window retrievability 0.9^(t/S) | 1 | 1 | OK |
| clear_instructions retrievability 0.9^(t/S) | 0.8812 | 0.8812 | OK |
| role_prompting retrievability 0.9^(t/S) | 1 | 1 | OK |
| few_shot_examples retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| output_formatting retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| iterative_refinement retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| hallucination_checking retrievability 0.9^(t/S) | 0.8689 | 0.8689 | OK |
| due (concepts with a schedule) | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | ['clear_instructions', 'few_shot_examples', 'hallucination_checking', 'iterative_refinement', 'language_model_basics', 'output_formatting', 'prompt_structure', 'sampling_temperature'] | OK |
| gaps | ['language_model_basics', 'context_window', 'role_prompting'] | ['language_model_basics', 'context_window', 'role_prompting'] | OK |
| GET /next = the step returned by step 14 | same step and questions | same | OK |

**h. Brain decision**

No brain decision in this step (state read only).

Next step from step 14's response: **lesson language_model_basics**

Reason: "relearning language_model_basics first: it was mastered, slipped to 0.26 (lapses 1)"

Step: `{"kind": "lesson", "concept_id": "language_model_basics", "target_misconceptions": ["language_model_basics__same_answer_every_time", "language_model_basics__model_understands_like_person"], "avoid_styles": [], "difficulty": null, "target_concept": null, "give_up_after": false}`

Lesson style **contrast**, targets ['language_model_basics__same_answer_every_time', 'language_model_basics__model_understands_like_person'], 168 words, 0 resources:

> You may believe a language model understands your prompt the way a person does, and that the same prompt always returns the same answer. Both beliefs break down. First, the right idea is that a model predicts which text is statistically likely to come next, one small piece at a time, based on the text it receives. The wrong belief treats it as a thinker grasping meaning, but it has no human-style comprehension. It matches patterns learned from enormous amounts of text. Second, the right idea is that outputs can vary between runs. The wrong belief assumes a fixed lookup that returns one answer, but generation usually samples from several probable continuations, so the same prompt can yield different wording or even different conclusions. Where the wrong beliefs break is at the point of choice: the model is selecting among likely options each time, not retrieving a stored response. So when you test a prompt, run it several times, and expect variation rather than a single guaranteed result.

Questions:
- [f707cec4-language_model_basics-t1] A support bot is asked for the refund policy of a company whose documents it never saw, and it writes a convincing policy. What best explains this?
  0. It returns the same policy text on every run, so it repeats itself
  1. It continues learned text patterns, so it can invent plausible policy details
  2. It searched the company's policy page and copied the rule
  3. It understood the question and worked out the rule logically
- [f707cec4-language_model_basics-t2] A student says a model's photosynthesis explanation must be correct because the model understands biology. What is the best response?
  0. Its wording reflects likely text patterns, so it can sound confident yet be wrong
  1. Its explanation is fixed, so a second request returns identical words
  2. It grasped the science and chose words a child would follow
  3. It checked its internal knowledge base and confirmed the facts
- [f707cec4-language_model_basics-d2] A learner asks the same question twice and gets differently worded answers. What best explains this?
  0. Next-word choices are sampled, so wording can differ between runs
  1. The model looked up a different stored answer each time
  2. The model grasped the question differently on the second try
  3. The model is faulty, since it should return identical text each time

<a id="step-16"></a>
## 16. POST .../sessions/new

**a. What and why.** Start a new session: the session counter resets.

**b. Request**

`POST http://127.0.0.1:8000/courses/b0dafa63/learners/trace/sessions/new`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response**

status 200, 15 ms

```json
{
  "session_questions": 0,
  "next_kind": "lesson",
  "next_concept_id": "language_model_basics"
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.255723 | 3 | 1 | 1 | 2026-11-03T16:46:13 | 2026-11-04T16:46:13 | 1 | 0 | False | ['contrast'] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |
| language_model_basics__same_answer_every_time | confirmed | 2 | 0 |
| language_model_basics__model_understands_like_person | confirmed | 2 | 0 |

session_questions: 0; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

- session_questions: 2 -> 0

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| session_questions | 0 | 0 | OK |

**h. Brain decision**

no brain decision in this step

<a id="step-17"></a>
## 17. Unwired and eval routes

**a. What and why.** Probe the research, virtual-learner and eval routes and record their status codes.

**b. Request (request 1)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/resources`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 1)**

status 404, 0 ms

```json
{
  "detail": "Not Found"
}
```

**b. Request (request 2)**

`GET http://127.0.0.1:8000/courses/b0dafa63/learners/trace/virtual/status`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 2)**

status 404, 0 ms

```json
{
  "detail": "Not Found"
}
```

**b. Request (request 3)**

`GET http://127.0.0.1:8000/eval/results`

```json
{
  "X-Master-Password": "***",
  "Content-Type": "application/json"
}
```
(no body)

**c. Response (request 3)**

status 404, 0 ms

```json
{
  "detail": "no eval results yet"
}
```

**d. External calls**

none

**e. Internal state (Mongo)**

| concept | p_mastery | attempts | failed_rounds | stability_days | last_reviewed_at | due_at | lapses | fallbacks | needs_help | explanations_tried |
|---|---|---|---|---|---|---|---|---|---|---|
| language_model_basics | 0.255723 | 3 | 1 | 1 | 2026-11-03T16:46:13 | 2026-11-04T16:46:13 | 1 | 0 | False | ['contrast'] |
| prompt_structure | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| sampling_temperature | 0.85 | 1 | 0 | 2 | 2026-10-30T16:46:13 | 2026-11-01T16:46:13 | 0 | 0 | False | [] |
| context_window | 0.481404 | 4 | 2 | 0 | None | None | 0 | 0 | False | ['contrast'] |
| clear_instructions | 0.990345 | 3 | 0 | 2.5 | 2026-10-31T16:46:13 | 2026-11-03T04:46:13 | 0 | 0 | False | [] |
| role_prompting | 0.177419 | 1 | 1 | 0 | None | None | 0 | 0 | False | ['worked_example', 'contrast'] |
| few_shot_examples | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| output_formatting | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| iterative_refinement | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |
| hallucination_checking | 0.85 | 1 | 0 | 3 | 2026-10-30T16:46:13 | 2026-11-02T16:46:13 | 0 | 0 | False | [] |

Misconceptions:

| tag | status | evidence | clean_streak |
|---|---|---|---|
| context_window__model_remembers_everything | resolved | 0 | 2 |
| role_prompting__any_role_works_equally | suspected | 1 | 0 |
| context_window__limit_is_only_words | suspected | 1 | 0 |
| language_model_basics__same_answer_every_time | confirmed | 2 | 0 |
| language_model_basics__model_understands_like_person | confirmed | 2 | 0 |

session_questions: 0; clock_offset_days: 4
roadmap: ['language_model_basics', 'prompt_structure', 'sampling_temperature', 'context_window', 'clear_instructions', 'role_prompting', 'few_shot_examples', 'output_formatting', 'iterative_refinement', 'hallucination_checking']
history: no history field in the stored state
lesson cache keys (8): `fae5bdd0a84d` (context_window, worked_example), `03aa2bd2c538` (context_window, contrast), `57a06ef6b5df` (clear_instructions, worked_example), `c2c5d5787720` (output_formatting, worked_example), `a7053b613db2` (context_window, contrast), `f5dac577b06d` (role_prompting, worked_example), `7c9f53433335` (role_prompting, contrast), `4978e19f6bc7` (language_model_basics, contrast)

**f. What changed**

nothing

**g. Independent check**

| quantity | expected | actual | result |
|---|---|---|---|
| /eval/results status | 404 | 404 | OK |

**h. Brain decision**

No brain decision.

- `/courses/b0dafa63/learners/trace/resources` -> 404
- `/courses/b0dafa63/learners/trace/virtual/status` -> 404
- `/eval/results` -> 404

## Trajectories

### p_mastery after each step

| step | language_model_basics | prompt_structure | sampling_temperature | context_window | clear_instructions | role_prompting | few_shot_examples | output_formatting | iterative_refinement | hallucination_checking |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 | 0.200 |
| 5 | 0.850 | 0.850 | 0.850 | 0.177 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 6 | 0.850 | 0.850 | 0.850 | 0.177 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 7 | 0.850 | 0.850 | 0.850 | 0.481 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 8 | 0.850 | 0.850 | 0.850 | 0.481 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 9 | 0.850 | 0.850 | 0.850 | 0.481 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 10 | 0.850 | 0.850 | 0.850 | 0.481 | 0.850 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 11 | 0.850 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 12 | 0.850 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 13 | 0.850 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 14 | 0.256 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 15 | 0.256 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 16 | 0.256 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |
| 17 | 0.256 | 0.850 | 0.850 | 0.481 | 0.990 | 0.177 | 0.850 | 0.850 | 0.850 | 0.850 |

### retrievability (at the step's simulated now)

| step | language_model_basics | prompt_structure | sampling_temperature | context_window | clear_instructions | role_prompting | few_shot_examples | output_formatting | iterative_refinement | hallucination_checking |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 8 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 9 | 0.949 | 0.949 | 0.949 | 1.000 | 0.900 | 1.000 | 0.965 | 0.965 | 0.965 | 0.965 |
| 10 | 0.949 | 0.949 | 0.949 | 1.000 | 0.900 | 1.000 | 0.965 | 0.965 | 0.965 | 0.965 |
| 11 | 0.949 | 0.949 | 0.949 | 1.000 | 1.000 | 1.000 | 0.965 | 0.965 | 0.965 | 0.965 |
| 12 | 0.810 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |
| 13 | 0.810 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |
| 14 | 1.000 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |
| 15 | 1.000 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |
| 16 | 1.000 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |
| 17 | 1.000 | 0.810 | 0.810 | 1.000 | 0.881 | 1.000 | 0.869 | 0.869 | 0.869 | 0.869 |

### stability_days

| step | language_model_basics | prompt_structure | sampling_temperature | context_window | clear_instructions | role_prompting | few_shot_examples | output_formatting | iterative_refinement | hallucination_checking |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 5 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 6 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 7 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 8 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 9 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 10 | 2.000 | 2.000 | 2.000 | 0.000 | 1.000 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 11 | 2.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 12 | 2.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 13 | 2.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 14 | 1.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 15 | 1.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 16 | 1.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |
| 17 | 1.000 | 2.000 | 2.000 | 0.000 | 2.500 | 0.000 | 3.000 | 3.000 | 3.000 | 3.000 |


## Problems found

- step 5: lesson has no resources (get_resources is a stub)
- step 7: lesson has no resources (get_resources is a stub)
- step 11: lesson has no resources (get_resources is a stub)
- step 14: lesson has no resources (get_resources is a stub)

## Not verified

- Log attribution is by arrival time of each server log line between request start and end; background work (e.g. generation) logged during another request would be attributed to it.
- Simulated 'now' is approximated in the script as real UTC at request start plus the offset; comparisons use a 0.001 tolerance on retrievability.
- `/resources`: the route does not exist yet (404).
- `/virtual/status`: the route does not exist yet (404).
