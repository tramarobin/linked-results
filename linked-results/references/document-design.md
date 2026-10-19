# The page: layout, linking, tables, figures

`scripts/template.html` holds the CSS, the HTML skeleton and all the JavaScript. The builder replaces
`/*DATA*/` (exactly once) and the empty `<title>`, and strips `<!-- -->` comments. JavaScript comments
ship with the page, so keep them free of internal names (SKILL.md rule 8).

## Contents
1. Layout
2. Linking
3. Tables
4. Figures
5. Statistics panel
6. Colours, themes, sizes
7. Stability
8. Where to change what

## 1. Layout
- A sticky top bar: the title, then **Methods** and **Results** tabs (upper case, underlined when
  selected). Under Results, a chip bar per level: the groups (e.g. Vibrations, EMG), then the tabs of the
  group (e.g. Peak acceleration … Damping). A bar with one chip is hidden.
- **Methods:** one prose box: the `methods.md` sections, then the generated "How to read this
  document", then the references. After the participants' section (`participants.section`): their table
  (characteristic, unit, mean (SD), range; numeric characteristics only, the counts being in the text), a figure with one violin
  per characteristic and every participant as a cross, and **Values per participant** with a CSV download.
  The methods' participant numbers are linked to that table and figure; hovering "12 men" marks the men's
  crosses.
- **A results tab**, top to bottom: the **Results** paragraphs (one per row), the table, then
  **Values per participant** (collapsed; a CSV download).
- **The figure and statistics panel** shows one row: beside the content, sticky, from 1400 px wide;
  below 1400 px it docks at the bottom (half the viewport), with **Hide figure / Show figure** remembered
  in `localStorage` (inside try/catch). Pinning shows it again. The first row of the tab is shown on
  opening; hovering another row's statistic or label shows that row.
- Phones: one column, a 16 px gutter, no sideways page scroll; wide tables scroll inside their box, with a
  round arrow on each side on hover.
- The page opens on Methods; then the last tab opened is remembered.

## 2. Linking
- Every statistic has a key (`references/texts.md` §4), carried as `data-row` + `data-k` by text spans,
  table cells and statistics rows, and as `data-row` + `data-ks` (a list) by the figure's panels, violins
  and brackets.
- **Hover** marks every element whose key is the same or related (a comparison and its ANOVA term);
  **click** pins it (`pin`); a second click, **Esc**, or a click on nothing that links releases it
  (`clickUsed` is set by a pin and reset on a capturing `pointerdown`). Controls (buttons, links,
  summaries, chips) never release.
- The house style of a mark: texts, cells and rows take a soft blue (`--sel-soft`), deeper when pinned
  (`--sel`, with a 2 px ring of the same colour on text); a figure panel or violin is **lifted**: a card
  (`--lift`) on a soft drop shadow, deeper when pinned. No yellow, no outline that changes a box's size.

  | Element | Hovered | Pinned | Tokens (light / dark) |
  |---|---|---|---|
  | Text statistic, citation, reference entry | `--sel-soft` + 2 px ring of it | `--sel` + ring | `#eaf1f9` / `#22303f`; `#d6e3f2` / `#2e4560` |
  | Table cell or row, statistics row | `--sel-soft` | `--sel` | as above |
  | Figure panel or violin | `--lift` + `drop-shadow(0 1px 5px var(--lift-sh))` | `drop-shadow(0 2px 9px var(--lift-sh2))` | `#ffffff`, `rgba(0,35,80,.28)`, `.42` / `#2a3038`, `rgba(0,0,0,.6)`, `.85` |
  | Comparison (bracket + p) | bracket 2.4 px, a `--sel-soft` chip behind the p | chip `--sel` | |
  | Participant (crosses, lines) | ink, crosses 2.8 px, lines 2 px; no ring | same | |

  Text links fade in (`transition: background-color .12s`) and keep their mark on each line when they wrap
  (`box-decoration-break: clone`). These are the author's court report's marks, chosen over a yellow band.
- A figure's panel stands for its main effect (row 1) or its comparison (interaction rows); a violin for
  its condition or level; a bracket for its comparison. Hovering them marks the texts and tables the same
  way.
- Participants: hovering a cross (or a row of the values table) marks that participant in every panel and
  every open figure, and in the values table; the marked crosses are copied to a top layer so they come
  in front of the mean labels.

## 3. Tables
- **Main table** (one per tab): the row label (split level, or outcome), the unit, mean (SD) of each
  condition (the second factor's levels as a header spanning the first factor's), then the p of each
  ANOVA term. Bold only when p ≤ alpha. Colour keys (a short line in the level's colour) on the headers.
- The note under it says what the values are, the design and the permutations when the sheet gives them.
- **Values per participant:** one column group per row of the tab, separated by a vertical rule, every
  other group shaded; values with one more decimal than the means; download as CSV (UTF-8 with BOM, so
  that Excel reads the units).

## 4. Figures (violins)
- **Panels:** with two factors, row 1 holds the main effects (each participant's mean over the other
  factor's levels), row 2 the first factor within each level of the second, row 3 the second within each
  level of the first. Each row has a caption: what it reads and, for the interaction rows, its p.
  One factor: one panel.
- **A violin:** the kernel density (Silverman's bandwidth) in the level's colour, its outline bold over
  the mean ± SD, a black mean line with the mean and (SD) written on it, every participant as a ×, spread
  sideways only to avoid overlap. Within-participant panels join each participant's values with a grey
  line; the spread is the smallest density of the participant's values, so the line stays level.
- **Brackets:** two levels: always one bracket with its p ("p = 0.003", bold when significant; "NS:
  p = 0.068" in muted ink). More levels: one bracket per significant pair, stacked. In an interaction row
  whose interaction is not significant, brackets are pale (outside the interaction).
- **Scale:** the same round ticks in every panel, taken from the data (`niceStep`); the headroom of each
  line of panels is grown until its brackets fit under the titles. A dashed zero line when 0 is in range.
- **Drawn at the box's width**, never scaled, so text stays ~12 px; redrawn on resize. Below 460 px, one
  panel per line (the row's caption over its first panel), so level names never collide.
- **Tooltips:** a participant (P#, condition, value); a violin (condition, mean, SD, n); a bracket (the
  comparison: difference, relative, p, g, t against its threshold, inside or outside).
- **⤢** (top right, faint until hovered) opens the figure in a dialog, redrawn at the dialog's width;
  Close, Esc or a click on the backdrop closes it.

## 4b. Correlations (a results tab with `"correlations": true`)
- **Table:** one row per outcome; one column group per split level, one column per level of `by`; each
  cell "r (p)", bold when significant, linked to its scatter plot. The note gives the y formula, its sign
  and the correction ("Holm–Bonferroni over the 8 tests of each axis").
- **Scatter plots** (the panel): one per level of `by`, side by side (stacked below 460 px). x the
  characteristic, y the difference, a dashed zero line, the least-squares line over the participants' range
  (solid when significant, dashed grey otherwise), every participant as a cross. Above each: the level, then
  "r = −0.83, p = 0.001 (very strong)", bold when significant. The same y axis for the panels of a row.
- **Statistics:** n, r, slope (y unit per x unit), p, p uncorrected, strength; the note gives the method,
  the correction and the strength thresholds.
- **Values per participant:** the characteristic, then every y.

## 4c. Participants, everywhere
Hovering a participant's cross (any figure) or row (any values table) marks them in every figure shown and
every values table, and the tooltip adds their characteristics (sex, age, height…), so a collaborator can
see who an outlier is without leaving the figure.

## 4d. Citations
`.cite` spans (dotted underline). Hover: after 150 ms the reference opens in a popover under the line the
pointer is on (over it when there is no room), with its links in a new tab; it closes 250 ms after the
pointer leaves, so the pointer can reach the link. Click keeps it; Esc, ×, a second click or a click
elsewhere closes it; keyboard focus opens it. The citation and its `.refentry` in the list take the soft
blue (class `chov`, not `hov`, so the statistics' marking leaves them alone); hovering an entry marks its
citations.

## 5. Statistics panel (under the figure)
- **Analysis of variance:** Effect | F | df | p (bold when significant); the F threshold in the row's
  tooltip; a note on the permutations.
- **Conditions:** each level over the other factor, then each condition: n, mean, SD.
- **Comparisons:** Comparison | Difference (unit) | Relative | p | g. The main effects first, then one block
  per reading of the interaction, its sub-header saying inside (with the interaction's p) or outside (pale,
  never bold). t, its threshold and the comparison's own p are in the row's tooltip, not in a column.

## 6. Colours, themes, sizes
- Tokens on `:root`, redefined for dark mode under `prefers-color-scheme: dark` (guarded by
  `:root:not([data-theme="light"])`) and under `:root[data-theme="dark"]`. Level colours become CSS
  variables (`--c-<factor>-<level>`) with their dark values.
- Text is never in a series colour: labels and values stay in ink; the colour is on the violins and keys.
- The page is ~0.1 MB for nine analyses of 15 participants; it grows with participants × conditions.

## 7. Stability
Hovering or pinning changes colours and shadows only, never a box's size, so nothing moves. Showing
another row redraws the panel at the same size (its height is held while it redraws, and its scroll kept).
`check_document.py` compares every element's box before and after each hover to 0.01 px.

## 8. Where to change what
| Change | Where |
|---|---|
| Words of the texts | `study.json` phrases, or `Texts` in `build_document.py` (`references/texts.md` §5) |
| Methods, references | `methods.md` |
| Reading guide | `guide()` in `build_document.py` |
| Table columns | `mainTable()`, `peopleTable()` |
| Figure layout, violins, brackets | `panelsOf()`, `drawFigure()` |
| Statistics panel | `statsOf()` |
| Hover and pin behaviour | `paint()`, `setHover()`, `toggle()`, `wire()` |
| Participants' table, figure and cards | `participantsBlock()`, `drawTraits()`, `personLines()` |
| Correlations | `corrTable()`, `drawScatter()`, `corrStats()`, `Texts.corr_paragraph()` |
| Citations | `resolve_refs()` (builder), the citations block (`openPop()`) |
| Colours of marks, layout breakpoints | the `<style>` block (tokens at the top) |

After any change: build, `check_document.py` at several widths and in dark mode, screenshots.
