"""Notebook-safe, CSS-only rendering for CodeJourney trace data."""

from __future__ import annotations

import html
import json
import math
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

from . import CollectionSnapshot, ObjectSnapshot, TraceEvent, TraceResult


def _json_value(value: Any) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else str(value)
    if type(value) is bytes:
        return {"type": "bytes", "hex": value.hex()}
    if type(value) in (list, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, ObjectSnapshot):
        return {"type": value.type_name}
    if isinstance(value, CollectionSnapshot):
        return {"type": value.type_name, "items": _json_value(value.items)}
    if is_dataclass(value):
        return _json_value(asdict(value))
    if type(value) is dict:
        return {str(key): _json_value(item) for key, item in value.items()}
    return {"type": type(value).__name__}


def _value_text(value: Any) -> str:
    return json.dumps(_json_value(value), ensure_ascii=True, indent=2)


def _is_object(value: Any) -> bool:
    return type(value) in (list, tuple, dict, set, frozenset) or isinstance(
        value, (CollectionSnapshot, ObjectSnapshot)
    )


def _variable_objects(event: TraceEvent, scope: str) -> tuple[str, str]:
    aliases = {alias.name: alias.linked_to for alias in event.aliases}

    def canonical_name(name: str) -> str:
        seen = set()
        while name in aliases and name not in seen:
            seen.add(name)
            name = aliases[name]
        return name

    object_ids = {}
    object_values = {}
    variable_rows = []
    for name, value in event.after.items():
        safe_name = html.escape(name)
        if _is_object(value):
            canonical = canonical_name(name)
            object_id = object_ids.get(canonical)
            if object_id is None:
                object_id = f"{scope}-object-{len(object_ids) + 1}"
                object_ids[canonical] = object_id
                object_values[canonical] = value
            pointer_label = object_id.rsplit("-object-", 1)[-1]
            alias_label = next(
                (alias.label for alias in event.aliases if alias.name == name),
                None,
            )
            variable_rows.append(
                '<div class="cj-variable">'
                f'<span class="cj-variable-name">{safe_name}</span>'
                f'<a class="cj-pointer" href="#{object_id}" aria-label="View object for {safe_name}">'
                f'&rarr; object {pointer_label}</a>'
                + (
                    f'<span class="cj-alias">{html.escape(alias_label)}</span>'
                    if alias_label is not None
                    else ""
                )
                + "</div>"
            )
        else:
            variable_rows.append(
                '<div class="cj-variable">'
                f'<span class="cj-variable-name">{safe_name}</span>'
                f'<code class="cj-scalar">= {html.escape(_value_text(value))}</code>'
                "</div>"
            )

    if not variable_rows:
        variables_html = '<p class="cj-empty">No variables in this state.</p>'
        objects_html = '<p class="cj-empty">No objects in this state.</p>'
        return variables_html, objects_html

    objects_html = []
    for canonical, value in object_values.items():
        object_id = object_ids[canonical]
        object_number = object_id.rsplit("-object-", 1)[-1]
        objects_html.append(
            f'<article class="cj-object" id="{object_id}">'
            f'<h4>Object {object_number}</h4>'
            f"<pre>{html.escape(_value_text(value))}</pre>"
            "</article>"
        )
    if not objects_html:
        objects_html.append('<p class="cj-empty">No objects in this state.</p>')
    return "\n".join(variable_rows), "\n".join(objects_html)


def _diffs_html(event: TraceEvent) -> str:
    if not event.variable_diffs:
        return '<p class="cj-empty">No variable changes at this step.</p>'
    cards = []
    for diff in event.variable_diffs:
        detail = (
            f"Before: {_value_text(diff.before)}\n"
            f"After:  {_value_text(diff.after)}"
        )
        if diff.list_indices:
            detail += "\nChanged list indices: " + ", ".join(
                str(index) for index in diff.list_indices
            )
        if diff.dictionary_keys:
            detail += "\nChanged dictionary keys: " + _value_text(
                diff.dictionary_keys
            )
        cards.append(
            '<article class="cj-diff">'
            f"<strong>{html.escape(diff.name)} · {html.escape(diff.change)}</strong>"
            f"<pre>{html.escape(detail)}</pre>"
            "</article>"
        )
    return "\n".join(cards)


 
def _view_html(
    result: TraceResult,
    event: TraceEvent,
    index: int,
    scope: str,
    show_error: bool,
) -> str:
    source_lines = result.source.splitlines()
    line_markup = "\n".join(
        f'<span class="cj-source-line{" cj-current" if number == event.line_number else ""}">'
        f'<span class="cj-line-number">{number:>3}</span> '
        f"{html.escape(line)}</span>"
        for number, line in enumerate(source_lines, start=1)
    )
    if not line_markup:
        line_markup = '<span class="cj-empty">No source lines.</span>'

    variables_html, objects_html = _variable_objects(event, f"{scope}-{index}")
    iteration_text = (
        event.loop_iterations[-1].label
        if event.loop_iterations
        else "No loop iteration selected"
    )
    boundary = next(
        (item for item in event.loop_boundaries if item.kind == "start"),
        None,
    )
    if boundary is not None:
        total = boundary.total_iterations if boundary.total_iterations is not None else "?"
        iteration_text = f"Iteration {boundary.iteration_index + 1} of {total} · iteration begins"

    aliases_text = "; ".join(alias.label for alias in event.aliases)
    if aliases_text:
        iteration_text += " · " + aliases_text

    condition_html = ""

    if event.condition_preview is not None:
        condition = event.condition_preview

        expression = html.escape(condition.expression)
        preview = html.escape(condition.preview)

        if condition.result is True:
            result_text = "✓ TRUE"
            result_class = "cj-condition-true"
        elif condition.result is False:
            result_text = "✕ FALSE"
            result_class = "cj-condition-false"
        else:
            result_text = "? UNKNOWN"
            result_class = "cj-condition-unknown"

        steps_html = ""
        if condition.evaluations:
            steps_html = (
                '<div class="cj-condition-steps" aria-label="Short-circuit evaluation steps">'
                '<div class="cj-condition-heading">SHORT-CIRCUIT STEPS</div>'
                + "".join(
                    '<div class="cj-condition-part cj-condition-part-'
                    + html.escape(step.status)
                    + '"><code>'
                    + html.escape(step.expression)
                    + '</code><strong>'
                    + html.escape(step.value)
                    + '</strong><span>Step '
                    + str(step_number)
                    + ': '
                    + html.escape(step.note)
                    + '</span></div>'
                    for step_number, step in enumerate(condition.evaluations, start=1)
                )
                + "</div>"
            )

        condition_html = (
            '<div class="cj-condition-card">'
            '<div class="cj-condition-heading">CONDITION</div>'
            f'<div class="cj-condition-expression">{expression}</div>'
            '<div class="cj-condition-heading">EVALUATION</div>'
            f'<div class="cj-condition-preview">{preview}</div>'
            + steps_html
            + f'<div class="cj-condition-result {result_class}">'
            + result_text
            + "</div></div>"
        )

    warning_html = "".join(
        f'<li class="cj-warning">{html.escape(warning.message)}'
        + (
            f' <span class="cj-muted">(line {warning.line_number})</span>'
            if warning.line_number is not None
            else ""
        )
        + "</li>"
        for warning in result.warnings
    )

    error_html = ""
    if result.error is not None and show_error:
        error_html = (
            '<li class="cj-error">'
            + html.escape(result.error.type_name)
            + ": "
            + html.escape(result.error.message)
            + "</li>"
        )

    if result.truncated:
        warning_html += (
            '<li class="cj-warning">Trace stopped after '
            + str(result.max_steps)
            + " steps. The displayed execution is partial.</li>"
        )

    return f"""<section class="cj-view" data-index="{index}">
  <div class="cj-state"><span class="cj-badge">{html.escape(iteration_text)}</span>{condition_html}</div>
  <div class="cj-layout">
    <section class="cj-panel"><h3>Source</h3><pre class="cj-source"><code>{line_markup}</code></pre></section>
    <section class="cj-panel">
      <h3>Variables</h3><div class="cj-variables">{variables_html}</div>
      <h3>Objects</h3><div class="cj-objects">{objects_html}</div>
      <h3>What changed?</h3><div class="cj-diffs">{_diffs_html(event)}</div>
      <h3>Learning notes</h3><ul>{warning_html}{error_html}</ul>
    </section>
  </div>
</section>"""



def render_html(result: TraceResult) -> str:
    """Render a self-contained, notebook-safe interactive HTML view.

    The timeline uses radio inputs and labels so it remains interactive in
    notebook renderers that intentionally disable JavaScript in HTML output.
    """
    scope = f"cj-{uuid.uuid4().hex}"
    events = tuple(
        event
        for event in result.events
        if event.line_number is not None and event.line_number > 0
    )
    initial_index = 0 if events else -1

    error_index = None
    if result.error is not None:
        exception_indices = [
            index
            for index, event in enumerate(events)
            if event.event == "exception"
        ]
        matching_errors = [
            index
            for index in exception_indices
            if events[index].exception_type == result.error.type_name
            and events[index].line_number == result.error.line_number
        ]
        matching_type = [
            index
            for index in exception_indices
            if events[index].exception_type == result.error.type_name
        ]
        if matching_errors:
            error_index = matching_errors[-1]
        elif matching_type:
            error_index = matching_type[-1]
        elif exception_indices:
            error_index = exception_indices[-1]

    controls = []
    timeline = []
    views = []
    selectors = []
    output_states = []
    count = len(events)
    for index, event in enumerate(events):
        selector_id = f"{scope}-step-{index}"
        selectors.append(
            f'<input class="cj-selector" type="radio" name="{scope}-steps" '
            f'id="{selector_id}"{ " checked" if index == initial_index else ""}>'
        )

        control_labels = []
        targets = {
            "prev": index - 1 if index > 0 else None,
            "next": index + 1 if index + 1 < count else None,
        }
        next_change = next(
            (
                candidate
                for candidate in range(index + 1, count)
                if events[candidate].variable_diffs
            ),
            None,
        )
        previous_iteration = next(
            (
                candidate
                for candidate in range(index - 1, -1, -1)
                if any(
                    boundary.kind == "start"
                    for boundary in events[candidate].loop_boundaries
                )
            ),
            None,
        )
        next_iteration = next(
            (
                candidate
                for candidate in range(index + 1, count)
                if any(
                    boundary.kind == "start"
                    for boundary in events[candidate].loop_boundaries
                )
            ),
            None,
        )
        targets.update(
            {
                "change": next_change,
                "prev-iteration": previous_iteration,
                "next-iteration": next_iteration,
            }
        )
        for action, label in (
            ("prev", "Prev"),
            ("next", "Next"),
            ("prev-iteration", "Prev Iteration"),
            ("next-iteration", "Next Iteration"),
            ("change", "Jump to Next Change"),
        ):
            target = targets[action]
            if target is None:
                control_labels.append(
                    f'<span class="cj-button cj-disabled" aria-disabled="true">{label}</span>'
                )
            else:
                control_labels.append(
                    f'<label class="cj-button" role="button" for="{scope}-step-{target}">'
                    f"{label}</label>"
                )
        controls.append(
            f'<div class="cj-controls" data-step-controls="{index}">'
            + "".join(control_labels)
            + f'<span class="cj-counter">'
            + ("END" if index == count - 1 else str(index + 1))
            + f' / {count}</span></div>'
        )
        tick_label = "END" if index == count - 1 else str(index + 1)
        timeline.append(
            f'<label class="cj-tick" role="button" for="{selector_id}" '
            f'aria-label="Go to {tick_label}" title="{tick_label}">'
            f"{tick_label}</label>"
        )
        output_content = (
            f"<pre>{html.escape(event.output)}</pre>"
            if event.output
            else '<p class="cj-output-empty">No output at this step.</p>'
        )
        output_states.append(
            f'<div class="cj-output-state" data-output-index="{index}">'
            f"{output_content}</div>"
        )
        views.append(
            _view_html(
                result,
                event,
                index,
                scope,
                error_index is not None and index >= error_index,
            )
        )

    rules = []
    for index in range(count):
        selector_id = f"{scope}-step-{index}"
        rules.append(
            f"#{selector_id}:checked ~ .cj-controls[data-step-controls='{index}']"
            "{display:flex}"
        )
        rules.append(
            f"#{selector_id}:checked ~ .cj-output-card .cj-output-state[data-output-index='{index}']"
            "{display:block}"
        )
        rules.append(
            f"#{selector_id}:checked ~ .cj-views .cj-view[data-index='{index}']"
            "{display:block}"
        )
        rules.append(
            f"#{selector_id}:checked ~ .cj-timeline label[for='{selector_id}']"
            "{background:#315fa8;color:#fff}"
        )

    if not events:
        selector_html = ""
        empty_state_html = '<p class="cj-empty">No execution steps captured.</p>'
        controls_html = ""
        timeline_html = ""
        views_html = ""
        output_states_html = '<p class="cj-output-empty">No output captured.</p>'
    else:
        selector_html = "".join(selectors)
        empty_state_html = ""
        controls_html = "".join(controls)
        output_states_html = "".join(output_states)
        timeline_html = (
            '<div class="cj-timeline" role="group" aria-label="Execution timeline">'
            + "".join(timeline)
            + "</div>"
        )
        views_html = '<div class="cj-views">' + "".join(views) + "</div>"
    output_card_html = (
        '<section class="cj-output-card" aria-label="Output">'
        "<h3>Output</h3>"
        + output_states_html
        + "</section>"
    )

    return f"""<div class="codejourney {scope}">
<style>
.codejourney {{ font: 14px/1.45 system-ui, sans-serif; color: #172033; background: #fff; border: 1px solid #d5dbe6; border-radius: 10px; padding: 14px; }}
.codejourney * {{ box-sizing: border-box; }}
.cj-selector {{ position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }}
.cj-output-card {{ margin: 0 0 12px; padding: 10px 12px; border: 1px solid #334155; border-radius: 8px; background: #172033; color: #f8fafc; color-scheme: dark; }}
.cj-output-card h3 {{ margin: 0 0 8px; color: #fff; font-size: 14px; }}
.cj-output-state {{ display: none; }}
.cj-output-card pre {{ max-height: 260px; overflow: auto; margin: 0; padding: 9px 10px; border-radius: 5px; background: #0b1220 !important; color: #f8fafc !important; white-space: pre-wrap; overflow-wrap: anywhere; }}
.cj-output-empty {{ margin: 0; color: #dbeafe; }}
.cj-controls {{ display: none; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 10px; }}
.cj-button {{ border: 1px solid #aeb8c8; background: #f7f9fc; border-radius: 6px; padding: 6px 10px; cursor: pointer; color: inherit; }}
.cj-button:hover {{ background: #e9eff8; }}
.cj-disabled {{ opacity: .5; cursor: default; }}
.cj-counter {{ margin-left: auto; color: #657187; font-size: 12px; }}
.cj-timeline {{ display: flex; gap: 4px; overflow-x: auto; padding: 5px 0 11px; }}
.cj-tick {{ flex: 0 0 auto; min-width: 24px; padding: 2px 6px; border-radius: 999px; background: #e8edf5; color: #34445c; text-align: center; cursor: pointer; font-size: 12px; }}
.cj-view {{ display: none; }}
.cj-layout {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, .8fr); gap: 12px; }}
.cj-panel {{ min-width: 0; border: 1px solid #e1e5ec; border-radius: 8px; padding: 10px; }}
.cj-panel h3 {{ font-size: 14px; margin: 0 0 8px; }}
.cj-panel h3:not(:first-child) {{ margin-top: 14px; }}
.codejourney .cj-source {{ overflow: auto; margin: 0; background: #ffffff !important; color: #172033 !important; color-scheme: light; border-radius: 6px; padding: 8px; white-space: pre; }}
.codejourney .cj-source code, .codejourney .cj-source-line {{ color: #172033 !important; }}
.codejourney .cj-source-line {{ display: block; min-height: 1.45em; background-color: #ffffff; }}
.codejourney .cj-source-line.cj-current {{ background: #fff0b3 !important; color: #172033 !important; outline: 1px solid #c49a18; }}
.codejourney .cj-line-number {{ user-select: none; color: #5e6b7b !important; }}
.cj-state {{ margin: 0 0 10px; }}
.cj-badge {{ display: inline-block; background: #e8efff; border-radius: 999px; padding: 3px 9px; font-size: 12px; }}

.cj-condition-card {{
    margin: 12px 0;
    padding: 16px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}}

.cj-condition-heading {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #64748b;
}}

.cj-condition-expression {{
    font-family: monospace;
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 8px;
}}

.cj-condition-preview {{
    font-family: monospace;
    font-size: 13px;
    color: #475569;
    background: #e2e8f0;
    padding: 9px 12px;
    border-radius: 6px;
}}

.cj-condition-result {{
    align-self: flex-start;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 12px;
}}

.cj-condition-true {{
    background: #dcfce7;
    color: #166534;
}}

.cj-condition-false {{
    background: #fee2e2;
    color: #991b1b;
}}

.cj-condition-unknown {{
    background: #e2e8f0;
    color: #475569;
}}

.codejourney .cj-condition-steps {{ display: flex; flex-direction: column; gap: 6px; color-scheme: light; }}
.codejourney .cj-condition-part {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 6px; border: 1px solid #cbd5e1 !important; background: #ffffff !important; color: #1e293b !important; color-scheme: light; box-shadow: none !important; }}
.codejourney .cj-condition-part code, .codejourney .cj-condition-part strong, .codejourney .cj-condition-part span {{ background: transparent !important; border: 0 !important; box-shadow: none !important; color: #1e293b !important; text-shadow: none !important; }}
.codejourney .cj-condition-part code {{ overflow-wrap: anywhere; }}
.codejourney .cj-condition-part strong {{ font-family: monospace; }}
.codejourney .cj-condition-part span {{ grid-column: 1 / -1; color: #475569 !important; font-size: 12px; }}
.codejourney .cj-condition-part-evaluated {{ background: #eff6ff !important; border-color: #60a5fa !important; border-left: 4px solid #2563eb !important; }}
.codejourney .cj-condition-part-skipped {{ background: #f1f5f9 !important; border-left: 4px solid #64748b !important; color: #334155 !important; }}
.codejourney .cj-condition-part-unknown {{ background: #fffbeb !important; border-left: 4px solid #d97706 !important; border-color: #fbbf24 !important; }}

.cj-variables {{ display: flex; flex-direction: column; gap: 7px; }}
.cj-variable {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 7px 9px; background: #edf4ff; border: 1px solid #cfddf4; border-radius: 6px; }}
.cj-variable-name {{ font-weight: 650; }}
.cj-pointer {{ color: #315fa8; font-weight: 700; text-decoration: none; }}
.cj-pointer:hover {{ text-decoration: underline; }}
.cj-alias {{ color: #657187; font-size: 12px; }}
.cj-scalar {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
.cj-object {{ border: 1px solid #bdc9da; border-radius: 7px; padding: 8px 10px; background: #fff; margin: 7px 0 0 18px; scroll-margin: 8px; }}
.cj-object h4 {{ font-size: 12px; color: #53647c; margin: 0 0 4px; }}
.cj-object pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
.cj-diff {{ border-left: 3px solid #6688c7; background: #f7f9fd; padding: 7px 9px; margin: 7px 0; border-radius: 4px; overflow-wrap: anywhere; }}
.cj-diff pre {{ margin: 4px 0 0; white-space: pre-wrap; }}
.cj-warning {{ color: #684800; background: #fff6d8; border-radius: 5px; padding: 6px 8px; margin: 5px 0; }}
.cj-error {{ color: #8d2020; background: #fde8e8; border-radius: 5px; padding: 6px 8px; margin: 5px 0; }}
.cj-muted, .cj-empty {{ color: #657187; font-size: 12px; }}
@media (max-width: 700px) {{ .cj-layout {{ grid-template-columns: 1fr; }} }}
{''.join(rules)}
</style>
{selector_html}
{output_card_html}
{empty_state_html}
{controls_html}
{timeline_html}
{views_html}
<p class="cj-muted">Educational trace, not a debugger. Code ran with this Python process's permissions; execution is not sandboxed.</p>
</div>"""
