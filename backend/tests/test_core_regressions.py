import warnings; warnings.filterwarnings("ignore")
from datetime import datetime
from schemas.learner import *
from schemas.content import *
from core.clock import Clock
from core.engine import submit_answers, get_next

_LS = LearnerState
def LearnerState(**kw): return _LS(learner_id="l", course_id="c", **kw)

def A(q, c, ok, tag=None, conf=None):
    return AnswerGraded(question_id=q, concept_id=c, correct=ok, chosen_tag=tag, confidence=conf)

qs = [Question.model_construct(id=f"q{i}", concept_id="A", options=[]) for i in range(40)] + \
     [Question.model_construct(id=f"b{i}", concept_id="B", options=[]) for i in range(40)]
graph = ConceptGraph.model_construct(concepts=[
    Concept.model_construct(id="A", prerequisites=[]),
    Concept.model_construct(id="B", prerequisites=["A"]),
    Concept.model_construct(id="C", prerequisites=[]),
])
cfg = PolicyConfig(max_questions_per_session=1000)
run = lambda s, a, clk, c=cfg: submit_answers(s, qs, a, c, clk)

print("2) Stability during one session (6 single-answer rounds):")
clk = Clock(datetime(2026,1,1)); s = LearnerState()
for i in range(6): s = run(s, [A(f"q{i}","A",True)], clk)
c = s.concepts["A"]; print(f"   p={c.p_mastery:.3f} S={c.stability_days} due={c.due_at}  (should stay S=1)")

print("3) Wrong answer on a mastered concept:")
s2 = run(s.model_copy(deep=True), [A("q10","A",False)], clk); c = s2.concepts["A"]
print(f"   p={c.p_mastery:.3f} S={c.stability_days} lapses={c.lapses}")

print("4) Failed review then pass:")
s3 = LearnerState(); clk3 = Clock(datetime(2026,1,1))
for i in range(3): s3 = run(s3, [A(f"q{i}","A",True)], clk3)
clk3.advance(days=2); print("   next:", get_next(s3, graph, cfg, clk3).kind)
s3 = run(s3, [A("q5","A",False)], clk3); c = s3.concepts["A"]
print(f"   after wrong: p={c.p_mastery:.3f} lapses={c.lapses} due={c.due_at} next={get_next(s3, graph, cfg, clk3).kind}")

print("5) Ranking: C has 0.6, A unseen 0.2 ->", end=" ")
s4 = LearnerState(); s4.concepts["C"] = ConceptState(concept_id="C", p_mastery=0.6)
print(get_next(s4, graph, cfg, Clock(datetime(2026,1,1))).concept_id, "(lowest effective mastery first)")

print("6) Stuck on B: fallback once, then give up instead of looping:")
s5 = LearnerState(); clk5 = Clock(datetime(2026,1,1))
for i in range(3): s5 = run(s5, [A(f"q{i}","A",True)], clk5)
s5.concepts["C"] = ConceptState(concept_id="C", p_mastery=0.95)
seq = []; n = 0
for r in range(12):
    st = get_next(s5, graph, cfg, clk5); seq.append(f"{st.kind}:{st.concept_id}")
    if st.kind in ("done", "session_end"): break
    cid = st.concept_id
    ok = cid == "A"
    s5 = run(s5, [A(f"{'q' if cid=='A' else 'b'}{20+n}", cid, ok)], clk5); n += 1
print("  ", " -> ".join(seq), "| B needs_help:", s5.concepts["B"].needs_help)

print("7) Static baseline on a fresh learner:",
      get_next(LearnerState(roadmap=["A","B","C"]), graph, PolicyConfig(adaptive=False), Clock(datetime(2026,1,1))).concept_id)

print("8) One round of 3 wrong answers -> failed_rounds =",
      run(LearnerState(), [A("b1","B",False), A("b2","B",False), A("b3","B",False)], Clock(datetime(2026,1,1))).concepts["B"].failed_rounds)

print("9) Session cap 15:", end=" ")
s8 = LearnerState(); c8 = Clock(datetime(2026,1,1))
for i in range(16): s8 = submit_answers(s8, qs, [A(f"b{i}","B",False)], PolicyConfig(), c8)
print(get_next(s8, graph, PolicyConfig(), c8).kind)

print("10) Misconception regression:", end=" ")
s9 = LearnerState(); c9 = Clock(datetime(2026,1,1))
s9 = run(s9, [A("q1","A",False,"m1","high")], c9)
s9 = run(s9, [A("q2","A",True), A("q3","A",True)], c9); a = s9.misconceptions["m1"].status
s9 = run(s9, [A("q4","A",False,"m1","high")], c9)
print(a, "->", s9.misconceptions["m1"].status)