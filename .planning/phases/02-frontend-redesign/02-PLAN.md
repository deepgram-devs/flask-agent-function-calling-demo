---
wave: 1
stream: B
depends_on: []
files_modified:
  - templates/index.html
  - static/style.css
autonomous: true
requirements:
  - R-02-A
  - R-02-B
  - R-02-C
  - R-02-D
  - R-02-E
  - R-02-F
  - R-02-G
  - R-02-H
  - R-02-I
  - R-02-J
  - R-03-A
  - R-03-B
  - R-03-C
  - R-03-D
---

# Phase 2: Frontend Redesign (Deepgram Design System)

## Goal
Rewrite `templates/index.html` using Deepgram's design system. Implement 3-panel layout, demo selector grid with selectable cards, builder form, and all Deepgram UI components. Replace `static/style.css` with minimal overrides only.

## must_haves
- Deepgram CDN CSS loaded, Font Awesome loaded
- Dark mode forced via `:root { color-scheme: dark; }`
- 3-panel `dg-columns` layout renders
- Demo selector shows `dg-card--selectable` grid (populated from `GET /configs` via JS)
- Start/stop button uses `dg-btn--primary` with mic icon
- `dg-status` component shows connection state
- Builder form opens in slide-in panel, POSTs to `/configs`, adds card to grid without reload
- Edit existing config pre-populates builder form
- All existing SocketIO JS logic preserved (audio, messages, logs)

## Tasks

<task id="2.1">
**Replace CSS: minimal overrides only**

Replace contents of `static/style.css` with minimal project-specific overrides on top of the Deepgram design system:

```css
/* Flask Voice Agent Demo — local overrides */
/* Deepgram design system loaded via CDN in index.html */

:root {
  color-scheme: dark;
}

/* Conversation transcript area */
.conversation-log {
  height: 100%;
  overflow-y: auto;
  padding: var(--dg-space-4, 1rem);
}

/* Per-message styling */
.message-agent {
  color: var(--dg-color-brand-green, #13ef95);
}
.message-user {
  color: var(--dg-color-text-primary, #fff);
}

/* Raw event log panel */
.event-log {
  font-family: monospace;
  font-size: 0.75rem;
  height: 100%;
  overflow-y: auto;
  padding: var(--dg-space-3, 0.75rem);
  color: var(--dg-color-text-muted, #888);
}

/* Builder slide-in panel */
.builder-panel {
  position: fixed;
  top: 0;
  right: -480px;
  width: 480px;
  height: 100vh;
  background: var(--dg-color-surface-2, #1a1a1e);
  border-left: 1px solid var(--dg-color-border, #2a2a30);
  transition: right 0.3s ease;
  overflow-y: auto;
  z-index: 100;
  padding: var(--dg-space-6, 1.5rem);
}
.builder-panel.open {
  right: 0;
}
.builder-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 99;
}
.builder-overlay.open {
  display: block;
}
```
</task>

<task id="2.2">
**Rewrite `templates/index.html` — head and CDN links**

Rewrite the `<head>` section:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Deepgram Voice Agent Demo</title>

  <!-- Deepgram Design System -->
  <link rel="stylesheet" href="https://unpkg.com/@deepgram/styles/dist/deepgram.css">
  <!-- Font Awesome -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
  <!-- Local overrides -->
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">

  <style>
    :root { color-scheme: dark; }
  </style>
</head>
```
</task>

<task id="2.3">
**Rewrite `templates/index.html` — 3-panel layout structure**

Replace the body with the `dg-columns` shell:

```html
<body>
  <div class="dg-columns" style="height: 100vh; overflow: hidden;">

    <!-- LEFT PANEL: Demo selector + controls -->
    <aside class="dg-columns__aside" style="overflow-y: auto; border-right: 1px solid var(--dg-color-border);">
      <div style="padding: 1rem;">
        <div class="dg-page-heading">
          <h1 class="dg-page-heading__title">Voice Agent Demo</h1>
          <p class="dg-page-heading__subtitle">Select a demo to begin</p>
        </div>

        <!-- Demo selector grid -->
        <div id="demo-selector" style="display: grid; grid-template-columns: 1fr; gap: 0.75rem; margin-top: 1rem;">
          <!-- Cards injected by JS from GET /configs -->
          <div class="dg-spinner" id="configs-loading"></div>
        </div>

        <!-- New Demo button -->
        <button class="dg-btn dg-btn--secondary" style="width: 100%; margin-top: 1rem;" id="new-demo-btn">
          <i class="fa fa-plus"></i> New Demo
        </button>

        <hr style="border-color: var(--dg-color-border); margin: 1.5rem 0;">

        <!-- Voice / Language selects -->
        <div class="dg-form-field">
          <label class="dg-form-field__label">Language</label>
          <select class="dg-select" id="language-select">
            <option value="en-US">English (US)</option>
            <option value="en-PH">English (Philippines)</option>
            <option value="tl">Tagalog</option>
            <option value="ar">Arabic</option>
          </select>
        </div>

        <div class="dg-form-field" style="margin-top: 0.75rem;">
          <label class="dg-form-field__label">Voice Model</label>
          <select class="dg-select" id="voice-model-select">
            <!-- Populated from /tts-models -->
          </select>
        </div>

        <hr style="border-color: var(--dg-color-border); margin: 1.5rem 0;">

        <!-- Start/Stop button -->
        <div style="text-align: center;">
          <div class="dg-status" id="status-indicator" data-status="idle">Ready</div>
          <button class="dg-btn dg-btn--primary" id="start-btn" style="margin-top: 1rem; width: 100%; font-size: 1.1rem; padding: 0.875rem;">
            <i class="fa fa-microphone"></i> Start Session
          </button>
        </div>
      </div>
    </aside>

    <!-- CENTER PANEL: Conversation transcript -->
    <main class="dg-columns__main" style="overflow: hidden; display: flex; flex-direction: column;">
      <div style="padding: 1rem 1rem 0; border-bottom: 1px solid var(--dg-color-border);">
        <h2 style="margin: 0; font-size: 1rem; font-weight: 600;" id="active-demo-name">No demo selected</h2>
      </div>
      <div class="conversation-log" id="conversation-log" style="flex: 1;">
        <div class="dg-alert dg-alert--info" id="welcome-message">
          Select a demo from the left panel and press Start Session.
        </div>
      </div>
    </main>

    <!-- RIGHT PANEL: Event log / debug -->
    <aside class="dg-columns__aside dg-columns__aside--right" style="overflow: hidden; border-left: 1px solid var(--dg-color-border); display: flex; flex-direction: column;">
      <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--dg-color-border); font-weight: 600; font-size: 0.85rem;">
        Event Log
      </div>
      <div class="event-log" id="event-log"></div>
    </aside>

  </div>

  <!-- Builder slide-in panel -->
  <div class="builder-overlay" id="builder-overlay"></div>
  <div class="builder-panel" id="builder-panel">
    <!-- Builder form injected in task 2.4 -->
  </div>
```
</task>

<task id="2.4">
**Rewrite `templates/index.html` — builder form**

Inside `#builder-panel`:

```html
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
  <h2 style="margin: 0; font-size: 1.1rem; font-weight: 700;" id="builder-title">New Demo</h2>
  <button class="dg-btn dg-btn--ghost dg-btn--sm" id="builder-close">
    <i class="fa fa-times"></i>
  </button>
</div>

<form id="builder-form">
  <input type="hidden" id="builder-id" name="id">

  <div class="dg-form-field">
    <label class="dg-form-field__label">Demo Name *</label>
    <input class="dg-input" type="text" id="builder-name" name="name" required placeholder="e.g. Acme Support Bot">
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Company</label>
    <input class="dg-input" type="text" id="builder-company" name="company" placeholder="e.g. Acme Corp">
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Personality</label>
    <textarea class="dg-textarea" id="builder-personality" name="personality" rows="2" placeholder="Brief personality description"></textarea>
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">System Prompt *</label>
    <textarea class="dg-textarea" id="builder-system-prompt" name="systemPrompt" rows="6" required placeholder="You are a helpful agent for..."></textarea>
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Greeting</label>
    <input class="dg-input" type="text" id="builder-greeting" name="greeting" placeholder="Hello, how can I help you today?">
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Language</label>
    <select class="dg-select" id="builder-language" name="language">
      <option value="en-US">English (US)</option>
      <option value="en-PH">English (Philippines)</option>
      <option value="tl">Tagalog</option>
      <option value="ar">Arabic</option>
    </select>
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Voice Model</label>
    <select class="dg-select" id="builder-voice-model" name="voiceModel">
      <!-- Populated from /tts-models -->
    </select>
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Hotword (optional)</label>
    <input class="dg-input" type="text" id="builder-hotword" name="hotword" placeholder="e.g. Hey Saga">
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label">Mode</label>
    <select class="dg-select" id="builder-mode" name="mode">
      <option value="voice_agent">Voice Agent</option>
      <option value="agent_assist">Agent Assist</option>
    </select>
  </div>

  <div class="dg-form-field">
    <label class="dg-form-field__label" style="margin-bottom: 0.5rem;">Functions</label>
    <div id="builder-functions" style="display: flex; flex-direction: column; gap: 0.5rem;">
      <!-- Toggles injected by JS from FUNCTION_DEFINITIONS -->
    </div>
  </div>

  <div style="margin-top: 1.5rem; display: flex; gap: 0.75rem;">
    <button type="submit" class="dg-btn dg-btn--primary" style="flex: 1;">
      <i class="fa fa-save"></i> Save Demo
    </button>
    <button type="button" class="dg-btn dg-btn--ghost" id="builder-cancel">Cancel</button>
  </div>
</form>
```
</task>

<task id="2.5">
**Rewrite `templates/index.html` — JavaScript**

Preserve all existing SocketIO audio/connection logic verbatim. Add or replace only UI-layer JS:

```javascript
// ── Config loader ────────────────────────────────────────
async function loadConfigs() {
  const res = await fetch('/configs');
  const configs = await res.json();
  renderConfigCards(configs);
}

function renderConfigCards(configs) {
  const container = document.getElementById('demo-selector');
  container.innerHTML = '';
  if (configs.length === 0) {
    container.innerHTML = '<p style="color: var(--dg-color-text-muted); font-size: 0.85rem;">No demos yet. Click New Demo to create one.</p>';
    return;
  }
  configs.forEach(cfg => {
    const card = document.createElement('div');
    card.className = 'dg-card dg-card--selectable';
    card.dataset.configId = cfg.id;
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <div style="font-weight: 600;">${cfg.name}</div>
          <div style="font-size: 0.8rem; color: var(--dg-color-text-muted);">${cfg.company || ''} · ${cfg.language || ''}</div>
        </div>
        <button class="dg-btn dg-btn--ghost dg-btn--xs edit-config-btn" data-config-id="${cfg.id}" title="Edit">
          <i class="fa fa-edit"></i>
        </button>
      </div>
    `;
    card.addEventListener('click', (e) => {
      if (e.target.closest('.edit-config-btn')) return;
      selectConfig(cfg);
    });
    card.querySelector('.edit-config-btn').addEventListener('click', () => openBuilder(cfg));
    container.appendChild(card);
  });
}

let selectedConfig = null;

function selectConfig(cfg) {
  selectedConfig = cfg;
  document.querySelectorAll('#demo-selector .dg-card--selectable').forEach(c => c.classList.remove('dg-card--selected'));
  const card = document.querySelector(`[data-config-id="${cfg.id}"]`);
  if (card) card.classList.add('dg-card--selected');
  document.getElementById('active-demo-name').textContent = cfg.name;
  // Sync language/voice selects
  if (cfg.language) document.getElementById('language-select').value = cfg.language;
  if (cfg.voiceModel) document.getElementById('voice-model-select').value = cfg.voiceModel;
}

// ── Builder panel ─────────────────────────────────────────
function openBuilder(existingConfig = null) {
  const panel = document.getElementById('builder-panel');
  const overlay = document.getElementById('builder-overlay');
  const title = document.getElementById('builder-title');
  const form = document.getElementById('builder-form');
  form.reset();
  if (existingConfig) {
    title.textContent = 'Edit Demo';
    document.getElementById('builder-id').value = existingConfig.id;
    document.getElementById('builder-name').value = existingConfig.name || '';
    document.getElementById('builder-company').value = existingConfig.company || '';
    document.getElementById('builder-personality').value = existingConfig.personality || '';
    document.getElementById('builder-system-prompt').value = existingConfig.systemPrompt || '';
    document.getElementById('builder-greeting').value = existingConfig.greeting || '';
    document.getElementById('builder-language').value = existingConfig.language || 'en-US';
    document.getElementById('builder-voice-model').value = existingConfig.voiceModel || '';
    document.getElementById('builder-hotword').value = existingConfig.hotword || '';
    document.getElementById('builder-mode').value = existingConfig.mode || 'voice_agent';
  } else {
    title.textContent = 'New Demo';
    document.getElementById('builder-id').value = '';
  }
  panel.classList.add('open');
  overlay.classList.add('open');
}

function closeBuilder() {
  document.getElementById('builder-panel').classList.remove('open');
  document.getElementById('builder-overlay').classList.remove('open');
}

document.getElementById('new-demo-btn').addEventListener('click', () => openBuilder());
document.getElementById('builder-close').addEventListener('click', closeBuilder);
document.getElementById('builder-cancel').addEventListener('click', closeBuilder);
document.getElementById('builder-overlay').addEventListener('click', closeBuilder);

document.getElementById('builder-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form));
  // Generate id from name if new
  if (!data.id) {
    data.id = data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }
  const res = await fetch('/configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (res.ok) {
    closeBuilder();
    await loadConfigs(); // Refresh selector grid
  } else {
    alert('Failed to save demo config.');
  }
});

// ── Status updates ────────────────────────────────────────
function setStatus(status, label) {
  const el = document.getElementById('status-indicator');
  el.dataset.status = status;
  el.textContent = label;
}

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadConfigs();
  // loadVoiceModels() -- existing function or new fetch to /tts-models
});
```

Wrap all existing SocketIO audio JS inside `DOMContentLoaded` or preserve its existing placement. Do NOT remove or modify any socket event handlers.
</task>

## Verification Criteria
- Page loads without JS errors in browser console
- `GET /configs` results render as `dg-card--selectable` cards
- Clicking a card highlights it and updates `#active-demo-name`
- "New Demo" opens builder panel; form submits and new card appears without page reload
- "Edit" button pre-populates builder form with config data
- Start button visible with mic icon
- `dg-status` element present in DOM
- Dark mode active (background is dark `#0b0b0c`)
- All existing SocketIO functionality still works (audio connect/disconnect)
