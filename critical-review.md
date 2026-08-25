# Critical Self-Review, Correction, and Final Rewrite

Critically review all work you have completed during this task before presenting your final answer.

## Objective

Identify and correct factual errors, missing steps, unsupported assumptions, contradictions, incomplete implementation, misleading claims, and invented or unverified details. Then produce a more precise, complete, and reliable final answer.

## Required Review Process

### 1. Re-examine the original request

* Re-read the complete user request and all stated requirements.
* Confirm that every requirement has been addressed.
* Identify anything that was misunderstood, omitted, or handled only partially.
* Distinguish explicitly requested requirements from assumptions you introduced.

### 2. Verify your work against available evidence

Where applicable, verify claims against:

* The actual repository and source files.
* Configuration files and environment settings.
* Database schemas and migrations.
* API contracts and integration documentation.
* Test results, command output, logs, diffs, and generated artifacts.
* Authoritative external documentation when current external facts are involved.

Do not treat earlier statements, plans, summaries, or model-generated descriptions as proof.

### 3. Identify problems

Look specifically for:

* Factual or technical errors.
* Missing requirements or implementation steps.
* Unsupported conclusions.
* Invented filenames, functions, endpoints, schemas, settings, or system behaviour.
* Assumptions presented as confirmed facts.
* Contradictions between different parts of the work.
* Changes described as completed but not actually implemented.
* Tests described as passing without evidence.
* Unhandled edge cases and failure paths.
* Security, privacy, permission, concurrency, or data-integrity risks.
* Regressions or compatibility problems.
* Overly broad, vague, or misleading language.
* Recommendations that do not fit the existing architecture.
* Temporary workarounds presented as complete solutions.

### 4. Classify every material finding

For each issue, determine whether it is:

* *Confirmed error* — contradicted by available evidence.
* *Missing work* — required but not completed.
* *Unsupported assumption* — plausible but not verified.
* *Unverified claim* — evidence is currently unavailable.
* *Quality improvement* — technically acceptable but could be clearer, safer, or more robust.
* *No issue* — verified and correct.

Do not manufacture criticism merely to appear thorough.

### 5. Propose and apply corrections

For every confirmed issue:

* Explain briefly what is wrong.
* State the correction or improvement required.
* Apply the correction directly when tools, permissions, and available evidence allow it.
* Update affected code, configuration, documentation, tests, or conclusions.
* Re-run relevant validation after applying changes.
* Check that the fix does not create new regressions.

If a correction cannot be applied:

* State exactly what is blocking it.
* Do not claim that it was fixed.
* Provide a concrete next action.
* Clearly separate the remaining blocker from completed work.

### 6. Validate the corrected result

After applying corrections:

* Inspect the final changes or revised reasoning.
* Run the most relevant available tests and checks.
* Report actual results accurately.
* Do not convert warnings, skipped tests, partial execution, or environment failures into successful results.
* Never claim that code was executed, tested, committed, deployed, or verified unless evidence confirms it.
* Preserve unrelated user changes and avoid destructive operations.

## Final Response Requirements

Rewrite the complete answer so that it replaces the earlier answer rather than merely appending corrections to it.

The rewritten answer must:

* Lead with the corrected outcome.
* Address the original request completely.
* Include only facts supported by evidence.
* Clearly label any remaining assumptions or unverified points.
* Distinguish completed work from proposed or blocked work.
* Include relevant files, components, commands, tests, results, and evidence where applicable.
* Explain material limitations and remaining risks.
* Remove invented, redundant, vague, or misleading content.
* Be precise enough that another engineer or reviewer can reproduce and verify the result.

Use this final structure:

# Corrected Final Answer

## Outcome

Provide the corrected and concise result.

## Issues Found and Corrected

List each material issue discovered, its classification, and the correction applied. If no material issues were found, say so explicitly and describe what was verified.

## Verified Changes or Findings

Describe only changes or conclusions supported by evidence.

## Validation

Report the checks and tests performed, including their actual results. Clearly identify anything that could not be tested.

## Remaining Risks, Assumptions, or Blockers

List unresolved matters. If none remain, state that explicitly.

## Next Steps

Include only necessary follow-up actions, if any.

## Confidence

End the response with exactly:

*Confidence: X/10*

Choose the score based on evidence, not optimism:

* *9–10:* Directly verified with strong evidence and comprehensive testing.
* *7–8:* Substantially verified with minor limitations.
* *5–6:* Partially verified with meaningful assumptions or test gaps.
* *3–4:* Significant uncertainty, missing access, or incomplete validation.
* *1–2:* Mostly speculative or seriously incomplete.

Do not assign *10/10* when any material claim, test, dependency, integration, or implementation detail remains unverified.
