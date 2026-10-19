# Checking a build

A document is shared, so check it before calling it done, and say what was checked and how.

## 1. The build's own checks
`python scripts/build_document.py <study.json> --check` validates the inputs (`data-contract.md` §5) and
prints every generated paragraph without writing the page. Read each paragraph against the stats sheet:
direction, size, the right p, inside or outside the interaction. Any failure stops the build with a
message naming the outcome, split and level.

## 2. The page in a headless browser
```
python scripts/check_document.py "<page.html>"                                 # 1600 × 1000
python scripts/check_document.py "<page.html>" --width 1000 --dark --dpr 1.25  # docked panel, dark, scaled display
python scripts/check_document.py "<page.html>" --width 390 --height 844        # phone
```
It needs Edge or Chrome (set `CHROME` to choose one) and the Python standard library. It prints a JSON
report and exits with 1 when something fails:

| Field | Must be | Means |
|---|---|---|
| `badSpans` | `[]` | a text statistic that does not mark its table or statistics row and its figure element |
| `badCells` | `[]` | a table value or p that does not mark its figure and statistics row |
| `badRows` | `[]` | a statistics row that does not mark its figure element |
| `shifts` | `[]` | an element that moved by 0.01 px or more while something was hovered |
| `pins` | `[]` | a pin that a click, Esc or a click on nothing did not set or release |
| `cites` | `[]` | a citation whose popover did not open with its reference, did not mark its entry, or did not close |
| `methods` | counts | the methods' participant statistics, table rows and citations covered |
| `dialog` | open, svg | the enlarged figure |
| `text` | `[]` | "NaN", "undefined", "Infinity" or "null" somewhere in the page |
| `console` | `[]` | an exception, a console error or warning |

The counts (`spans`, `cells`, `statRows`, `methods`) tell how much was covered; the example covers 39
results statistics, 79 cells, 169 statistics rows, and in the methods 9 statistics, 5 rows and 3 citations.

## 3. Screenshots, then look at them
`--shot out.png --tab G,T` (group G, tab T, from 0; `-1,0` the methods; `--full` the whole page;
`--no-checks` for the screenshot alone). Crop the part that changed (PIL:
`Image.open(p).crop((x0, y0, x1, y1))`) and look at it: labels that collide, brackets under a title, a
caption cut at the edge, a violin squashed by headroom, a table wider than its box. The checks test logic;
only the image shows the layout.

Look at least at: a tab with an interaction, a tab without one, the methods, the docked panel
(`--width 1000`), a phone (`--width 390`), and dark mode.

## 4. Common failures
- **"N columns for cell …"**: the pattern or the separator does not match the column names, or a fixed
  level (`fixed`) is missing for an outcome analysed once.
- **"the sheet's diff … is not the difference of the data's means"**: `level_a` and `level_b` swapped,
  `diff` given as b − a, or the stats were run on other data (different participants, other trials).
- **"… comparisons of X at Y=…, need …"**: the interaction family is incomplete; export both readings,
  even when the interaction is not significant.
- **A blank p in `--check` output**: a `<` written into HTML without escaping (the generator's `ph()`
  escapes it; keep using it in new sentences).
- **A page that does not load in the checker**: it says "the page did not load"; open the page in a
  browser and read its console.

## 5. Synthetic designs
To test a change to the builder or the template beyond the example, make a small synthetic study (for
example Group between × Time within with three levels, unequal groups, and a one-factor version), compute
its stats sheet with any ANOVA software, build it and run the checks. The between-factor and
three-level paths are not exercised by the example.
