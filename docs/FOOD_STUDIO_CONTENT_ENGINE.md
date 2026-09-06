# Food Studio Content Engine

## Publishing model
- Shorts: 20–40 seconds, discovery and repeatable formats.
- Long-form: 6–12 minutes initially, depth, search, session time and monetization.
- Default cadence: 5 Shorts/week + 2 Long-form/week; configurable per channel.

## Content repurposing
A Long-form project can generate a content package of one full recipe/story plus native derivative Shorts. Shorts get independent hooks and pacing and should not simply be stretched or clipped copies.

## Long-form workflow
Idea → Research → Recipe validation → Outline → Storyboard → Asset plan → Generation → Assembly → Captions/SFX → QA → Packaging → Publish → Analytics

Defaults: 16:9, 6–12 minutes, English, voice-over optional, captions ON, cooking SFX ON, music optional, chapters when useful.

## Long-form formats
1. 5 Recipes With One Ingredient
2. Viral Recipe Test
3. Budget vs Luxury
4. Complete Recipe Guide
5. Food Story
6. Food Challenge / Experiment
7. Ingredient Deep Dive

## Shorts formats
1. Luxury Transformation
2. One Ingredient → Multiple Recipes
3. Food Stories

## Cross-format planning
Every idea stores a primary format, derivative opportunities, production reuse score, effort and packaging variants.
Example: 5 Banana Desserts → one Long + five native Shorts, one for each dessert.

## Data model additions
ContentProject: content_type (short|long), parent_project_id, derivative_projects, target_duration, aspect_ratio, publishing_date.
ContentPackage: primary_project, derivative_projects, shared_assets, shared_recipe, shared_brand_rules.
LongFormOutline: hook, promise, sections, recipe_steps, tips, payoff, CTA, chapters.

## Production queue
Idea → Research → Recipe → Outline → Storyboard → Images → Video → Sound → Assembly → QA → Packaging → Scheduled → Published → Analytics.
Each stage supports retrying only failed items.

## Product requirement
The user can create one Long-form project and ask Studio to propose derivative Shorts without unnecessary asset regeneration. Reuse approved references, recipe data, continuity and provider-cost optimizations.

## Updated priority
P0: content type abstraction; food format templates; storyboard engine for 9:16 and 16:9; recipe model; production queue; captions + SFX.
P1: long-form outline generator; content package/derivative Shorts; Trend Board; provider adapters; assembly/export.
P2: YouTube publishing; analytics; experiment learning loop; monetization dashboard.