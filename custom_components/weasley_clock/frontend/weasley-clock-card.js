/*
 * Weasley Clock card for Home Assistant.
 * Served automatically by the weasley_clock integration.
 *
 *   type: custom:weasley-clock-card
 *   clock: Family Clock      # optional: clock name or id (defaults to the first clock)
 *   title: Our House         # optional: override centre text
 *   show_legend: true        # optional: list people + positions under the clock
 *   flip_labels: true        # optional: keep bottom labels upright (false = authentic)
 *   wood: true               # optional: wooden box background
 *   title_font: UnifrakturMaguntia  # optional: font for the centre text
 *   hand_color: "#141414"    # optional: colour of the scissor-blade hands
 *   person_colors: false     # optional: true = use each person's colour from the integration
 */

const CARD_VERSION = "0.1.0";
const FONT_HREF =
  "https://fonts.googleapis.com/css2?family=Pirata+One&family=Cinzel:wght@700&family=UnifrakturMaguntia&family=IM+Fell+English:ital@0;1&display=swap";

const R_BEZEL = 196;
const R_FACE = 178;
const R_INNER_RING = 104;
const R_INNER_FACE = 92;
const R_LABEL = 150;
const R_HAND = 134; // hands stop short of the labels so they stay readable

const INITIAL_FONT = `"Cinzel", "Trajan Pro", "Times New Roman", serif`;
let fontsReady;

// Load the web fonts once; resolves when the faces we measure with are ready.
function ensureFonts() {
  if (fontsReady) return fontsReady;
  fontsReady = new Promise((resolve) => {
    const done = () =>
      Promise.all([
        document.fonts.load(`700 20px "Cinzel"`),
        document.fonts.load(`20px "Pirata One"`),
      ]).finally(resolve);
    let link = document.getElementById("weasley-clock-fonts");
    if (!link) {
      link = document.createElement("link");
      link.id = "weasley-clock-fonts";
      link.rel = "stylesheet";
      link.href = FONT_HREF;
      link.addEventListener("load", done, { once: true });
      link.addEventListener("error", () => resolve(), { once: true });
      document.head.appendChild(link);
    } else if (link.sheet) {
      done();
    } else {
      link.addEventListener("load", done, { once: true });
    }
    setTimeout(resolve, 8000); // never wait forever (offline etc.)
  });
  return fontsReady;
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function textColorFor(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return "#fff";
  const n = parseInt(m[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#1b1b1b" : "#fdf8e8";
}

function splitLabel(name) {
  const words = String(name).split(/\s+/).filter(Boolean);
  if (name.length <= 9 || words.length < 2) return [name];
  let best = [name];
  let bestDiff = Infinity;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(" ");
    const b = words.slice(i).join(" ");
    const diff = Math.abs(a.length - b.length);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = [a, b];
    }
  }
  return best;
}

class WeasleyClockCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._angles = {};
    this._layoutKey = null;
  }

  static getStubConfig() {
    return {};
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "clock", selector: { text: {} } },
        { name: "title", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "show_legend", selector: { boolean: {} } },
            { name: "flip_labels", selector: { boolean: {} } },
            { name: "wood", selector: { boolean: {} } },
          ],
        },
      ],
      computeLabel: (s) =>
        ({
          clock: "Clock name (blank = first clock)",
          title: "Centre text (blank = from integration)",
          show_legend: "Show legend",
          flip_labels: "Keep bottom labels upright",
          wood: "Wooden case",
        })[s.name],
    };
  }

  setConfig(config) {
    this._config = { show_legend: true, flip_labels: true, wood: true, ...(config || {}) };
    this._layoutKey = null;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return this._config?.show_legend ? 8 : 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  // ---------------------------------------------------------------- data
  _people() {
    const states = this._hass.states;
    let list;
    if (Array.isArray(this._config.entities) && this._config.entities.length) {
      list = this._config.entities.map((e) => states[typeof e === "string" ? e : e.entity]).filter(Boolean);
    } else {
      list = Object.values(states).filter((s) => s.attributes && s.attributes.weasley_clock === true);
      const want = this._config.clock;
      let clockId;
      if (want) {
        const match = list.find(
          (s) =>
            s.attributes.clock_id === want ||
            String(s.attributes.clock_name || "").toLowerCase() === String(want).toLowerCase()
        );
        clockId = match?.attributes.clock_id;
      } else {
        clockId = list[0]?.attributes.clock_id;
      }
      list = list.filter((s) => s.attributes.clock_id === clockId);
    }
    return list.sort((a, b) => (a.attributes.person_order ?? 0) - (b.attributes.person_order ?? 0));
  }

  // -------------------------------------------------------------- render
  _update() {
    if (!this._config || !this._hass) return;
    const people = this._people();
    if (!people.length) {
      this._renderEmpty();
      return;
    }
    const a0 = people[0].attributes;
    const locations = a0.locations || [];
    const title = this._config.title || a0.clock_title || a0.clock_name || "";
    const key = JSON.stringify([
      locations,
      title,
      this._config,
      people.map((p) => [p.entity_id, p.attributes.person_name, p.attributes.color]),
    ]);
    if (key !== this._layoutKey) {
      this._layoutKey = key;
      this._render(locations, title, people);
    }
    this._placeHands(locations, people);
  }

  _renderEmpty() {
    this._layoutKey = null;
    this.shadowRoot.innerHTML = `
      <ha-card><div style="padding:16px">
        No Weasley Clock found. Add the <b>Weasley Clock</b> integration and give it some people.
      </div></ha-card>`;
  }

  _render(locations, title, people) {
    ensureFonts();
    const n = Math.max(locations.length, 1);
    const seg = 360 / n;
    const cfg = this._config;

    const dividers = locations
      .map((_, i) => {
        const a = (((i - 0.5) * seg - 90) * Math.PI) / 180;
        const x1 = Math.cos(a) * R_INNER_RING, y1 = Math.sin(a) * R_INNER_RING;
        const x2 = Math.cos(a) * R_FACE, y2 = Math.sin(a) * R_FACE;
        return `<line x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"/>`;
      })
      .join("");

    const arc = (2 * Math.PI * R_LABEL) / n;
    const labels = locations
      .map((name, i) => {
        const c = i * seg;
        const flip = cfg.flip_labels && c > 90 && c < 270;
        const lines = splitLabel(name);
        const longest = Math.max(...lines.map((l) => l.length));
        const size = Math.max(7, Math.min(lines.length > 1 ? 13.5 : 17, (arc * 0.86) / (longest * 0.5), 28 / lines.length));
        const gap = size * 0.95;
        const tspans = lines
          .map((l, j) => `<tspan x="0" y="${((j - (lines.length - 1) / 2) * gap).toFixed(2)}">${esc(l)}</tspan>`)
          .join("");
        return `<text class="label" font-size="${size.toFixed(2)}"
          transform="rotate(${c.toFixed(3)}) translate(0 ${-R_LABEL})${flip ? " rotate(180)" : ""}">${tspans}</text>`;
      })
      .join("");

    const titleLines = splitLabel(title);
    const tSize = Math.min(30, (R_INNER_FACE * 1.5) / Math.max(4, ...titleLines.map((l) => l.length)) / 0.5);
    const titleSvg = titleLines
      .map(
        (l, j) =>
          `<text class="title" font-size="${tSize.toFixed(1)}" x="0" y="${(
            (titleLines.length > 1 ? (j === 0 ? -1 : 1) * R_INNER_FACE * 0.5 : 0) +
            (titleLines.length === 1 ? -R_INNER_FACE * 0.42 : 0)
          ).toFixed(1)}">${esc(l)}</text>`
      )
      .join("");

    // Each hand is one rigid piece (loop + shank + blade) stacked on the pivot in person order.
    const hands = people
      .map(
        (p) => `<g class="hand hand-blade" data-blade="${esc(p.entity_id)}" data-entity="${esc(p.entity_id)}" tabindex="0" role="button"
                  aria-label="${esc(p.attributes.person_name)}"><g class="hand-body"></g></g>`
      )
      .join("");

    const legend = cfg.show_legend
      ? `<div class="legend">${people
          .map(
            (p) => `<div class="chip" data-entity="${esc(p.entity_id)}">
              <span class="dot" style="background:${esc(this._handColor(p))};color:${textColorFor(this._handColor(p))}">${esc(
                (String(p.attributes.person_name || "?").trim()[0] || "?").toUpperCase()
              )}</span>
              <span class="who">${esc(p.attributes.person_name)}</span>
              <span class="where"></span></div>`
          )
          .join("")}</div>`
      : "";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        ha-card { overflow:hidden; }
        .case { padding: 18px; }
        .case.wood {
          background:
            repeating-linear-gradient(97deg, rgba(0,0,0,.07) 0 2px, transparent 2px 9px),
            repeating-linear-gradient(83deg, rgba(255,255,255,.04) 0 1px, transparent 1px 13px),
            linear-gradient(135deg, #6e4423, #4a2c15 55%, #5d391c);
          box-shadow: inset 0 0 0 6px rgba(0,0,0,.18), inset 0 0 30px rgba(0,0,0,.45);
        }
        svg { display:block; width:100%; height:auto; max-width:620px; margin:0 auto; overflow:visible; }
        .dividers line { stroke:#3a3328; stroke-width:.9; }
        .label {
          font-family: "IM Fell English", "Palatino Linotype", Palatino, Georgia, serif;
          font-style: italic; fill:#211c15; text-anchor:middle; dominant-baseline:central;
        }
        .title {
          font-family: ${cfg.title_font ? `"${esc(cfg.title_font)}", ` : ""}"Pirata One", "Old English Text MT", "IM Fell English", Georgia, serif;
          fill:#1c1812; text-anchor:middle; dominant-baseline:central;
        }
        .hand { cursor:pointer; transition: transform 2.4s cubic-bezier(.45,-0.25,.35,1.3); outline:none; }
        .hand.lost { opacity:.45; }
        .hand:focus-visible .shaft { stroke:#fff; stroke-width:1.6; }
        .hand-name {
          font-family: "IM Fell English", Georgia, serif; font-size:9.5px; font-weight:bold;
          text-anchor:middle; dominant-baseline:central; letter-spacing:.6px; pointer-events:none;
          text-transform: uppercase;
        }
        .hand-initial {
          font-family: "Cinzel", "Trajan Pro", "Times New Roman", serif; font-weight:700; stroke-width:.9px; stroke-linejoin:round; pointer-events:none;
        }
        .legend { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; padding:14px 4px 2px; }
        .chip {
          display:flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; cursor:pointer;
          background: rgba(251,247,236,.92); color:#211c15; font-family:"IM Fell English", Georgia, serif; font-size:14px;
          box-shadow: 0 1px 2px rgba(0,0,0,.3);
        }
        .chip .dot {
          width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
          font-family:"Pirata One", Georgia, serif; font-size:12px; line-height:1;
        }
        .chip .who { font-weight:bold; }
        .chip .where { font-style:italic; }
        .case:not(.wood) .chip { background: var(--secondary-background-color); color: var(--primary-text-color); }
        @media (prefers-reduced-motion: reduce) { .hand { transition:none; } }
      </style>
      <ha-card>
        <div class="case ${cfg.wood ? "wood" : ""}">
          <svg viewBox="-205 -205 410 410" role="img" aria-label="${esc(title || "Weasley clock")}">
            <defs>
              <linearGradient id="brassA" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#fff2b0"/><stop offset=".22" stop-color="#d9ac4b"/>
                <stop offset=".5" stop-color="#8a6420"/><stop offset=".75" stop-color="#e8c564"/>
                <stop offset="1" stop-color="#6d4c14"/>
              </linearGradient>
              <linearGradient id="brassB" x1="1" y1="1" x2="0" y2="0">
                <stop offset="0" stop-color="#fff2b0"/><stop offset=".3" stop-color="#c79a3c"/>
                <stop offset=".6" stop-color="#7a5717"/><stop offset="1" stop-color="#e3be5c"/>
              </linearGradient>
              <radialGradient id="paper" cx="45%" cy="40%" r="70%">
                <stop offset="0" stop-color="#fdfbf4"/><stop offset=".7" stop-color="#f3eedf"/>
                <stop offset="1" stop-color="#e2d9c0"/>
              </radialGradient>

              <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="2" dy="3" stdDeviation="2.2" flood-color="#000" flood-opacity=".45"/>
              </filter>
            </defs>
            <circle r="${R_BEZEL + 4}" fill="#2a1a0c" opacity=".55" filter="url(#shadow)"/>
            <circle r="${R_BEZEL}" fill="url(#brassA)"/>
            <circle r="${R_BEZEL - 7}" fill="url(#brassB)"/>
            <circle r="${R_FACE + 2.5}" fill="#5b4316"/>
            <circle r="${R_FACE}" fill="url(#paper)"/>
            <g class="dividers">${dividers}</g>
            <circle r="${R_FACE - 0.5}" fill="none" stroke="#3a3328" stroke-width=".8"/>
            <circle r="${R_INNER_RING}" fill="url(#brassB)" filter="url(#shadow)"/>
            <circle r="${R_INNER_RING - 5}" fill="url(#brassA)"/>
            <circle r="${R_INNER_FACE}" fill="url(#paper)"/>
            <g class="labels">${labels}</g>
            <g class="titles">${titleSvg}</g>
            <g class="hands" filter="url(#shadow)">${hands}</g>
            <circle r="11" fill="url(#brassA)" filter="url(#shadow)"/>
            <circle r="5.5" fill="url(#brassB)"/>
          </svg>
          ${legend}
        </div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll("[data-entity]").forEach((el) => {
      const open = () =>
        this.dispatchEvent(
          new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId: el.dataset.entity } })
        );
      el.addEventListener("click", open);
      el.addEventListener("keydown", (ev) => (ev.key === "Enter" || ev.key === " ") && open());
    });
    // New DOM: let hands sweep in from 12 o'clock.
    this._angles = {};
  }

  _placeHands(locations, people) {
    const n = Math.max(locations.length, 1);
    const seg = 360 / n;
    const groups = {};
    people.forEach((p) => {
      const idx = p.attributes.location_index;
      const k = idx === null || idx === undefined ? "lost" : idx;
      (groups[k] = groups[k] || []).push(p);
    });

    Object.entries(groups).forEach(([k, members]) => {
      const lost = k === "lost";
      const centre = lost ? 0 : Number(k) * seg;
      const spread = Math.min(seg * 0.7, 13 * (members.length - 1));
      members.forEach((p, j) => {
        const offset = members.length > 1 ? -spread / 2 + (j * spread) / (members.length - 1) : 0;
        const target = centre + offset;
        const length = R_HAND - (members.length > 1 ? (j % 3) * 11 : 0);
        this._drawHand(p, target, length, lost, members.length > 1 ? j % 3 : 0);
      });
    });

    this.shadowRoot.querySelectorAll(".chip").forEach((chip) => {
      const st = this._hass.states[chip.dataset.entity];
      const where = chip.querySelector(".where");
      if (where) where.textContent = st ? (st.state === "unknown" ? "?" : st.state) : "";
    });
  }

  // Size and place an initial so its ink spans the hole and touches the rim.
  // Uses canvas text metrics (real glyph ink bounds, not the em box).
  _initialGeometry(letter, cx, cy, hole) {
    const ctx = (this._measureCtx ||= document.createElement("canvas").getContext("2d"));
    ctx.font = `700 100px ${INITIAL_FONT}`;
    const m = ctx.measureText(letter);
    const asc = m.actualBoundingBoxAscent || 70;
    const desc = m.actualBoundingBoxDescent || 0;
    const left = m.actualBoundingBoxLeft || 0;
    const right = m.actualBoundingBoxRight || 60;
    const inkH = asc + desc;
    const inkW = left + right;
    // Cap height just over the hole so the top and bottom strokes fuse into the rim;
    // wide letters are limited so their corner serifs reach (and join) the rim
    // without losing the letter shape.
    // Round letters would merge into the rim, so they are set smaller and joined
    // with short bridges (top/bottom) where their strokes cross the centre line.
    const round = "OCGQSDU".includes(letter);
    let size = (100 * (2 * hole + (round ? -5 : 1.2))) / inkH;
    size = Math.min(size, (100 * (2 * hole * (round ? 0.8 : 1.02))) / inkW);
    const k = size / 100;
    const top = cy - (inkH * k) / 2;
    const bottom = cy + (inkH * k) / 2;
    const bridges = [];
    if (round) {
      if (letter !== "U") bridges.push([cy - hole - 0.6, top + 1.2]);
      bridges.push([bottom - 1.2, cy + hole + 0.6]);
    }
    return {
      size,
      x: cx - (inkW * k) / 2 + left * k,
      y: cy + ((asc - desc) * k) / 2,
      bridges,
    };
  }

  _hookFonts() {
    if (this._fontsHooked) return;
    this._fontsHooked = true;
    ensureFonts().then(() => {
      // Re-measure initials now the real glyphs are available.
      this.shadowRoot.querySelectorAll(".hand-body").forEach((b) => delete b.dataset.sig);
      if (this._hass) this._update();
    });
  }

  _handColor(p) {
    if (this._config.person_colors && p.attributes.color) return p.attributes.color;
    return this._config.hand_color || "#141414";
  }

  _drawHand(p, target, length, lost, tier = 0) {
    const sel = (attr) => this.shadowRoot.querySelector(`[${attr}="${CSS.escape(p.entity_id)}"]`);
    const blade = sel("data-blade");
    if (!blade) return;
    const id = p.entity_id;
    const first = !(id in this._angles);
    let cur = first ? 0 : this._angles[id];
    const delta = ((((target - cur) % 360) + 540) % 360) - 180;
    cur += delta;
    this._angles[id] = cur;

    const color = this._handColor(p);
    const ink = textColorFor(color);
    const name = p.attributes.person_name || p.entity_id;
    const initial = (name.trim()[0] || "?").toUpperCase();
    const L = length;
    const f = (v) => v.toFixed(1);

    // One half of a pair of scissors, pointing up (-y), pivot at the origin.
    // Blade: straight cutting edge on the left, curved back on the right.
    const bladePath = [
      "M -7 -6",
      `L -1.8 ${f(-L * 0.86)}`,
      `Q -0.7 ${f(-L * 0.97)} 0.6 ${-L}`,
      `Q 5.5 ${f(-L * 0.76)} 12.5 ${f(-L * 0.36)}`,
      "Q 15.5 -16 11 -6",
      "Z",
    ].join(" ");
    const engraving = `M 9 -11 Q 11.6 ${f(-L * 0.3)} 3 ${f(-L * 0.74)}`;
    // Shank from the pivot down to the finger loop.
    const ringX = -6;
    const ringY = 52 + tier * 13; // hands sharing a place get longer shanks so loops don't coincide
    const ringR = 17;
    const shank = `M -5 4 Q -12 24 ${ringX - 5} ${ringY - ringR + 3} L ${ringX + 6} ${ringY - ringR + 1} Q -1 24 6 5 Z`;

    const norm = ((cur % 360) + 360) % 360;
    const leftSide = norm > 180;
    const start = 17;
    const end = L * 0.7;
    const mid = (start + end) / 2;
    const room = end - start;
    const est = name.length * 6;
    const fit = est > room ? ` textLength="${f(room)}" lengthAdjust="spacingAndGlyphs"` : "";
    const textTransform = leftSide ? "rotate(90)" : "rotate(-90)";
    const textX = leftSide ? -mid : mid;
    const textY = leftSide ? -3 : 3;

    // The loop is a real hole (even-odd fill) so whatever is beneath shows through.
    // The initial is fretwork: same metal as the hand, scaled so its strokes run into
    // the rim and clipped to the hole so letter and loop read as one piece.
    const holeR = ringR - 4.5;
    const clipId = `wc-loop-${CSS.escape(id).replace(/[^a-zA-Z0-9_-]/g, "_")}`;
    const ini = this._initialGeometry(initial, ringX, ringY, holeR);
    this._hookFonts();
    // Light the whole hand from the top-left of the screen whatever the hand angle:
    // the filter works in the hand's rotated space, so counter-rotate the light.
    const bevelId = `${clipId}-bevel`;
    const lightAz = 225 - norm;
    const ringPath =
      `M ${ringX - ringR} ${ringY} a ${ringR} ${ringR} 0 1 0 ${2 * ringR} 0 a ${ringR} ${ringR} 0 1 0 ${-2 * ringR} 0 Z ` +
      `M ${ringX - ringR + 4.5} ${ringY} a ${ringR - 4.5} ${ringR - 4.5} 0 1 0 ${2 * (ringR - 4.5)} 0 a ${ringR - 4.5} ${ringR - 4.5} 0 1 0 ${-2 * (ringR - 4.5)} 0 Z`;
    const bladeBody = blade.querySelector(".hand-body");
    const sig = [color, name, initial, L, tier, leftSide, Math.round(norm)].join("|");
    if (bladeBody.dataset.sig !== sig) {
      bladeBody.dataset.sig = sig;
      bladeBody.innerHTML = `
        <filter id="${bevelId}" filterUnits="userSpaceOnUse" x="-40" y="${-L - 10}" width="80" height="${L + ringY + ringR + 20}" color-interpolation-filters="sRGB">
          <feGaussianBlur in="SourceAlpha" stdDeviation="1.1" result="blur"/>
          <feSpecularLighting in="blur" surfaceScale="2.6" specularConstant="1" specularExponent="16"
                              lighting-color="#ffffff" result="spec">
            <feDistantLight azimuth="${f(lightAz)}" elevation="38"/>
          </feSpecularLighting>
          <feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn"/>
          <feDiffuseLighting in="blur" surfaceScale="2.6" diffuseConstant="1" lighting-color="#ffffff" result="diff">
            <feDistantLight azimuth="${f(lightAz)}" elevation="50"/>
          </feDiffuseLighting>
          <feComposite in="SourceGraphic" in2="diff" operator="arithmetic" k1="0.55" k2="0.6" k3="0" k4="0" result="lit"/>
          <feComposite in="lit" in2="SourceAlpha" operator="in" result="litIn"/>
          <feComposite in="litIn" in2="specIn" operator="arithmetic" k1="0" k2="1" k3="0.5" k4="0"/>
        </filter>
        <clipPath id="${clipId}"><circle cx="${ringX}" cy="${ringY}" r="${holeR + 0.6}"/></clipPath>
        <g class="metal" filter="url(#${bevelId})">
        <path d="${shank}" fill="${esc(color)}"/>
        <path d="${ringPath}" fill="${esc(color)}" fill-rule="evenodd"/>
        <g clip-path="url(#${clipId})">
          ${ini.bridges
            .map(([y1, y2]) => `<rect x="${ringX - 1.3}" y="${f(y1)}" width="2.6" height="${f(y2 - y1)}" fill="${esc(color)}"
                  transform="rotate(${f(-norm)} ${ringX} ${ringY})"/>`)
            .join("")}
          <text class="hand-initial" fill="${esc(color)}" stroke="${esc(color)}"
                x="${f(ini.x)}" y="${f(ini.y)}" font-size="${f(ini.size)}"
                transform="rotate(${f(-norm)} ${ringX} ${ringY})">${esc(initial)}</text>
        </g>
        <path class="shaft" d="${bladePath}" fill="${esc(color)}"/>
        <circle r="10" fill="${esc(color)}"/>
        </g>
        <path d="${engraving}" fill="none" stroke="${ink}" stroke-opacity=".28" stroke-width=".7" pointer-events="none"/>
        <text class="hand-name" fill="${ink}" transform="${textTransform}" x="${f(textX)}" y="${textY}"${fit}>${esc(name)}</text>`;
    }

    for (const g of [blade]) {
      g.classList.toggle("lost", lost);
      if (first) {
        g.style.transition = "none";
        g.style.transform = "rotate(0deg)";
        void g.getBoundingClientRect(); // force reflow so the first sweep animates
        g.style.transition = "";
      }
      g.style.transform = `rotate(${cur}deg)`;
    }
  }
}

if (!customElements.get("weasley-clock-card")) {
  customElements.define("weasley-clock-card", WeasleyClockCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "weasley-clock-card",
    name: "Weasley Clock",
    description: "Shows where everyone is on a magical brass clock face.",
    preview: true,
    documentationURL: "https://github.com/VaticanUK/virtual-weasley-clock",
  });
  console.info(`%c WEASLEY-CLOCK-CARD %c ${CARD_VERSION} `, "background:#8a6420;color:#fff2b0", "background:#211c15;color:#fff");
}
