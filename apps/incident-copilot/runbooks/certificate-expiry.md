# TLS Certificate Expired (Ingress / cert-manager)

## Symptoms

- Clients see TLS/SSL errors in browsers or via `curl`: `certificate has expired`, `NET::ERR_CERT_DATE_INVALID`, or similar.
- `openssl s_client -connect <host>:443` shows a `notAfter` date in the past.
- If using `cert-manager`, `kubectl get certificate` shows the certificate's `READY` column as `False`, or `kubectl describe certificate` shows a stalled/failed renewal.
- Traffic to the affected ingress/service drops sharply as clients refuse the connection outright.

## Likely Causes

- `cert-manager`'s automatic renewal failed silently (e.g., the ACME challenge couldn't complete due to a DNS or HTTP-01 challenge misconfiguration).
- The certificate issuer (`ClusterIssuer`/`Issuer`) itself is misconfigured or its credentials (e.g., a DNS provider API key for DNS-01 challenges) expired.
- Rate limiting from the certificate authority (e.g., Let's Encrypt) blocked a renewal attempt after too many retries.
- A manually-managed (non-cert-manager) certificate was simply never rotated before expiry — a process gap, not a tooling failure.

## Diagnosis Steps

1. `openssl s_client -connect <host>:443 -servername <host> </dev/null 2>/dev/null | openssl x509 -noout -dates` — confirm the actual expiry date being served.
2. `kubectl describe certificate <name>` — if using cert-manager, read the Conditions/Events for the specific renewal failure reason.
3. `kubectl describe certificaterequest` and `kubectl describe order`/`challenge` (cert-manager CRDs) to trace exactly where the ACME flow stalled.
4. Check the issuer's credentials (DNS provider API key, etc.) haven't themselves expired or been revoked.
5. Check the certificate authority's own status page for active rate-limiting or outages.

## Resolution

- Challenge misconfiguration: fix the DNS-01/HTTP-01 challenge setup (correct DNS zone delegation, or correct ingress routing for the HTTP-01 solver path) and trigger a manual renewal.
- Issuer credentials expired: rotate the credential in the `Issuer`/`ClusterIssuer` secret, then retry.
- Rate limited: wait out the rate-limit window (CA-specific) before retrying; consider switching to a staging issuer for testing to avoid burning production rate limits.
- Manual process gap: migrate to `cert-manager` (or equivalent automated renewal) so this class of incident stops being a manual tracking problem.
- Immediate mitigation while fixing root cause: if available, temporarily serve a short-lived manually-issued certificate to restore service while the automated path is fixed.
