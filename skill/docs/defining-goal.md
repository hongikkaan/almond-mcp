# Defining Goal

## Purpose and boundary

Turn an idea, problem, or assignment into a **critically examined, explicitly user-aligned Plan Goal**. This is an interactive decision-making process, not a questionnaire or an exercise in filling out a template.

**The Plan Goal records the agreed working direction for design development.** Defining the task and executing the task are distinct stages, not necessarily distinct agents or sessions. The same agent carries that direction into the Plan workflow if the user has already authorized execution or subsequently requests it. Do not force a handoff, new chat, or subagent. Recording the Goal or classifying its Work Mode as EXECUTION & PRODUCTION does not itself authorize execution.

Keep the user's critical decisions with the user; own the investigation, reasoning, alternatives, and recommendations required to support those decisions. **Alignment takes precedence over minimizing questions or conversational turns.**

## Procedure

### 1. Establish the starting position

Use the current request, relevant conversation history, established decisions, and available project evidence. Distinguish confirmed facts, earlier proposals, superseded decisions, assumptions, and unresolved issues.

Investigate facts that can reasonably be established through available sources before asking the user to choose a technical scope or boundary that depends on them. Do not make the user repeat known facts or perform your investigative work. Read only materials relevant to defining the assignment. Do not modify the subject project during this skill without separate authorization.

Identify the provisional objective and what remains undecided. If even the underlying problem is unclear, begin by discussing that rather than prematurely selecting an implementation approach.

### 2. Map decisions before asking

Distinguish:

- **Discoverable facts:** independently research and verify when relevant.
- **User-owned decisions:** objectives, values, priorities, design direction, material trade-offs, important exclusions, risk tolerance, and consequential permissions. Discuss and obtain alignment.
- **Agent-owned decisions:** routine technical methods, low-risk implementation details, and investigation approaches. Leave to the competent executing agent unless the user specifies them or their consequences are material.

Construct a compact decision map with states and sources. Check it before reopening a question, after a user correction, and when resuming or handing off work. Ask upstream, consequential questions before their downstream details. Do not classify an important design or scope decision as a mere technical detail to avoid discussion.

### 3. Interview for genuine alignment

- Conduct the interview in **Korean** unless the user requests otherwise.
- Favor an open, high-value question that advances a consequential decision. You may group up to three **independent** questions when they are naturally discussed together; do not impose a question quota or rush an unresolved discussion.
- Surface alternative interpretations, hidden assumptions, material dependencies, conflicts, and failure scenarios. Challenge weak premises, with reasons and better options where possible.
- Supply an evidence-based provisional recommendation **separately from the neutral question**, including the principal trade-offs. Invite rejection, modification, or deferral. Do not treat a polite “yes,” silence, or quick assent as substantive agreement when important implications remain unexamined.
- Explore contradictions and consequential misunderstandings until aligned. Do not manufacture disagreement or reopen settled decisions without a relevant change. Explain what changed when renewed alignment is needed. Keep explicitly deferred work separate unless an evidenced dependency makes it necessary now.
- Do not substitute speed, question-count targets, or a theoretical interruption cost for the quality of mutual understanding.

The goal is neither to maximize questions nor to minimize them. It is to reach an informed, shared understanding of the intended task.

### 4. Classify the Work Mode and authority

Identify one **primary** Work Mode, with supporting modes or phases only if useful:

1. **RESEARCH** — discover and substantiate information.
2. **ANALYSIS & CRITIQUE** — evaluate evidence, premises, alternatives, and consequences.
3. **REVIEW & AUDIT** — assess an existing artifact or system against criteria.
4. **EXECUTION & PRODUCTION** — create, implement, change, repair, or operate within authorization.

For multi-mode work, identify relevant phase transitions and what each transition permits. **Mode labels describe work, not permission grants.** Recording an execution phase does not itself authorize edits, publication, deployment, or consequential actions.

Discuss any material uncertainty concerning scope, mode choice, allowed changes, or authority with the user. Be especially clear about whether the task is limited to investigation/recommendation or extends to changing the subject.

### 5. Define quality, evidence, and completion

Agree on the purpose, expected deliverables, non-negotiable requirements, exclusions, priorities, and success criteria. Tailor acceptance standards to the task: evidence quality for research, reasoning and trade-offs for analysis, traceable findings for audit, observable results and regression protection for execution.

Prefer **verifiable, outcome-focused** criteria over arbitrary metrics or procedural micromanagement. Preserve explicit methods if the user requires them. Where the answer depends on a prototype or subsequent discovery, identify that as a decision gate rather than manufacturing certainty.

Make the intended end state concrete with a representative use case or before/after example when abstract labels could hide different expectations. Include consequential residual limits, such as shared responsibilities or retained compatibility paths. Distinguish preservation checks from evidence of the user's intended benefit; if that benefit needs later use to verify, record the bounded check and its status instead of claiming it is proven. For work depending on external review or real-environment validation, state what completion evidence is required and who resolves unavailable evidence; do not invent a mandatory review or deployment gate.

### 6. Synthesize, challenge, and explicitly confirm

Propose a coherent **Plan Goal** that says what to develop, why, and what must hold while exploring it. It preserves material user decisions and their rationale, separates facts from assumptions, and identifies unresolved consequential issues.

**Present the draft or an accurate decision-level synopsis to the user for explicit alignment.** Invite corrections, challenges, and revisions. Do not equate “I can proceed” with “we agree,” and do not treat the absence of objection as consent.

Revise with the user as needed. A consequential unresolved user-owned decision requires explicit resolution, explicit deferral with an appropriate decision gate, or an explicitly provisional Goal; do not silently decide it.

### 7. Record the Goal and carry it into the design work

After alignment, set or update the Plan Goal. State what to develop and why, the conditions to keep, and the choices left open for exploration. When execution is authorized, start or resume the Loop with `plan_03-execute_looping` and follow the Steps of that Plan.

Carry the reasoning into the drawing and modeling. The Goal sets a direction to test, not an answer to implement unchanged. Revisit relevant choices when work or critique uncovers evidence that changes the direction. Discuss consequential changes to user-set conditions with the user and record what prompted the change. Do not restart the whole interview for an unaffected decision.

## Completion check

Before recording the Plan Goal, verify:

- The user's actual objective and governing priorities are understood by both parties.
- Material assumptions and contradictions have been examined; significant decisions are accurately recorded.
- Work Mode, phase boundaries, and operational authority are distinguished.
- In scope / out of scope, critical invariants, and prohibited changes are explicit.
- Deliverables and acceptance criteria would meaningfully test success.
- The Goal delegates ordinary professional methodology without transferring user-owned decisions.
- The user **explicitly confirmed** the consequential choices that needed their decision.
- No unrequested implementation or handoff occurred during definition.

**Operating principle:** Investigate facts; discuss values and consequential choices; challenge intelligently; converge through explicit agreement; then carry that understanding into the design work.
