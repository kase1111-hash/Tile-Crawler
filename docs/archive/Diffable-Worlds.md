# Diffable Worlds

## DLP‑Native State Mutation Specification (v0.1)

---

### Purpose

Define a **hardware–software contract** for symbolic worlds where change—not frames—is the unit of computation. This spec formalizes how Digital Language Processors (DLPs) read, reason, and write world state using **glyph grids, legends, and diffs**.

---

## 1. World Model

### 1.1 Glyph Grid (VRAM)

A world is a fixed-size or streaming 2D grid of glyph IDs.

```json
{
  "size": [W, H],
  "layers": {
    "terrain": [["G001","G001"], ...],
    "entities": [["E010", null], ...],
    "fx": [[null, null], ...]
  }
}
```

**Rules**

* Layers are orthogonal; no blending.
* Empty cells are `null`.
* Glyph IDs are opaque tokens.

---

### 1.2 Glyph Legend (ISA)

The legend maps glyph IDs to semantics.

```json
{
  "G001": {"name":"stone wall","solid":true},
  "T004": {"name":"floor","walkable":true},
  "E010": {"name":"player","agent":true}
}
```

**Invariant**: The legend is immutable during a tick.

---

## 2. Tick Model

A **tick** is an atomic transaction:

```
Perception → Intent → Validation → Diff Commit → Broadcast
```

No partial frames. No redraws.

---

## 3. Perception Window (Cache Line)

DLPs operate on a bounded window.

```json
{
  "center": [x,y],
  "radius": r,
  "layers": ["terrain","entities"]
}
```

**Properties**

* Deterministic slicing
* No hidden pixels
* Symbol-budget bounded

---

## 4. Intent Bus

DLPs emit **intent**, never diffs.

```json
{
  "intent": "move",
  "actor": "E010",
  "vector": [1,0]
}
```

Other examples:

* `interact.open`
* `attack.melee`
* `audio.footstep`

---

## 5. Diff Primitives (Write‑Back)

Diffs are the only write operation.

### 5.1 Cell Replace

```json
{
  "op": "replace",
  "layer": "entities",
  "pos": [x,y],
  "from": "E010",
  "to": null
}
```

### 5.2 Cell Insert

```json
{
  "op": "insert",
  "layer": "entities",
  "pos": [x,y],
  "glyph": "E010"
}
```

### 5.3 Batch Diff

```json
{
  "tick": 1842,
  "diffs": [ ... ]
}
```

**Guarantees**

* Order-independent within layer
* Reversible
* Loggable

---

## 6. Validation Layer (Physics Without Physics)

Before commit, diffs are validated against legend constraints.

```json
{
  "rule": "no_overlap",
  "if": {"solid": true},
  "then": "reject"
}
```

This replaces:

* collision engines
* navmeshes
* raycasts

---

## 7. Commit Semantics

All diffs in a tick:

* succeed together
* or fail together

This enables:

* rollback
* replay
* determinism

---

## 8. Broadcast Channels

After commit, diffs are broadcast to:

* Renderer (font → screen)
* Audio Engine (intent → DSP)
* Narrative Memory (fact extraction)
* Observers (logging / multiplayer)

---

## 9. Performance Model

* **O(d)** per tick where *d* = number of diffs
* Zero cost for unchanged cells
* Linear token cost

---

## 10. Interop

Legacy engines may:

* mirror glyph grids
* ignore legend
* treat diffs as draw calls

DLP-native engines treat diffs as **state truth**.

---

## 11. Why This Replaces Frames

Frames redraw reality.
Diffs **describe causality**.

DLPs compute causality.

---

## 12. Status

This spec is intentionally minimal.
It is designed to be:

* language-agnostic
* engine-agnostic
* hardware-forward

Future versions may add:

* 3D glyph volumes
* temporal glyphs
* probabilistic diffs

---

**Diffable Worlds are not an optimization.**
They are a different contract.

Frames are for pixels.
Diffs are for meaning.
