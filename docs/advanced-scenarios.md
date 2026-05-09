# Sprint 8 Advanced Scenarios / İleri Senaryolar

This document summarizes Sprint 8 backend improvements for advanced scenarios / ileri senaryolar, error taxonomy / hata sınıflandırması, and validation checks / doğrulama kontrolleri.

## Goal

Sprint 8 focuses on making hard difficulty labs more realistic without breaking the stable MVP flow.

The priority is:

1. Better hard scenarios / daha iyi zor senaryolar
2. Richer validation checks / daha detaylı doğrulama kontrolleri
3. Stable scoring / puanlama
4. Recommendation and analytics compatibility / öneri ve analitik uyumluluğu
5. Keeping CLI access stable with docker exec local demo mode / yerel demo modu

## Error taxonomy / Hata sınıflandırması

Sprint 8 uses these canonical topics:

- ip_addressing
- subnetting
- interface_status
- default_gateway
- static_routing
- vlan_like
- acl_like
- connectivity

These topics are used by:

- error injection / hata enjeksiyonu
- validation checks / doğrulama kontrolleri
- scoring / puanlama
- recommendation module / öneri modülü
- instructor analytics / eğitmen analitiği

## Hard difficulty / Zor seviye

Hard difficulty still injects five errors, but Sprint 8 improves the selection logic.

Instead of randomly selecting five errors that may belong to the same topic, the backend now tries to select diverse topics. This creates a more analytical troubleshooting experience.

Example hard topics may include:

- static_routing
- default_gateway
- subnetting
- connectivity
- interface_status

## Validation check format / Doğrulama kontrol formatı

Each validation check now includes:

```json
{
  "check_id": "check_1_static_routing",
  "topic": "static_routing",
  "description": "Validate whether Static Routing related configuration state is correct on r3.",
  "status": "failed",
  "passed": false,
  "points": 0,
  "max_points": 20,
  "message": "Static Routing validation failed on r3. The related issue still appears unresolved.",
  "hint": "Review static route destination networks and next-hop addresses.",
  "evidence": {
    "validation_mode": "config_marker_check",
    "device": "r3",
    "config_file": "r3.conf",
    "config_file_present": true,
    "observed_state": "issue marker is still present"
  }
}
```

## Runtime validation / Çalışma zamanı doğrulama

Sprint 8 keeps validation stable by preserving config-marker validation.

Current validation mode:

- Reads injected error metadata.
- Reads generated device config files.
- Checks whether the injected error marker is still present.
- Calculates points based on severity and passed checks.

This is intentionally stable and mockable in tests.

Possible future runtime validation improvements:

- docker exec based `ip addr` checks
- docker exec based `ip route` checks
- container inspect state checks
- ping/connectivity checks between running containers

These are future work because they require the lab runtime to be deployed and healthy during validation.

## Out of scope / Kapsam dışı

Sprint 8 does not implement:

- OSPF/BGP scenarios
- vendor-specific network OS integration
- production browser terminal
- production SSH gateway
- full runtime state validation dependency

These items are documented as future work to protect demo stability.
