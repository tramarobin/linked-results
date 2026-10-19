---
name: linked-results
description: Turn a study's data and its already-computed statistics (a tidy stats sheet of ANOVA terms and post hoc comparisons, and optionally a sheet of correlations, from any software) into one self-contained, interactive HTML results document - Methods (with a participants table and figure) and Results tabs, violin plots and scatter plots with every participant, tables, per-participant values with CSV download, hoverable citations, and results texts written from the data in which every statistic is linked to its table row and figure (hover marks it everywhere, click keeps it). Python only; it never computes a p-value. Use it whenever someone wants to share or browse a full set of results (one- or two-factor designs, within and/or between participants, several outcomes, separate analyses per axis or side, correlations with a participant characteristic), wants such a document built, rebuilt after new data, adapted to another study, fixed or verified, or asks how to word or show such results, even without naming the skill.
---

# Linked results document

This skill builds **one HTML file** that holds every result of a study, so that collaborators can browse a
large set of results without opening spreadsheets and figure folders: texts, tables and figures stay in
step, and each number can be traced to its statistic and to every participant's values.

It **designs**; it does not analyse. The statistics are given in sheets (from MATLAB, R, Python, JASP,
SPSS...). The builder computes only descriptive values (means, SDs, differences, relative differences, a
correlation's r to check the sheet, and effect sizes when the sheet has none), and checks them against the
sheets.

## What it needs

| Input | What it is | Contract |
|---|---|---|
| Data | One CSV per outcome, one row per participant, one column per condition (`ACC.C.L` = levels joined by a separator) | `references/data-contract.md` §2 |
| Stats sheet | One tidy CSV: one row per ANOVA term and per comparison | §3 |
| Participants file (optional) | **Anonymized**: the data's IDs only, then characteristics (age, height, fat thickness…) and between-participant factors | §1, §2 |
| Correlations sheet (optional) | One row per correlation of a participant characteristic with a per-participant difference (r, p, slope…) | §3.4 |
| `study.json` | Factors (level names, phrases for texts, colours, reference level), outcomes (names, units, decimals), the split (separate analyses, e.g. axes), the tabs, the participants and correlations settings | §1 |
| `methods.md` | The methods in Markdown; `{n}`, `{mean_sd:age}`, `{count:sex=M}`… are filled (and linked) from the data; `[@key]` cites an entry of its References section | §4 |

A worked example ships with the repository: `example/study.json`, `example/methods.md` and `data/`, built
into `example/muscle-vibration-results.html`.

## Building

```
python scripts/build_document.py <study.json> --check        # validate, print every generated text
python scripts/build_document.py <study.json> [--out <page>]  # write the page (default: <file_name>.html)
python scripts/check_document.py <page.html>                  # test it in headless Edge/Chrome
```

Python 3.9+ and the standard library only; the check needs Edge or Chrome. The page loads no external
resource and works offline, from disk or from any web host.

### Workflow for a new study
1. **Read the data and the statistics.** Map the columns to factors and levels. If the statistics come in
   another layout, write a small converter to the sheets first (`references/data-contract.md` §3.3). Never
   fill a p-value by hand, never compute one.
2. **Anonymize the participants file.** Keep only the data's IDs and the characteristics to show; no names,
   initials, dates of birth or original subject numbers. A file with identifying columns never goes beside
   the data that will be shared: say so to the user, and add it to `.gitignore` when the folder is a repository.
   Check which participants were analysed (the analysis scripts usually list them) and in which order.
3. **Write `study.json`.** Choose each factor's reference level (the denominator of relative differences: a
   baseline, a control, the gold-standard device) and the phrases the texts use ("with accelerometry", "in
   the contracted muscle"). Ask the user when the reference is not obvious.
4. **Write `methods.md`** from the user's protocol or article. Change only what differs (usually the
   statistics), say so in an opening paragraph, and put numbers that come from the data as placeholders.
   Cite with `[@key]` against a `## References` section.
5. **`--check`**, and read every generated sentence against the sheets. The build stops on a level that is
   not in the data, a missing ANOVA term or comparison, a sheet difference or r that does not match the
   data, an unknown placeholder or citation.
6. **Build, then `check_document.py`** (wide, `--width 1000`, `--width 390`, `--dark`, `--dpr 1.25`), and
   look at screenshots (`--shot out.png --tab G,T`) before showing anything (`references/verification.md`).

### Data-only update
New participants or re-run statistics, same design: replace the CSVs and the sheets, then build and check.
Every number and every wording that depends on significance is regenerated; nothing is typed by hand.

## Standing rules

These come from the author's results pages; follow them without being asked.

1. **Every number in a text comes from the data**, through the generator, never typed (methods included:
   use placeholders). Texts are regenerated at each build, and the builder asserts that every cited
   statistic exists.
2. **Bold means significant (p ≤ α), and only that**, in tables and figures. Plain values are never bold.
3. **Text, tables and figures are linked and behave the same way.** Hovering a statistic marks it
   everywhere: a soft blue on texts, cells and rows; the figure's panel or violin lifted on a soft shadow; a
   soft-blue chip behind a comparison's p. A click keeps it (deeper blue, deeper shadow); a second click,
   Esc or a click on nothing releases it. Nothing on the page moves while this happens
   (`check_document.py` measures it to 0.01 px). Never a yellow band.
4. **An absolute difference wherever a relative one appears**: "−10.0 Hz, −34.8%, p = 0.003". Turn the
   relative difference off for an outcome whose reference is near 0 (`"relative": false`).
5. **Interactions: say which reading, and inside or outside.** A comparison is part of the interaction
   only where the interaction is significant (drawn solid). Otherwise it is drawn pale, greyed in the
   tables and never cited as an interaction effect: it mostly reflects a main effect.
6. **p-values only from the sheets**; means, SDs, differences and effect sizes may be computed, but a stored
   effect size comes first. Never offer what the analysis does not give (no t-based CI beside permutation
   p-values).
7. **Differences come from group means** (test − reference, relative to the reference's mean), never from
   averaged individual ratios, which explode near zero.
8. **The document is shared.** No internal script or file names, no build dates; participants are shown as
   P1…Pn (natural order of their IDs); never mention excluded participants; the participants file is
   anonymized (step 2). Even anonymized, sex + age + height + mass can identify someone in a small sample:
   remind the user to check that their ethics approval covers sharing them. Software that is part of the
   method stays in the methods. JavaScript comments ship with the page; `<!-- -->` comments do not.
9. **References are hoverable.** Every citation opens its reference in a popover with its link, and marks
   its entry in the list (and the reverse). Citations are generated from the list by key.
10. **Say how p-values were corrected, and for which family**, in the methods and in the tables' notes
    (e.g. Holm–Bonferroni over the 8 tests of each axis). When the user's article and the data disagree
    (a significance that the stated correction cannot give), show the user the numbers and ask which
    correction to use; do not choose silently.
11. **Never delete outputs to rebuild them; overwrite them.** Back up a hand-edited page before a rebuild.
12. **Claims with "only", "every" or "no other" are generated from every listed result**, so adding an
    outcome keeps them true.

## References

| Task | Read |
|---|---|
| The inputs: `study.json`, data, participants, stats and correlations sheets (columns, sign conventions, converters), methods placeholders and citations | `references/data-contract.md` |
| How the texts are written and how to change their wording safely | `references/texts.md` |
| The page: layout, tabs, linking keys, tables, figures, participants block, correlations, citations, colours, dark mode, phone layout, what to change where | `references/document-design.md` |
| Checking a build: the checks, screenshots, what to look at, common failures | `references/verification.md` |

## Limits (extend the builder when a study needs more)
- One or two factors, each within or between participants, with any number of levels; one split
  (separate analyses per level, such as an axis or a side). Three-factor designs need a third reading in
  `panelsOf()` and `Texts.row_paragraph()`.
- Scalar outcomes (one value per participant and condition). Curves and maps need another figure type.
- Correlations: one participant characteristic (x) against a per-participant difference or relative
  difference between two levels of one factor, at each level of the other factor (`by`), per outcome and
  split level. Correlations between two outcomes, or by age group, need another row type.
