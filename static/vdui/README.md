# vdui

Assets copied from Deepgram's brand UI kit, [`deepgram-devs/dg-brand-ui`](https://github.com/deepgram-devs/dg-brand-ui) **v0.6.0** (`assets/`). This app has no npm step, so they're committed here.

| File | From the kit | Used for |
| --- | --- | --- |
| `brand.css` | `assets/brand.css` | Tokens, fonts (Work Sans, Azeret Mono), and utilities (`label`, `card`, `glass`, `stage-glow`) |
| `textures/stage.webp` | `assets/textures/stage.webp` | The `stage-glow` background behind the sidebar |
| `logos/deepgram.svg`, `logos/deepgram-favicon.svg` | `assets/logos/` | Logo and favicon |
| `ring-element/deepgram-voice-ring.js` | `assets/ring-element/` | The `<deepgram-voice-ring>` Web Component |

Don't edit these files. To upgrade, recopy them from the kit's `assets/` at the new tag (or run `npx vdui-assets <dir>` from a project that has the kit installed) and update the version above. `brand.css` also references `textures/landing.webp`; this page doesn't use `landing-texture`, so it isn't copied.
