---
name: host-swarm
description: How flow's review-host operations (fetch-review, open-draft, ready-for-review) run on Helix Swarm for a Perforce workspace. Swarm has no issues, so there is no fetch-issue. Load when a flow phase or deep-review names one of these operations and the p4 server has a Swarm URL.
user-invocable: false
---

Swarm reviews Perforce changelists. Changelist, shelve, and submit steps
belong to `vcs-perforce`. Swarm has no issue tracker: issue references fall
back to a connected tracker tool, or to asking for the text.

## Detect

Use this skill when `p4 property -l -n P4.Swarm.URL` prints a URL. That URL
is `<swarm>` below.

## API access

Find the API version from `<swarm>/api/version` and use the newest it
lists. Authenticate as the p4 user with their ticket for this server.
Never run `p4 tickets` on its own: it prints every ticket. Instead build
the curl config inside one pipeline, from `p4 tickets` through a filter to
`curl -K -`, so the ticket reaches curl's stdin and never your output or
the command line. If the user isn't logged
in (`p4 login -s` fails), ask them to run `p4 login`; never ask for a
password.

## fetch-review

`GET <swarm>/api/<version>/reviews/<id>`. From the response:

- **state** (`needsReview`, `needsRevision`, `approved`, `rejected`,
  `archived`) and the description, for intent.
- **Completed review** (it has `commits`): the submitted changelists in
  `commits`, oldest first.
- **Open review:** the shelved changelist of the latest entry in
  `versions`.

Report the review URL, `<swarm>/reviews/<id>`.

## open-draft

Swarm has no drafts, and a new review notifies its reviewers. So leave the
work as a shelved changelist and report its number. Don't add `#review` yet.

## ready-for-review

Add `#review` (or the repo's own keyword, if its docs name one) to the work
changelist's description. In stream mode that's the shelved copy-up
changelist from `vcs-perforce`'s `publish`. Then shelve it again
(`p4 shelve -f -c <cl>`); Swarm opens the review. Later shelves update it.
Find its ID with `GET <swarm>/api/<version>/reviews?change[]=<cl>` and
report `<swarm>/reviews/<id>`.

Never approve or commit the review yourself.
