# Accessibility & responsive — frontend

## Accessibility baseline

For every in-scope interactive surface:

- [ ] Focus order is logical; primary actions reachable by keyboard
- [ ] Buttons/links have accessible names (visible text or `aria-label`)
- [ ] Form inputs have associated labels
- [ ] Errors are announced/associated with fields where practical
- [ ] Do not rely on color alone for status (review/spend/error)
- [ ] Modals/dialogs trap focus and restore focus on close (when used)
- [ ] Images/icons that convey meaning have text alternatives; decorative icons are hidden from AT

Operator tools are **not** exempt from basic a11y.

## Responsive baseline

- [ ] Primary flows usable at ~320–400px width and desktop
- [ ] No horizontal scroll for core forms/tables without a deliberate overflow pattern (e.g. table scroll container)
- [ ] Touch targets adequately sized for primary actions on small screens
- [ ] Navigation/workspace switcher does not obscure critical Review Gate actions

## Performance (frontend)

- Prefer pagination / virtualization for long lists when API supports paging
- Avoid refetch-on-every-keypress without debounce for search
- Do not load the entire audit history into memory if the API is paginated
- Measure only what’s needed; note known costs in the skill output

## Evidence

Paste what you verified (keyboard pass, viewport checks). If material a11y bugs remain in scope → **FAILED** or fix before VERIFIED.
