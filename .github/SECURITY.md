# Security policy

Please report vulnerabilities privately through GitHub Security Advisories
when available.

Do not include credentials, proprietary Unity assets or private project paths
in a report. A minimal synthetic fixture is preferred.

The most security-sensitive areas are:

- path containment during materialization, apply and rollback;
- approval-ID and content-hash verification;
- archive and Theme Pack ingestion;
- accidental source mutation during read-only indexing;
- credentials or absolute paths leaking into exported context.
