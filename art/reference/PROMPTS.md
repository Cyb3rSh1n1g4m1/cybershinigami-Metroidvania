# Image Prompts — Cyb3r$h1n1g4m1

Paste-ready prompts for ChatGPT (GPT Image) or Gemini (Nano Banana). Work down
the list — each one locks something the next one depends on.

**Two rules that matter more than the prompt text:**

1. **Attach the previous output as a reference image** on every prompt after #1.
   Say: *"Match this character exactly. Same mask, same horns, same hair, same
   outfit, same colors. Only change the pose/view."* Without this you get a
   different character every generation, which is the single biggest failure mode.
2. **Never let it invent colors.** The palette block is in every prompt below.
   If output drifts warm/purple/orange, re-paste the palette and say
   *"use ONLY these hex colors."*

---

## 1 — Character sheet (run this first, it defines everything else)

> Character reference sheet for a 2D video game. Pure black background. Three
> full-body views of the SAME character side by side: front view, side profile,
> and back view. Flat cel-shaded vector illustration, bold clean linework, hard
> shadows, no gradients, no soft rendering, no photorealism.
>
> CHARACTER — a cyberpunk death god. Lean, athletic, agile build, standing in a
> relaxed neutral pose, arms at sides.
>
> FACE — wears a Japanese hannya oni demon mask that covers the ENTIRE face,
> forehead to chin, in bright electric red with darker red carved detail. There is
> no skin and no visible face anywhere — the mask is the whole head front. The
> narrow angular eye slits and the wide fanged grinning mouth are open holes that
> glow with pale cyan-white spirit light from inside the empty skull, and that same
> ghostly light bleeds out from behind the rim of the mask along the jawline. A
> single small glowing cyan third eye sits on the mask's forehead. Two long
> twisted ridged horns in bright red sweep BACKWARD from the temples, not upward.
>
> HAIR — very long straight hair in a high ponytail trailing far down past the
> hips, banded in three flat color blocks: deep indigo blue at the roots, electric
> blue in the middle, bright cyan at the tips. Tied with an acid-green band.
>
> BODY — he is a Black man with deep brown skin. The tracksuit sleeves are pushed
> up to the elbows, so his bare brown forearms and hands are visible. Skin also
> shows at the neck between mask and collar. Use a warm brown skin ramp (shadow
> #4A2A1A, base #855434, highlight #B07A4A) with a thin cyan rim light so the
> skin reads against the neon.
>
> OUTFIT — a fusion of modern streetwear and samurai dress:
> · a black athletic TRACKSUIT jacket with a stand-up zip collar, and twin
>   parallel racing stripes in acid-green and cyan running down the outside of
>   both sleeves — sleeves pushed up to the elbow
> · black HAKAMA-style trousers, wide and pleated through the thigh, with the same
>   twin racing stripes down the outer seam, gathered into elastic tracksuit cuffs
>   at the ankles
> · black tabi split-toe boots
> · a deep blue obi sash at the waist with a thin acid-green line
> · over all of it, a PURE WHITE SLEEVELESS captain's haori — long, reaching below
>   the knee, hanging open at the front, with a torn ragged frayed hem. The white
>   haori is the brightest thing in the image and defines the silhouette against
>   the black background.
>
> WEAPONS — a matched samurai daisho pair, one long katana and one shorter
> wakizashi, both in black lacquered scabbards thrust through the sash at the LEFT
> hip, angled down and back. A thin acid-green glowing line runs along each
> scabbard mouth and sword guard.
>
> STRICT PALETTE — use ONLY these colors: black #000000, near-black #0A0E1F, deep
> indigo #1E33D9, electric blue #2B6FE8, cyan #35C6F4, pale cyan #8FE8FF, dark red
> #8F1116, electric red #E01F26, acid green #C6F02A, white #FFFFFF, grey #4A5568,
> plus the skin ramp #4A2A1A / #855434 / #B07A4A. No other colors. No purple, no
> orange. High-contrast neon on pure black.
>
> Game character model sheet, evenly lit, no background scenery, no text, no logos.

---

## 2 — Hero key art (attach #1 as reference)

> Match this character exactly — same mask, horns, hair, tracksuit, white ragged
> sleeveless haori, same colors. Now draw cinematic video game key art.
>
> He stands on a rain-slicked neon rooftop above a dense futuristic Japanese
> megacity at night. Glowing holographic signage, towering skyscrapers fading into
> fog, and a colossal distant torii gate silhouetted on the skyline. He is caught
> mid iaido draw-cut, ripping the katana from its scabbard at his hip — the exposed
> blade edge burns with a searing acid-green temper line and leaves a bright arcing
> slash trail through the air. The white haori and long cyan ponytail whip
> dramatically in the wind. Small floating green spirit flames drift around him.
>
> Flat bold cel-shaded illustration, heavy black shadows, dramatic neon rim
> lighting. Same strict palette: black, deep indigo, electric blue, cyan, pale
> cyan, dark red, electric red, acid green, white, grey. No other colors. No text.

---

## 3 — Pose sheet (attach #1 — this is the bridge to animation)

> Match this character exactly. Pure black background. One horizontal row of six
> full-body SIDE-PROFILE poses of the same character, all facing RIGHT, all the
> same size and standing on the same ground line, evenly spaced:
> 1. idle, relaxed, weight on back foot, both swords sheathed
> 2. mid-run, legs extended in a full stride, haori and ponytail streaming behind
> 3. jumping upward, knees tucked, one arm raised
> 4. falling, legs trailing, haori billowing up
> 5. high overhead sword cut, blade brought down from above the head
> 6. low sword cut, blade sweeping down and forward at ankle height
>
> Flat cel-shaded vector, bold clean linework, no gradients, identical character
> design in every pose. Same strict palette: black, deep indigo, electric blue,
> cyan, pale cyan, dark red, electric red, acid green, white, grey. No other
> colors. Character sheet layout, no background, no text.

---

## 4 — Pixel sprite conversion (attach #3)

> Convert this exact character into 2D game PIXEL ART. Side profile, facing right,
> idle standing pose, both swords sheathed. Low resolution pixel art with large
> chunky visible square pixels and hard aliased edges — NO anti-aliasing, NO
> blurring, NO smooth curves. The whole figure must be readable at roughly 40
> pixels tall, so simplify aggressively: the red mask, the white ragged haori, the
> cyan ponytail, and the black sheathed swords are the only shapes that need to
> survive. Pure black background.
>
> Use ONLY these 12 colors: #000000 #0A0E1F #1E33D9 #2B6FE8 #35C6F4 #8FE8FF
> #8F1116 #E01F26 #C6F02A #6B8A0F #FFFFFF #4A5568. Flat color blocks, at most two
> shades per material, no dithering, no gradients. Retro 16-bit game sprite.

**Reality check on #4:** AI models are poor at true pixel art — they produce
*pixel-art-styled illustrations* with off-palette colors and inconsistent pixel
grids. Treat the output as a **color and shape study**, then redraw it by hand on
a real 48×48 canvas in Clip Studio. Do not try to get finished sprites out of a
generator; frame-to-frame consistency is where it fails hardest, and a
Metroidvania needs ~47 consistent frames for the player alone.

---

## 4b — Unmasked form (attach #1; used for shrines, pause portrait, title screen)

> Match this character exactly — same hair, same tracksuit, same white ragged
> sleeveless haori, same colors — but the hannya mask is OFF, held loosely in his
> right hand at his side. Waist-up portrait on a pure black background.
>
> His face is visible: a Black man with deep brown skin, a short natural afro
> fade, rectangular glasses catching a faint cyan reflection, a mustache and
> goatee, and a single small stud earring. Calm, tired, knowing expression —
> a man who has seen the inside of the machine. The long blue-to-cyan ponytail
> is his own hair, unchanged. A faint cyan rim light traces his profile; small
> green spirit flames drift in the black behind him.
>
> Flat cel-shaded vector illustration, bold linework, hard shadows. Skin ramp
> #4A2A1A / #855434 / #B07A4A with cyan rim light. Same strict palette otherwise.
> No text.

**Tip:** if you want the face closer to your own, also attach a photo of yourself
to this prompt and say "base the face on this person." That's your call to make
with each service — a text description alone gets the vibe, a photo gets likeness.

---

## 5 — Enemy set (attach #1 for style match, optional)

> Same art style, same strict palette, pure black background. A row of four
> separate enemy character designs for a cyberpunk Japanese horror game, full body,
> side profile, facing right, flat cel-shaded vector:
> 1. a segmented mechanical worm-serpent of black chrome with red glowing seams
> 2. a hovering four-winged surveillance drone with a single cyan eye
> 3. a hunched humanoid husk in tattered black rags wearing a cracked broken white
>    oni mask, glowing green data leaking from the crack
> 4. a tall faceless guardian in heavy black segmented armor with acid-green
>    circuit lines and a broken red mask
>
> Each wears or carries some form of broken Japanese demon mask. Palette: black,
> deep indigo, electric blue, cyan, pale cyan, dark red, electric red, acid green,
> white, grey. No other colors. No text.

---

## 5-fix — Re-run of #5 (ATTACH the original render — without it the designs re-roll)

> Recreate this exact image with two corrections only. Keep all four enemy
> designs IDENTICAL to the reference — the same coiled segmented worm-serpent
> with the red-eyed goggled oni head, the same four-winged drone with the single
> cyan eye, the same hunched husk with the cracked white oni mask leaking green
> data, the same tall armored guardian with the red hannya mask on its shoulder
> and the green-edged axe. Same poses, same proportions, same details, same
> left-to-right order.
>
> Correction 1 — the background becomes PURE BLACK #000000.
> Correction 2 — palette compliance: shift every color to this exact set: black
> #000000, near-black #0A0E1F, deep indigo #1E33D9, electric blue #2B6FE8, cyan
> #35C6F4, pale cyan #8FE8FF, dark red #8F1116, electric red #E01F26, acid green
> #C6F02A, deep green #6B8A0F, white #FFFFFF, grey #4A5568. The husk's skin
> becomes near-black #0A0E1F with pale cyan #8FE8FF highlights — a dead process,
> not grey flesh.
>
> Change nothing else. Flat cel-shaded vector, bold linework, no text.

---

## Fixing bad output

| Problem | Say this |
|---|---|
| Colors drift warm / purple / muddy | "Use ONLY these hex colors: [paste]. No other colors at all." |
| Face shows through the mask | "The mask covers the ENTIRE face. Skin shows only at the neck, forearms, and hands." |
| Skin tone drifts light or grey | "He is a Black man with deep brown skin: shadow #4A2A1A, base #855434, highlight #B07A4A." |
| Horns point up | "The horns sweep BACKWARD behind the head, not upward." |
| Haori has sleeves | "The white haori is SLEEVELESS — bare armholes, the tracksuit sleeves show through." |
| Character changes between images | Attach the previous image. "Match this character exactly, only change the pose." |
| Looks 3D / painted / photoreal | "Flat cel-shaded vector illustration. Hard-edged flat color blocks. No gradients, no soft shading." |
| Swords on the wrong side | "Both scabbards on the LEFT hip, angled down and back." |
