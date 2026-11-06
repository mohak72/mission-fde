"""10 hand-labeled test cases for AC3's retrieval accuracy requirement.

Each case is a synthetic simulated-Prometheus-alert payload (matching the
shape of `AlertPayload`) paired with the runbook id a competent on-call
engineer would expect retrieval to surface. Plain Python data, not a
pytest fixture dependency, per Test Strategy's fixture conventions.
"""

RETRIEVAL_TEST_CASES: list[dict] = [
    {
        "expected_runbook_id": "pod-crashloop-oom",
        "labels": {
            "alertname": "KubePodCrashLooping",
            "namespace": "payments",
            "pod": "checkout-7f9c-abc12",
            "severity": "critical",
        },
        "annotations": {
            "summary": "Pod checkout-7f9c-abc12 is crash looping",
            "description": (
                "Container checkout was OOMKilled, exit code 137, memory limit exceeded"
            ),
        },
    },
    {
        "expected_runbook_id": "pod-crashloop-liveness-probe-failure",
        "labels": {"alertname": "KubePodCrashLooping", "pod": "auth-6d4f-xyz89"},
        "annotations": {
            "summary": "Pod auth-6d4f-xyz89 crash looping",
            "description": (
                "Liveness probe failed: HTTP probe to /healthz returned connection refused, "
                "container killed and restarted"
            ),
        },
    },
    {
        "expected_runbook_id": "image-pull-backoff",
        "labels": {"alertname": "KubePodNotReady", "pod": "worker-5b2e-def34"},
        "annotations": {
            "summary": "Pod worker-5b2e-def34 stuck in ImagePullBackOff",
            "description": (
                "Failed to pull image myregistry/worker:v2.3.1: manifest unknown, unauthorized"
            ),
        },
    },
    {
        "expected_runbook_id": "pvc-pending-unbound",
        "labels": {"alertname": "KubePersistentVolumeClaimPending", "pvc": "data-store-0"},
        "annotations": {
            "summary": "PVC data-store-0 stuck Pending",
            "description": (
                "PersistentVolumeClaim has been pending for over 15 minutes, no persistent "
                "volumes available for this claim"
            ),
        },
    },
    {
        "expected_runbook_id": "node-not-ready",
        "labels": {"alertname": "KubeNodeNotReady", "node": "ip-10-0-3-212"},
        "annotations": {
            "summary": "Node ip-10-0-3-212 is NotReady",
            "description": (
                "Node has been in NotReady state for more than 5 minutes, kubelet not "
                "reporting status"
            ),
        },
    },
    {
        "expected_runbook_id": "dns-resolution-failure",
        "labels": {"alertname": "CoreDNSResolutionErrors", "namespace": "checkout"},
        "annotations": {
            "summary": "DNS resolution failures spiking",
            "description": (
                "Application logs show could not resolve host errors calling internal "
                "service, CoreDNS pods showing high latency"
            ),
        },
    },
    {
        "expected_runbook_id": "hpa-not-scaling",
        "labels": {"alertname": "KubeHpaMaxedOut", "hpa": "api-gateway"},
        "annotations": {
            "summary": "HPA api-gateway not scaling under load",
            "description": (
                "HorizontalPodAutoscaler unable to fetch metrics, missing resource requests "
                "for cpu on target deployment"
            ),
        },
    },
    {
        "expected_runbook_id": "certificate-expiry",
        "labels": {"alertname": "CertificateExpiringSoon", "ingress": "public-api"},
        "annotations": {
            "summary": "TLS certificate for public-api has expired",
            "description": (
                "Clients receiving certificate has expired errors, cert-manager renewal "
                "appears stalled"
            ),
        },
    },
    {
        "expected_runbook_id": "disk-pressure-eviction",
        "labels": {"alertname": "KubeNodeDiskPressure", "node": "ip-10-0-4-88"},
        "annotations": {
            "summary": "Node ip-10-0-4-88 under disk pressure",
            "description": (
                "Pods being evicted due to DiskPressure condition, node ephemeral-storage "
                "nearly full"
            ),
        },
    },
    {
        "expected_runbook_id": "service-endpoint-mismatch",
        "labels": {"alertname": "KubeServiceNoEndpoints", "service": "billing-svc"},
        "annotations": {
            "summary": "Service billing-svc has no endpoints",
            "description": (
                "Clients calling billing-svc get connection refused, selector does not match "
                "any running pod labels"
            ),
        },
    },
]
