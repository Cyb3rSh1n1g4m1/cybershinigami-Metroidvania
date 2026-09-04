# Canon reference — hybrid system

Two files govern the character; they answer different questions.

| File | Authority over | Attach when… |
|---|---|---|
| `charsheet_design.png` (Flash) | **Design truth** — black bg, backswept horns, full-face mask, left-hip daishō | …the generator is drifting off-model |
| `charsheet_quality.png` (Pro) | **Rendering quality** — hair volume/banding, linework, the exact `0x0029`/死神 back mark | …you want the drawing standard raised |

Known deviations in the quality sheet (design sheet wins on all three):
white background, horns curve up-forward, chin exposed in side view.

Everything else (`spritesheet`, `keyart_*`, `unmasked`, `enemies`, `objects`,
`icons`) is single-source canon. `spritesheet.png` is the per-frame painting
target for hand-polishing the procedural strips in Clip Studio.

Prompts that produced all of these: `../jobs.json` (run `python ../gen_ref.py ../jobs.json`).

---

## Model drift checklist — verify EVERY new player sheet against this

These details silently change between generations. Each has broken a sheet at
least once. Check them before slicing, not after wiring.

| # | Must be true | Failure seen |
|---|---|---|
| 1 | **Sleeves rolled to the elbows, bare BROWN forearms and hands** | air8 came back with full sleeves and pale grey hands |
| 2 | **White haori present in EVERY frame** | air8 dropped one frame; sheet_mega dropped the ENTIRE run row — dropout clusters by activity, so restate the haori inside at-risk row descriptions |
| 3 | **Horns swept BACKWARD**, never up or forward | charsheet_quality curved them up-forward |
| 4 | **Full-face mask** — no chin, jaw, or skin below it | charsheet_quality exposed the chin in profile |
| 5 | **Daishō at the LEFT hip only**, none on the back | early charsheets scattered them across views |
| 6 | **Ponytail BANDED** indigo → blue → cyan, not flat | first locomotion sheet came back all-cyan |
| 7 | **Pure black background** | ignored on maybe half of all sheets (harmless — the slicer flood-removes either polarity) |
| 8 | **One straight row, wide gaps, no arcs or overlap** | air8 drew a parabola; attack8's slash arcs bridged the gutters |
| 9 | **STRICT SIDE ELEVATION — no visible top surfaces, no isometric** | background rooftops were drawn from above; upgrade pedestals came back isometric with elliptical top rings |

**The ellipse test** for #9: any circle drawn as an *ellipse* means the camera is
above the object. Scan every new prop for ovals where there should be flat lines —
ring inlays, barrel tops, pipe mouths, rooftops. It is the fastest way to catch a
projection error before it ships.

### Two hard-won prompting rules

- **Never attach a reference image for a NEW action.** The reference dominates
  the text: attaching the combat sheet to a run-cycle prompt regenerated the
  *combat sheet*. Attach only when the goal is literally "same content, fix X."
- **Layout instructions must come FIRST and loudest.** Buried at the bottom they
  are ignored; leading with "LAYOUT IS THE MOST IMPORTANT REQUIREMENT" works.
