# Food YouTube Studio — Product Blueprint

## Purpose

Build an AI-first production studio for an international, English-language food YouTube channel. The studio translates the publicly described stages of Alexander Orobeyko's YouTube Start methodology into software workflows, while adding automation for AI-generated food content.

This is an implementation blueprint, not a reproduction of proprietary course materials.

## Source methodology

The publicly listed course structure contains nine stages: introduction, niche selection, content plan, shooting preparation, production, editing, channel setup/packaging, upload/design, and monetization. Public 2026 communications also describe AI thumbnail workflows, an AI assistant, and large-scale culinary-channel analytics. These are treated as product requirements at the level of workflow concepts, not copied course content.

## Studio workflow

### 1. Channel Setup
Inputs:
- target country/language
- channel name
- audience
- visual identity
- publishing platforms

Outputs:
- channel profile
- About text
- visual kit
- default publishing settings
- content rules

Food defaults:
- English
- international audience
- Shorts-first
- 9:16
- no face
- no voice-over by default
- captions + cooking SFX

### 2. Niche Intelligence
The studio continuously evaluates:
- food sub-niches
- recurring formats
- rising topics
- ingredient trends
- competitor videos
- title patterns
- thumbnail patterns
- views-to-channel-size anomalies

Output:
- Trend Board
- Opportunity Score
- recommended experiments

### 3. Content Strategy
Generate a repeatable content system, not isolated ideas.

Core formats:
1. Luxury Transformation
2. One Ingredient → Multiple Recipes
3. Food Stories

Each format contains:
- hook formula
- story structure
- duration
- shot count
- caption style
- SFX profile
- CTA
- thumbnail formula

Output:
- 30-day content calendar
- experiment matrix
- backlog ranked by opportunity

### 4. Recipe / Concept Development
Input:
- ingredient, dish, trend, or concept

AI produces:
- concept
- recipe
- ingredient list
- steps
- timing
- visual payoff
- safety notes
- hook
- CTA

Recipe claims must be conservative and should not invent unsafe cooking instructions.

### 5. Storyboard-First Production
Every short begins as an 6–10 shot storyboard.

Each shot stores:
- shot number
- duration
- visual
- action
- camera
- lighting
- food state
- caption
- SFX
- image prompt
- video prompt
- continuity constraints

Workflow:
Draft → Review → Approve → Generate.

No expensive video generation before storyboard approval.

### 6. AI Production
Provider-neutral adapters for:
- image generation
- image-to-video
- text-to-video
- optional upscaling

Production rules:
- generate stills first where practical
- animate approved stills
- preserve ingredient/plate continuity
- prefer 1080p to control cost
- retry only failed shots
- never regenerate the whole project because one shot failed

### 7. Edit / Assembly
The studio creates an assembly plan:
- clip order
- trim points
- captions
- cooking SFX
- optional background music
- transitions
- end card

Default:
- voice-over OFF
- captions ON
- cooking SFX ON
- music low or OFF
- 9:16 / 1080x1920
- 25–30 seconds

### 8. Packaging / Publishing
Generate:
- title variants
- description
- hashtags
- thumbnail concepts
- thumbnail prompt
- pinned-comment prompt
- upload metadata

Packaging is evaluated against:
- curiosity
- clarity
- promise/payoff match
- audience fit

### 9. Analytics / Monetization
Track:
- views
- impressions
- CTR where available
- average view duration
- retention curve
- rewatches
- likes
- comments
- shares
- saves where available
- subscribers gained
- revenue when available

The system converts results into:
- winning format
- losing format
- hook lessons
- packaging lessons
- next experiments

Monetization layer:
- YouTube Partner Program readiness
- affiliate opportunities
- brand opportunities
- digital products later
- channel portfolio scaling later

## AI Studio dashboard

### Home
- Today's recommended video
- current experiment
- production queue
- failed jobs
- publishing queue
- channel health

### Trend Board
Columns:
- Trend
- Evidence
- Competition
- Opportunity
- Suggested format
- Score
- Action

### Content Lab
Controls:
- Format
- Ingredient
- Trend
- Duration
- Audience
- Generate ideas

### Storyboard
Visual 6–10 shot board with:
- approve shot
- regenerate shot
- lock continuity
- edit caption
- edit SFX
- generate image
- generate video

### Production Queue
States:
Idea → Script → Storyboard → Images → Video → Sound → Assembly → QA → Ready → Published

### Analytics
Compare:
- format
- hook
- ingredient
- title
- thumbnail
- duration
- retention

## Food-specific scoring

Every concept receives a 0–100 score:

- Hook strength: 20
- Visual transformation: 20
- Appetite appeal: 15
- Novelty: 15
- Retention potential: 15
- Repeatability: 10
- Production cost: 5

Opportunity Score is not a prediction of views. It is a prioritization score for experiments.

## Core data entities

Channel
- identity
- audience
- language
- platforms
- brand kit

Trend
- source
- topic
- evidence
- score
- detected_at

ContentIdea
- format
- hook
- concept
- ingredient
- score
- status

Recipe
- ingredients
- quantities
- steps
- timings
- safety_notes

Storyboard
- duration
- aspect_ratio
- shots
- approval_status

Shot
- duration
- visual_prompt
- video_prompt
- caption
- sfx_prompt
- continuity_key
- generation_status

Asset
- provider
- model
- prompt
- cost
- source
- status

VideoProject
- channel
- idea
- storyboard
- assets
- assembly
- packaging
- publish_status

AnalyticsSnapshot
- video
- timestamp
- metrics
- derived_insights

## Cost-control rules

1. Plan before generating.
2. Generate one representative shot before batch generation when a new style is introduced.
3. Reuse approved references.
4. Prefer image-to-video when it is cheaper and more stable.
5. Use 1080p by default.
6. Retry only failed assets.
7. Keep provider adapters interchangeable.
8. Record estimated and actual generation cost per asset.
9. Never spend credits on a shot that has not passed storyboard approval.

## First implementation order

P0:
1. Food channel configuration
2. Format templates
3. Storyboard data model
4. Storyboard UI
5. Caption + SFX fields
6. Production queue

P1:
7. Trend Board
8. Opportunity scoring
9. Recipe generator
10. Image/video provider adapters
11. Assembly export

P2:
12. YouTube publishing
13. Analytics ingestion
14. Experiment learning loop
15. Monetization dashboard

## Definition of done for the first usable Food Studio

A user should be able to:

1. choose a food format;
2. enter one ingredient;
3. receive several concepts;
4. choose one;
5. generate and approve a storyboard;
6. generate image prompts and video prompts;
7. generate only the approved shots;
8. receive captions and cooking-SFX instructions;
9. assemble a 9:16 Short;
10. generate title, description and thumbnail prompt;
11. mark the video published;
12. later record performance and feed the result into the next idea ranking.

## Product principle

The user should make creative decisions; the Studio should remove repetitive production work.

The target interaction is:

**Choose → Approve → Generate → Review → Publish → Learn.**
