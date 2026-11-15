# Challenges log

Add real problems as you hit them: date, who, what happened, what fixed it.

## 2026-11-15 — Knowledge base content (ticket #6)

- **NHS page layout changed.** Most medicines are now one page with sections ("What metformin is for", "How to take metformin", …), not one page per topic. Ramipril and salbutamol inhaler still use the older layout (About, How and when to take, Side effects, Who can and cannot, Pregnancy, With other medicines, Common questions). We kept each page's own NHS heading names, so chunk ids differ between the two layouts (e.g. `metformin#how-to-take-metformin` vs `ramipril#how-and-when-to-take-ramipril`).
- **Licence check.** Each page shows only "© Crown copyright". The NHS website terms (nhs.uk/our-policies/terms-and-conditions/) release NHS website content under the Open Government Licence v3.0 except items on the "content not licensed for re-use" page. That page excludes only some campaign sites (Change4Life, One You, Smokefree, …) and some images and videos, none of which we use. No BNF text is on these pages. No medicine was dropped.
- **Refresh rule.** The terms ask re-users to refresh content at least every 7 days. All 12 leaflets were retrieved on 2026-11-15; re-collect them before the final demo or submission if more than 7 days have passed.
- **Interaction table scope.** Rows only where a leaflet's "with other medicines" section names both medicines. Class-only mentions ("other blood pressure medicines", "medicines for diabetes") were not turned into pairs. Ramipril + aspirin was left out on purpose: the ramipril leaflet says daily low-dose aspirin (75mg) is safe with ramipril, so a blanket warning would be wrong for most older users on low-dose aspirin.
