# CodeJourney manual test checklist

Use this checklist for personal verification in a fresh environment. Mark a
check only after you observe the expected behavior. Do not copy "passed",
"complete", or similar status from repository automation.

## Verification record

- Tester:
- Date:
- Operating system:
- Python version:
- Jupyter/IPython environment:
- CodeJourney version checked:
- Installation method:

## Fresh installation

- [ ] Create and activate a fresh virtual environment.
- [ ] Install the repository development package:
  `python -m pip install -e .`
- [ ] Confirm that the package metadata or development install reports the
  intended version.
- [ ] Start Jupyter/IPython from the environment.
- [ ] **Pending publication:** do not mark the PyPI installation check until a
  PyPI release is confirmed and the package can be installed successfully.

**Observed result / notes:**

## Import

- [ ] Run `import codejourney` without IPython-specific registration errors.
- [ ] Run `from codejourney import run_viz`.
- [ ] Confirm `run_viz("answer = 40\nanswer += 2")` returns a trace object.
- [ ] Confirm an invalid `max_steps` value raises the documented validation
  error.

**Observed result / notes:**

## `%%pyviz` registration

- [ ] Import `codejourney` in an active IPython/Jupyter kernel.
- [ ] Confirm `%%pyviz` is accepted as a cell magic.
- [ ] Run:

  ```python
  %%pyviz
  total = 0
  for number in [1, 2, 3]:
      total += number
  ```

- [ ] Confirm the visualization renders and shows the final `total` state.

**Observed result / notes:**

## Prev and Next

Use a source cell with at least four executed steps.

- [ ] Confirm the first step disables or shows **Prev** as unavailable.
- [ ] Click or select **Next** and confirm the source highlight and variables
  change to the next state.
- [ ] Confirm **Prev** returns to the previous state.
- [ ] Confirm the last step disables or shows **Next** as unavailable.
- [ ] Confirm the timeline tick selects the corresponding step.
- [ ] Confirm the step counter stays synchronized.

**Observed result / notes:**

## Iteration navigation

Use a loop with at least two iterations.

- [ ] Confirm the iteration badge identifies loop execution context.
- [ ] Confirm **Next Iteration** moves to the next loop-start boundary.
- [ ] Confirm **Prev Iteration** moves to the previous loop-start boundary.
- [ ] Confirm the controls are unavailable when no previous or next iteration
  exists.
- [ ] Repeat for a nested loop and verify that more than one loop context does
  not make navigation misleading.

**Observed result / notes:**

## Jump to Next Change

- [ ] Start before a variable assignment or collection mutation.
- [ ] Confirm **Jump to Next Change** selects the next step with a variable
  diff.
- [ ] Confirm the selected step includes an added, removed, or modified
  variable.
- [ ] Confirm the button is unavailable when no later change remains.
- [ ] Confirm direct timeline navigation does not unexpectedly skip steps.

**Observed result / notes:**

## Source highlighting

- [ ] Confirm exactly one source line is highlighted for the selected step.
- [ ] Step through assignments and loop lines.
- [ ] Confirm the highlighted line moves to the runtime-error line when one
  occurs.
- [ ] Confirm source text containing HTML-like characters is displayed safely
  and does not execute.

**Observed result / notes:**

## Variables and objects

- [ ] Confirm scalar variables appear in **Variables**.
- [ ] Confirm list, tuple, or dictionary values appear as objects or
  collections and can be inspected.
- [ ] Confirm **What changed?** identifies added, removed, and modified
  variables.
- [ ] Confirm list-index changes or dictionary-key changes are shown when the
  implementation detects them.
- [ ] Confirm unsupported objects are represented safely rather than by calling
  a custom `repr`.

**Observed result / notes:**

## Alias visualization

Run:

```python
first = [1, 2]
second = first
second.append(3)
```

- [ ] Confirm `second` is linked or labeled as shared with `first`.
- [ ] Confirm the variable link opens or scrolls to the shared object display.
- [ ] Run a separate case with equal but independent lists:

  ```python
  first = [1]
  second = [1]
  ```

- [ ] Confirm independent equal lists are not presented as aliases.

**Observed result / notes:**

## Learning notes

Test one supported warning at a time:

- [ ] List mutation during iteration:

  ```python
  items = [1]
  for item in items:
      items.append(item)
  ```

- [ ] `break` in the first loop iteration.
- [ ] `return` in the first loop iteration, inside a function.
- [ ] Assignment or definition that shadows a built-in name.
- [ ] Confirm each warning is presented as an educational prompt and does not
  claim that a defect is proven.
- [ ] Confirm condition previews show source expressions and captured results
  where available.
- [ ] Confirm unavailable condition values are labeled rather than invented.

**Observed result / notes:**

## Common runtime errors

Test and record at least these cases:

- [ ] Syntax error:

  ```python
  if True
      pass
  ```

- [ ] Type error:

  ```python
  s = "hello"
  t = "world"
  print(s - t)
  ```

- [ ] Raised exception:

  ```python
  raise ValueError("bad input")
  ```

- [ ] Step limit:

  ```python
  count = 0
  while True:
      count += 1
  ```

  Run with `max_steps=5` or a small positive limit.

For every case, confirm:

- [ ] The error or truncation is shown in **Learning notes**.
- [ ] Available partial trace steps remain inspectable.
- [ ] Syntax/runtime errors are not presented as successful completion.
- [ ] The step limit is described as a trace limit, not a timeout or security
  boundary.

**Observed result / notes:**

## Security behavior

- [ ] Confirm the rendered UI communicates that code execution is not
  sandboxed.
- [ ] Confirm use is limited to trusted code during testing.

**Observed result / notes:**

## Final sign-off

- [ ] I personally reviewed all applicable items above.
- [ ] I recorded failures or unresolved behavior.
- [ ] I did not mark an item passed based only on repository automation.

Tester signature / status:
