# Wisely — Design & Architecture

This document is the "what and why." For "how to run it," see [backend/README.md](../backend/README.md).

## What Wisely is

Wisely is a **book-review site where only clinicians (therapists) can post reviews** —
"Letterboxd, but the reviewers are licensed mental-health professionals." The public,
low-friction surface is book reviews; the real product underneath is a **clinician
directory**. Books are the acquisition funnel (they get clinicians on the platform sharing
opinions, and give seekers a reason to browse), and seekers are gently guided from "I like
this clinician's taste in books" toward "I'd like this clinician."

Two audiences:
- **Clinicians** — licensed professionals who write reviews and are discoverable. The content creators / "critics."
- **Seekers** — everyone else: they read reviews, follow clinicians, and bookmark books. The audience / future leads.

## Product principles

1. **PHI-free by design.** Seekers store only optional demographics + saved books + the
   clinicians they follow. We deliberately do **not** collect self-disclosed clinical
   concerns, diagnoses, or symptoms, which keeps Wisely clear of HIPAA. (This is why there's
   no "presenting concern" field; book saves are the arms-length interest signal instead.)
2. **Books are the funnel, the directory is the product.** Features should reinforce the
   path from book engagement → clinician discovery.
3. **Affinity, not clinical outcomes** (see Matching below).

## Architecture

- **Django 5.1 + Django REST Framework**, **PostgreSQL**, dependencies via **uv**, containerized with **Docker Compose**.
- Project: `wisely_api/`. Apps live beside the settings package.

| App | Owns | Notes |
|-----|------|-------|
| `core` | `User` (custom auth), `Category`, shared `choices` (e.g. `STATE_CHOICES`) | `User.user_type` ∈ clinician/seeker/business_admin; social follow graph exposed as `user.following` / `user.followers` |
| `books` | `Book`, `Review` | Book metadata from Google Books; `Review` is a clinician's "critic" review. Hosts the books API + affiliate buy-redirect |
| `clinicians` | `Clinician`, `License`, `ClinicianLicense`, `ClinicianSpecialty` | A clinician profile (bio + video bio), state licensure, specialties |
| `seekers` | `Seeker` | Thin, PHI-free profile |
| `engagement` | `Follow`, `SavedBook`, `Event` | Social graph + bookmarks + append-only clickstream |

Cross-app relations use string references (`'clinicians.Clinician'`, `'books.Book'`, `'core.Category'`) to avoid import cycles.

## Data model highlights

- **`core.User`** — custom user. `following` is a self-referential M2M *through* `engagement.Follow` (`symmetrical=False`), giving `user.following` (people they follow) and `user.followers`.
- **`core.Category`** — a single taxonomy shared by **book topics** (`Book.categories`) and **clinician specialties** (`ClinicianSpecialty.category`) and **seeker interests** (`Seeker.interests`). This shared taxonomy is the seam that lets us connect a seeker's book tastes to relevant clinicians.
- **`books.Book`** — title/subtitle/author/description/page_count/etc. from Google Books, plus `isbn`/`isbn_10`, cover fields, and the **audience** rating (`google_average_rating`/`google_ratings_count`).
- **`books.Review`** — a clinician's review (rating 1–5 + text). The **critic** side.
- **Audience vs critic scores** (Rotten-Tomatoes style): `Book.audience_score` (Google aggregate) vs `Book.critic_score` (clinician review average), both normalized to 0–100.
- **`clinicians.Clinician`** — `bio` (text) + `video_bio_url`, `is_active`, `has_openings`, contact fields. `ClinicianLicense` ties a `License` type to an `issued_state`.
- **`seekers.Seeker`** — `user`, optional `birthdate`/`state`, `interests` (Category M2M, grows as they browse), `saved_books` (through `engagement.SavedBook`). Following clinicians happens via the `Follow` graph, not a field here.

## Engagement & analytics

Two layers, because they answer different questions:

- **State** — the current truth: `Follow` (who follows whom) and `SavedBook` (what a seeker has bookmarked, with `via_review` recording which review drove the save). These power features.
- **Log** — `Event`, an append-only clickstream. Every impression/click/action is a row (`event_type`, optional `actor`/`session_id`, nullable target FKs to book/clinician/review, a `source_review` for attribution, `provider`, and a `metadata` JSON). This is what makes **click-through and conversion funnels** possible — a "viewed a review but didn't follow" only exists in the log.

Typical funnel: `review_viewed → review_clicked → clinician_viewed → clinician_followed → affiliate_clicked`. Conversion between steps = `count(sessions reaching N+1) / count(sessions reaching N)`; attribution stitches via `session_id` and/or the explicit `source_review`.

Postgres is the right home for now. Expect to offload the clickstream to a warehouse / product-analytics tool once volume grows; keep `Event` append-only.

## Monetization

Affiliate book links fund the platform:
- **Bookshop.org** and **Amazon Associates**, generated from each book's ISBN + account tags (`BOOKSHOP_AFFILIATE_ID`, `AMAZON_ASSOCIATE_TAG`) — so every imported book gets buy-links automatically.
- Clicks are tracked via a **redirect endpoint** (`GET /api/books/{id}/buy/?provider=…`) that logs an `affiliate_clicked` event, then 302s to the retailer.
- The per-user funnel ends at the click; **actual purchases are reported by the retailers' dashboards in aggregate** (they don't report per-user). An FTC affiliate disclosure belongs in the UI.

## Matching / ML direction

Because we stay PHI-free, there are **no clinical labels** (no WAI alliance scores, no PHQ-9
outcomes). So the realistic, defensible target is **affinity / engagement** — collaborative
filtering on book + review taste and follow/save/click behavior ("seekers who followed these
clinicians also saved these books"). The clinician's *review text* is a proxy for their voice
and values, which is Wisely's distinctive signal vs a checkbox directory.

Predicting validated **therapeutic alliance** would require clinical measures = PHI = HIPAA,
and would have to be a separate, consented, compliance-walled module. Out of scope for now.

## Key design decisions

- **"Saved/influencer clinicians" is modeled as a follow graph**, not a separate `SavedClinician` table. Following a clinician *is* the influencer relationship, and it matches Letterboxd/Instagram (you **follow people** and **save content**). Books are saved; clinicians are followed.
- **One `engagement` app** holds follows, saves, and events — named for the domain ("how users engage") rather than "analytics," since it includes social relationships, not just metrics.
- **Shared `Category` taxonomy** across books, specialties, and seeker interests (the matching seam).
- **Generated affiliate links** (from ISBN) rather than per-book stored URLs.

## Authentication

**django-allauth + dj-rest-auth**, issuing **JWTs** (simplejwt) in the response body for the
React/Next.js and mobile clients. Username/password **and** Google social login. Endpoints
under `/api/auth/` (login, logout, registration, user, token refresh, `google/`). DRF defaults
to `IsAuthenticatedOrReadOnly` — public reads, authenticated writes. Google credentials and the
Site domain are configured via env / the admin.

Email verification is **mandatory**: users must confirm their address before they can log in
(Google accounts arrive pre-verified, so they're unaffected), which makes email required at
signup. Dev prints confirmation emails to the console; production configures SMTP via env.

## Not yet built (roadmap)

- **Engagement write endpoints**: follow/unfollow, save/unsave, and event ingestion from the frontend (now unblocked by auth).
- **Clinicians & seekers APIs** (profiles, search/filter by specialty/state) — apps are reserved at `/api/clinicians/`, `/api/seekers/`.
- **Review authoring endpoint** for clinicians.
- Clickstream offload to an analytics store once volume warrants.
