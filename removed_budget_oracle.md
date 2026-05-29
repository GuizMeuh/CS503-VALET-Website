# Removed: Budget-Limited Oracle Content

Stripped from `index.html` on 2026-05-29. Re-add when results are ready.

---

## Sokoban section subsection (was after the Transfer Results block)

```html
            <!-- Budget oracle -->
            <h4 class="title is-5 mt-5">Budget-Limited Oracle</h4>
            <p>
              As an exploratory extension, we investigate a budget-constrained variant in which
              the agent is allowed at most \(B\) oracle queries per episode. The remaining budget
              is communicated via a spatially-constant 4th input channel, encoded as
              \(\lfloor(\text{remaining}/B)\times 255\rfloor\), so the CNN can condition its
              querying decisions on how much of its allowance remains (see the architecture
              diagram in Section III-A). These 4-channel checkpoints are not compatible with
              the standard 3-channel weights; full quantitative results for this variant are
              deferred to future work.
            </p>
```

---

## CNN diagram caption sentence (was in the Architecture figure caption, Method §A)

```
For the budget-aware variant the input carries a 4th channel encoding remaining query budget.
```

Full original caption for reference:

```html
              <p class="mt-2" style="font-size:0.82em; color:#555;">
                <strong>Architecture.</strong> Shared CNN encoder used for DoorKey-16×16 (partial obs)
                and all Sokoban experiments (56×56×3 RGB input, normalised to [0,1]). The first conv
                downsamples spatially (stride 2); adaptive pooling normalises the feature map to
                64×8×8 = 4096 before the shared FC layer. Policy and value heads use orthogonal
                initialisation (std=0.01 and 1.0 respectively). For the budget-aware variant the
                input carries a 4th channel encoding remaining query budget. For DoorKey-8×8
                (full obs, 40×40×3) the pool is omitted and the flatten projects directly to 256.
              </p>
```

---

## Context from ARCHITECTURES.md

```
### Budget-aware policy (4-channel, --max-oracle-queries runs)

Identical to above except the first conv takes 4 input channels:

Input: 56x56x4  (RGB + budget channel)
Conv2d(4, 32, kernel=3, stride=2, padding=1)
... remainder identical ...

The 4th channel encodes remaining query budget as a spatially-constant
uint8 value: int((queries_remaining / max_queries) * 255).
These checkpoints are incompatible with 3-channel checkpoints.
```
