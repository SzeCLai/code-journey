# CodeJourney manual test checklist

Check only behavior personally verified by the tester. Leave untested items unchecked.

## Verification record

- Tester: CHENG Nga Yuen
- Date: 2026-11-21
- Operating system: Windows 11 client accessing CityU JupyterHub
- Python version: 3.14.9
- Jupyter/IPython environment: CityU JupyterLab, Python 3 (ipykernel)
- CodeJourney version checked: 0.1.0
- Installation method: PyPI (`%pip install --upgrade codejourney`)

## Fresh installation

- [ ] Create and activate a fresh virtual environment.
- [ ] Install the repository in editable mode with `python -m pip install -e .`.
- [x] Install CodeJourney from PyPI with `%pip install --upgrade codejourney`.
- [x] Confirm the installed package version is `0.1.0`.

**Observed result / notes:** CodeJourney 0.1.0 installed successfully from PyPI in CityU JupyterLab using Python 3.14.9. The Jupyter kernel was restarted after installation.

## Import

- [x] Run `import codejourney` without an exception.
- [ ] Run `from codejourney import run_viz` and verify standalone `run_viz` behavior.
- [ ] Confirm an invalid `max_steps` value raises the documented validation error.

## `%%pyviz` registration and loop visualization

- [x] Import CodeJourney in an active IPython/Jupyter kernel and confirm `%%pyviz` is registered.
- [x] Run a loop cell with `%%pyviz` and confirm its visualization renders.

```python
%%pyviz
total = 0
for number in [1, 2, 3]:
    total += number
```

## Prev and Next

- [x] Use **Prev** and **Next** to move between captured execution steps.
- [x] Confirm the timeline selects steps and the step counter updates.
- [ ] Confirm **Prev** is unavailable at the first step and **Next** at the last step.

## Iteration navigation

- [x] Confirm **Next Iteration** advances to the following loop iteration.
- [x] Confirm **Prev Iteration** returns to the previous loop iteration.
- [ ] Confirm the iteration badge identifies loop execution context.
- [ ] Verify navigation behavior with nested loops.

**Observed result / notes:** The loop example produced nine captured steps and three identified iterations. **Next Iteration** moved from Iteration 1 of 3 to Iteration 2 of 3; **Prev Iteration** returned to the previous iteration.

## Jump to Next Change

- [x] Confirm **Jump to Next Change** advances to a step where a variable changed.
- [x] Confirm the before and after values are shown under **What changed?**.
- [ ] Confirm the button is unavailable when no later change remains.

**Observed result / notes:** Jumped to the step where `total` changed from `0` to `1`; both values were displayed.

## Source highlighting

- [x] Confirm source-line highlighting follows the selected execution state.
- [ ] Confirm source containing HTML-like text is escaped and displayed safely.

## Variables and objects

- [x] Confirm scalar variables appear in **Variables**.
- [x] Confirm a list appears in the object display.
- [x] Confirm the changed list index is reported as index `2`.
- [ ] Confirm added, removed, and modified variables are all reported.
- [ ] Confirm dictionary-key changes are reported.
- [ ] Confirm unsupported custom objects are represented without calling custom `repr`.

## Alias visualization

```python
numbers = [1, 2]
alias = numbers
numbers.append(3)
```

- [x] Confirm alias detection links `alias` to `numbers`.
- [x] Confirm the list mutation displays the value changing from `[1, 2]` to `[1, 2, 3]`.
- [x] Confirm the changed list index is shown as `2`.
- [ ] Confirm equal but independent lists are not presented as aliases.

**Observed result / notes:** The shared list was detected between `numbers` and `alias`. Appending through `alias` changed the list from `[1, 2]` to `[1, 2, 3]`, with changed index `2` reported.

## Learning notes

- [ ] Verify the dedicated list-mutation-during-iteration warning example.
- [ ] Verify the first-iteration `break` warning example.
- [ ] Verify the first-iteration `return` warning example.
- [ ] Verify the built-in-name-shadowing warning example.
- [ ] Confirm warnings are educational prompts, not definitive diagnoses.
- [ ] Verify condition previews and unavailable condition values.

## Common runtime errors

- [ ] Verify a syntax error is displayed.
- [ ] Verify a `TypeError` is displayed.
- [ ] Verify an explicit `ValueError` is displayed.
- [ ] Verify the step-limit behavior.
- [x] Verify `IndexError` is displayed for access to `values[3]`.
- [x] Confirm earlier trace states remain accessible after the `IndexError`.

```python
values = [10, 20]
print(values[3])
```

**Observed result / notes:** The `IndexError` for `values[3]` was displayed, and earlier states remained accessible after the error.

## Security behavior

- [x] Confirm the rendered interface displays the warning that execution is not sandboxed.

## Final sign-off

- [x] I reviewed all applicable checklist items.
- [ ] I recorded any failures or unresolved behavior.

Tester signature / status: CHENG Nga Yuen — verified listed items; remaining unchecked items were not tested.
