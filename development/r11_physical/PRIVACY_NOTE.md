# Controlled-printer identity privacy note

The R11 Gate A-left v2 control overlay intentionally publishes a SHA-256 hash
of the approved printer identifier. It does **not** publish the raw printer
serial, account credentials, network address, access token, or pairing secret.

The public hash is a stable device fingerprint. It is retained because the
current frozen control contract uses it to fail closed when an attempt targets
a different physical printer. Removing or replacing that value would change a
safety boundary and requires a separately reviewed, explicitly authorized new
overlay version. It must not be silently edited out of v2.

Privacy tradeoff accepted by the current evidence design:

- benefit: an attempt can be checked against the exact approved printer
  without publishing the raw serial;
- limitation: observers can correlate repositories or records that publish
  the same one-way hash;
- boundary: the hash is an identifier, not a credential and not a means to
  connect to or control the printer;
- future improvement: a newly versioned overlay may use a project-specific
  salted commitment plus a private external identity ledger, provided the
  approved physical printer remains unchanged and the migration receives
  explicit review and authorization.

This note changes no permit, print, installation, or load authorization.
