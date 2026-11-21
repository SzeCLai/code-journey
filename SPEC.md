# CodeJourney Specification

## Purpose and scope

CodeJourney is an educational Python execution visualizer for Jupyter
Notebooks. It helps beginners follow how code executes; it is not a full
debugger and does not provide breakpoints, stepping control over a live
session, or a security sandbox.

This document is the source of truth for the initial implementation.

## Public interface and notebook integration

- Importing `codejourney` in a live IPython/Jupyter environment automatically
  registers the `%%pyviz` cell magic. Registration is idempotent. Importing
  outside IPython succeeds without requiring IPython to be installed.
- `%%pyviz` analyzes and runs its cell's Python source, then displays the
  resulting visualization in the notebook.
- `run_viz(code_str: str, *, max_steps: int = 500) -> VisualizationResult`
  provides the same execution analysis without a live notebook. The result
  exposes `_repr_html_()` and is directly testable using pytest.
- `max_steps` must be a positive integer. Invalid input raises a clear
  `TypeError` or `ValueError`.

## Execution analysis

Use Python's `ast` module together with `sys.settrace`. AST analysis supplies
source structure and loop/condition metadata; tracing captures observed
execution. Each captured step includes the source line number, source text,
and before/after variable snapshots. Source line numbers are relative to the
provided code string and remain stable in the visualization.

Snapshots compare supported built-in values (including nested lists and
dictionaries) without invoking student-defined equality or display methods.
Each step reports added, removed, and modified variables. In-place changes
must still appear as modifications, even when the variable's identity does
not change. List changes identify affected indices; dictionary changes
identify affected keys. Unsupported values receive a safe type-oriented
display rather than arbitrary `repr()` execution.

Detect shared references using `id()` over observed objects and label aliases
with readable names, for example **Linked to `a`**. Alias reporting describes
shared identity; it must not imply that separate equal values are aliases.

### Loops and conditions

Track `for` and `while` loops as first-class execution regions, including
iteration start/end boundaries, loop identity, nesting, and iteration index.
The interface uses one-based labels such as **Iteration 1 of N**. Show a
known total when execution establishes it; use an unknown-total label until
then, and for loops whose total cannot be determined. Navigation can jump
between iteration boundaries as well as individual execution steps.

For `if`, `elif`, and `while` conditions, provide a preview when the expression
can be safely represented from captured values. For example:

`x > 2 -> 4 > 2 -> True`

Do not re-evaluate an expression just to render a preview. If a safe preview
cannot be produced, show the original expression and indicate that its value
is unavailable.

### Educational warnings

Display concise warnings for supported, recognizable cases of:

- Mutating a list while iterating over that list.
- `return` during loop iteration 0.
- `break` during loop iteration 0.
- Assigning to or defining a name that shadows a Python built-in.

Warnings are educational indicators, not proof of a defect. Static AST
patterns and observed trace events may be combined; unsupported or ambiguous
patterns should not produce confident claims.

## Educational Differentiators

Traditional execution visualizers often present execution as a flat sequence
of line-by-line states. CodeJourney is designed to help beginners understand
the patterns behind execution, especially how loop iterations and values
relate:

- **Iteration-aware navigation:** Treat loop iterations as first-class
  landmarks, so learners can move between iterations and inspect their
  boundaries instead of losing loop structure in a long sequence of steps.
- **Variable-diff-based learning:** Emphasize what changed between steps,
  including modified variables and affected collection entries, rather than
  requiring learners to compare complete state snapshots themselves.
- **Alias detection:** Make shared references visible with labels such as
  **Linked to `a`**, helping explain why changing one name can affect an
  object observed through another.
- **Condition evaluation peeks:** Show a readable substitution and result,
  such as `x > 2 -> 4 > 2 -> True`, to connect a condition in source code to
  the branch or loop behavior that follows.
- **Beginner bug spotting:** Call attention to recognizable learning hazards,
  including mutation during iteration, early `return` or `break` in the first
  iteration, and shadowed built-ins. These are educational prompts, not
  definitive diagnoses.

## Visualization

`VisualizationResult._repr_html_()` returns self-contained HTML, CSS, and
JavaScript with no external network dependencies. Escape source text, labels,
warnings, and serialized data for their output context.

The interface includes:

- A timeline slider, **Prev**, **Next**, and **Jump to Next Change** controls.
- Iteration-aware navigation and a loop iteration badge.
- Warning alerts and variable-diff cards.
- Current-line highlighting in the source listing.

The current source line, selected execution state, and loop/iteration metadata
must stay synchronized as the user navigates. Jump to Next Change selects the
next step with a variable or collection mutation, and reports when none
remains.

## Safety and execution behavior

`max_steps` defaults to 500 traced execution steps. Reaching the limit stops
further traced execution and returns the captured partial visualization with a
clear truncation warning. Syntax and runtime errors are represented explicitly
alongside available partial analysis; they must not be presented as successful
completion.

Tracing must be scoped to CodeJourney's execution and restore any previously
installed trace function, including when execution raises or reaches the step
limit. Each `run_viz` call uses an isolated execution namespace.

**Execution is not sandboxed.** An analyzed program runs with the Python
process's normal permissions and can perform I/O, access the network, or block
inside native code. The step limit bounds traced Python execution only; it is
not a timeout or a security boundary. The notebook UI and API must communicate
this limitation clearly.

## Implementation roadmap

1. **Phase 1: API and baseline tracing** — create the package, import-safe
   `run_viz` API, optional `%%pyviz` registration, structured trace events,
   source-line and basic variable snapshots, error reporting, and scoped
   `sys.settrace` handling with the default 500-step limit.
2. **Execution analysis** — deepen snapshots and diffs, identify collection
   mutation details and aliases, and add AST/source analysis.
3. **AST-derived learning cues** — add loop boundaries/iteration metadata,
   safe condition previews, and the four educational warning categories.
4. **Notebook visualization** — render self-contained HTML and implement
   timeline, change/iteration navigation, badges, warnings, diffs, and line
   highlighting.
5. **Validation and polish** — add pytest coverage for API, tracing, edge
   cases, safety messaging, rendering/escaping, and IPython integration; run
   the full test suite and document usage.

Do not begin implementation until this specification and roadmap have been
reviewed.
