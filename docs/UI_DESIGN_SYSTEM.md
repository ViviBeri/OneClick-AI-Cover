# Studio UI design system

## Product direction

OneClick AI Cover is a local-first audio creation tool. The interface should feel like a focused audio workstation: calm, precise, dark, and approachable for first-time users. Keep the primary task obvious and keep advanced processing controls available without overwhelming the main workflow.

## Visual tokens

| Token | Value | Use |
|---|---|---|
| Background | `#080D18` | Main application canvas |
| Panel | `#111A2B` | Cards, tabs, and grouped controls |
| Raised panel | `#172338` | Elevated surfaces |
| Primary accent | `#8B7CFF` | Main actions and active navigation |
| Accent highlight | `#A99CFF` | Kicker and focus details |
| Main text | `#EDF2FF` | Headings and important labels |
| Muted text | `#9AA9C2` | Supporting copy |
| Border | `rgba(148, 163, 184, 0.16)` | Quiet separation |

## Layout rules

- Keep the content column capped at 1180px and centered.
- Use a clear hero, four-step workflow summary, then the task navigation.
- Keep Generate Cover the main workflow; put training, model discovery, and diagnostics in secondary tabs.
- On narrow screens, stack form rows, retain horizontal tab scrolling, and keep touch targets at least 44px high.
- Avoid horizontal page overflow at a 390px viewport.

## Interaction rules

- Every primary action must have a clear label and visible result or error.
- Keep advanced Demucs controls collapsed by default.
- Explain local processing and model trust risks before users import or run voice checkpoints.
- Respect reduced-motion preferences and maintain readable contrast.
- Do not imply cloud processing, remote access, or Android-side inference where those capabilities are not implemented.

## Validation

The browser smoke test must verify the hero, all four workflow steps, model import, model refresh, and the primary Generate Cover action at a 390px viewport. Visual review is still required on a real Android browser before calling the UI production-ready.
