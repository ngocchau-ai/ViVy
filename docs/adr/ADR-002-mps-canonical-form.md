# ADR-002: MPS Canonical Form

**Status:** Accepted (implemented in core/mps.py)

## Context
Matrix Product States need a canonical form to enable efficient gate application,
norm computation, and truncation. The orthogonality center defines which tensor
carries the norm.

## Decision
- `canonical_form(target_center=k)` brings the MPS into mixed-canonical form
  centered at site k
- Sites 0..k-1 are left-canonical (isometric from left bond to physical+right)
- Sites k+1..n-1 are right-canonical (isometric from right bond to physical+left)
- `_center = -1` means "not canonical" — norm falls back to full contraction
- Default center on init is 0 (left-canonical)

## Consequences
- `apply_gate` canonicalizes to the first target qubit before contracting
- Norm is O(χ²) when canonical, O(n·χ³) when not
- `canonicalize=False` on init skips the sweep for speed