# Family Deals UX Baseline

Status: Approved product direction
Date: September 4, 2026

## Rule

Universal Watcher must preserve the existing Family Deals capabilities and improve presentation around them rather than simplifying away working functionality.

## Search flow

The V1 Family Deals screen should preserve these primary controls:

1. Location (city, ZIP, address, or current location)
2. Search radius
3. Party size / people to feed
4. Maximum total budget
5. Cuisine multi-select
6. Restaurant type
   - Any
   - Independent + local
   - Independent only
   - Chains only
7. Find Family Deals

The UI should remain simple while the existing engine keeps the complex behavior underneath, including full-radius discovery, conservative chain classification, strict offer/price verification, family-size logic, event/birthday-package rejection, caching, concurrency, and source evidence.

## Results baseline

Results should be deal-first rather than restaurant-first.

Each result should prioritize:

- restaurant name
- cuisine
- restaurant classification
- distance
- deal name
- verified total price
- servings / party-size coverage
- included items when known
- verification state
- direct View Deal action

Verified matches should be prioritized. Uncertain or partially verified results must be clearly labeled rather than mixed into verified matches as if equally trustworthy.

Initial sort behavior should favor the strongest verified match / best value, with future optional sorts for price, distance, and number served.

## Hard rule

Do not reintroduce an arbitrary top-N restaurant limit for speed. Search coverage remains a product requirement.
