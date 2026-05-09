# AutoNetLab API Contracts

This document defines the REST/HTTP JSON API contracts between the AutoNetLab Backend API and the Web Dashboard frontend.

Bu dosya, AutoNetLab Backend API ile Web Dashboard frontend arasÄ±ndaki REST/HTTP JSON sÃ¶zleÅŸmelerini tanÄ±mlar.

---

## Base URL

```text
http://127.0.0.1:8000/api/v1
```

Local development / yerel geliÅŸtirme sÄ±rasÄ±nda backend bu adres Ã¼zerinden Ã§alÄ±ÅŸacaktÄ±r.

---

# 1. Health Check

Health Check endpoint/uÃ§ noktasÄ± backend servisinin Ã§alÄ±ÅŸÄ±p Ã§alÄ±ÅŸmadÄ±ÄŸÄ±nÄ± kontrol etmek iÃ§in kullanÄ±lÄ±r.

Bu endpoint genellikle frontend tarafÄ±ndan da kullanÄ±labilir ama asÄ±l amacÄ± geliÅŸtirme sÄ±rasÄ±nda backend ayakta mÄ± diye hÄ±zlÄ± kontrol yapmaktÄ±r.

## Request

```http
GET /health
```

## Full URL

```text
http://127.0.0.1:8000/api/v1/health
```

## Response

```json
{
  "status": "ok",
  "service": "AutoNetLab Backend API"
}
```

## Meaning

```text
status = ok
```

Backend API Ã§alÄ±ÅŸÄ±yor demektir.

---

# 2. Get Difficulty Levels

Bu endpoint/uÃ§ nokta frontendâ€™e kullanÄ±labilir zorluk seviyelerini dÃ¶ner.

Muhammed bu response/cevap sayesinde ekranda ÅŸu seÃ§enekleri gÃ¶sterebilir:

- Easy
- Medium
- Hard

## Request

```http
GET /meta/difficulties
```

## Full URL

```text
http://127.0.0.1:8000/api/v1/meta/difficulties
```

## Response

```json
{
  "difficulties": [
    {
      "value": "easy",
      "label": "Easy",
      "description": "Two injected errors. Suitable for beginners."
    },
    {
      "value": "medium",
      "label": "Medium",
      "description": "Three injected errors. Suitable for intermediate users."
    },
    {
      "value": "hard",
      "label": "Hard",
      "description": "Five injected errors. Suitable for advanced users."
    }
  ]
}
```

---

# 3. Create Lab Session

Bu endpoint/uÃ§ nokta yeni bir lab session / laboratuvar oturumu oluÅŸturur.

Frontend kullanÄ±cÄ±nÄ±n seÃ§tiÄŸi zorluk seviyesini backendâ€™e gÃ¶nderir. Backend ise yeni bir session oluÅŸturur, topology/topoloji bilgisini Ã¼retir, injected errors/enjekte edilen hatalarÄ± belirler ve frontendâ€™e JSON olarak dÃ¶ner.

## Request

```http
POST /labs
```

## Full URL

```text
http://127.0.0.1:8000/api/v1/labs
```

## Request Body

```json
{
  "student_id": "kadir",
  "difficulty": "easy",
  "topology_template": "basic-two-router"
}
```

## Request Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| student_id | string | yes | Ã–ÄŸrenci kullanÄ±cÄ± adÄ± veya ID bilgisi |
| difficulty | string | yes | Lab zorluk seviyesi: easy, medium veya hard |
| topology_template | string | yes | KullanÄ±lacak topology/topoloji ÅŸablonu |

## Response

```json
{
  "session_id": "lab-abc12345",
  "student_id": "kadir",
  "difficulty": "easy",
  "status": "created",
  "topology": {
    "name": "basic-two-router",
    "nodes": [
      {
        "id": "r1",
        "label": "Router 1",
        "kind": "linux",
        "image": "alpine:latest",
        "mgmt_ipv4": null
      },
      {
        "id": "r2",
        "label": "Router 2",
        "kind": "linux",
        "image": "alpine:latest",
        "mgmt_ipv4": null
      }
    ],
    "links": [
      {
        "source": {
          "node": "r1",
          "interface": "eth1"
        },
        "target": {
          "node": "r2",
          "interface": "eth1"
        }
      }
    ]
  },
  "injected_errors": [
    {
      "code": "IP_ADDRESS_MISMATCH",
      "topic": "IP Addressing",
      "device": "r1",
      "description": "Incorrect IP address configured on r1 eth1.",
      "severity": "low"
    }
  ],
  "cli_access": [
    {
      "device_id": "r1",
      "command": "docker exec -it clab-autonetlab-r1 sh"
    },
    {
      "device_id": "r2",
      "command": "docker exec -it clab-autonetlab-r2 sh"
    }
  ],
  "message": "Lab session created successfully."
}
```

## Response Fields

| Field | Type | Description |
|---|---|---|
| session_id | string | OluÅŸturulan lab session/lab oturumu ID bilgisi |
| student_id | string | Ã–ÄŸrenci ID bilgisi |
| difficulty | string | SeÃ§ilen zorluk seviyesi |
| status | string | Session durumu |
| topology | object | Frontendâ€™in topology gÃ¶rselleÅŸtirmesi iÃ§in kullanacaÄŸÄ± veri |
| injected_errors | array | Sistemin lab iÃ§ine eklediÄŸi hatalar |
| cli_access | array | Ã–ÄŸrencinin CLI Ã¼zerinden baÄŸlanacaÄŸÄ± cihaz komutlarÄ± |
| message | string | KullanÄ±cÄ±ya gÃ¶sterilecek aÃ§Ä±klama mesajÄ± |

---

# 4. Get Lab Session

Bu endpoint/uÃ§ nokta daha Ã¶nce oluÅŸturulmuÅŸ bir lab session/lab oturumunu getirir.

Frontend, sayfa yenilendiÄŸinde veya session detayÄ±nÄ± gÃ¶stermek istediÄŸinde bu endpointâ€™i kullanabilir.

## Request

```http
GET /labs/{session_id}
```

## Example Full URL

```text
http://127.0.0.1:8000/api/v1/labs/lab-abc12345
```

## Response

```json
{
  "session_id": "lab-abc12345",
  "student_id": "kadir",
  "difficulty": "easy",
  "status": "created",
  "topology": {
    "name": "basic-two-router",
    "nodes": [],
    "links": []
  },
  "injected_errors": [],
  "cli_access": [],
  "message": "Lab session retrieved successfully."
}
```

---

# 5. Deploy Lab

Bu endpoint/uÃ§ nokta lab ortamÄ±nÄ± Ã§alÄ±ÅŸtÄ±rmak iÃ§in kullanÄ±lÄ±r.

Sprint 1 MVP aÅŸamasÄ±nda bu endpoint gerÃ§ek Containerlab komutu Ã§alÄ±ÅŸtÄ±rmayacak. Åimdilik mock/sahte cevap dÃ¶necek.

Ä°leride burada ÅŸu komut backend tarafÄ±ndan Ã§alÄ±ÅŸtÄ±rÄ±lacak:

```bash
containerlab deploy -t path/to/topology.clab.yml
```

## Request

```http
POST /labs/{session_id}/deploy
```

## Example Full URL

```text
http://127.0.0.1:8000/api/v1/labs/lab-abc12345/deploy
```

## Response

```json
{
  "session_id": "lab-abc12345",
  "status": "deployed",
  "message": "MOCK: Topology 'basic-two-router' deployed successfully."
}
```

---

# 6. Validate Lab

Bu endpoint/uÃ§ nokta Ã¶ÄŸrencinin yaptÄ±ÄŸÄ± dÃ¼zeltmelerden sonra validation/doÄŸrulama iÅŸlemini baÅŸlatÄ±r.

Sprint 1 MVP aÅŸamasÄ±nda gerÃ§ek network validation/doÄŸrulama yapÄ±lmayacak. Mock/sahte validation sonucu dÃ¶necek.

Ä°leride burada Python validation scripts/doÄŸrulama scriptleri Ã§alÄ±ÅŸtÄ±rÄ±lacak.

## Request

```http
POST /labs/{session_id}/validate
```

## Example Full URL

```text
http://127.0.0.1:8000/api/v1/labs/lab-abc12345/validate
```

## Response

```json
{
  "session_id": "lab-abc12345",
  "status": "validated",
  "passed": false,
  "score": 50,
  "checks": [
    {
      "check_id": "check_1_ip_address_mismatch",
      "topic": "IP Addressing",
      "passed": false,
      "message": "IP Addressing issue still exists: Incorrect IP address configured on r1 eth1."
    },
    {
      "check_id": "check_2_vlan_mismatch",
      "topic": "VLAN",
      "passed": true,
      "message": "VLAN check passed."
    }
  ],
  "recommendations": [
    "Review topic: IP Addressing"
  ]
}
```

## Response Fields

| Field | Type | Description |
|---|---|---|
| session_id | string | Validation/doÄŸrulama yapÄ±lan session ID |
| status | string | Session durumu |
| passed | boolean | Genel baÅŸarÄ± durumu |
| score | integer | 0-100 arasÄ± puan |
| checks | array | Her validation kontrolÃ¼nÃ¼n sonucu |
| recommendations | array | Ã–ÄŸrenciye Ã¶nerilen tekrar konularÄ± |

---

# 7. Destroy Lab

Bu endpoint/uÃ§ nokta Ã§alÄ±ÅŸan lab ortamÄ±nÄ± kapatmak iÃ§in kullanÄ±lÄ±r.

Ä°leride backend bu endpoint iÃ§inde ÅŸu Containerlab komutunu Ã§alÄ±ÅŸtÄ±racak:

```bash
containerlab destroy -t path/to/topology.clab.yml
```

Sprint 1 MVP aÅŸamasÄ±nda mock/sahte cevap dÃ¶ner.

## Request

```http
POST /labs/{session_id}/destroy
```

## Example Full URL

```text
http://127.0.0.1:8000/api/v1/labs/lab-abc12345/destroy
```

## Response

```json
{
  "session_id": "lab-abc12345",
  "status": "destroyed",
  "message": "MOCK: Topology 'basic-two-router' destroyed successfully."
}
```

---

# 8. Session Status Values

Backend tarafÄ±nda session/lab oturumu ÅŸu durumlardan birine sahip olabilir:

| Status | Meaning |
|---|---|
| created | Lab session oluÅŸturuldu ama henÃ¼z deploy edilmedi |
| deployed | Lab ortamÄ± Ã§alÄ±ÅŸtÄ±rÄ±ldÄ± |
| validated | Validation/doÄŸrulama yapÄ±ldÄ± |
| destroyed | Lab ortamÄ± kapatÄ±ldÄ± |
| error | Bir hata oluÅŸtu |

---

# 9. Difficulty Values

| Difficulty | Error Count | Description |
|---|---:|---|
| easy | 2 | BaÅŸlangÄ±Ã§ seviyesi |
| medium | 3 | Orta seviye |
| hard | 5 | Zor seviye |

---

# 10. Frontend Notes for Muhammed

Muhammed frontend tarafÄ±nda Ã¶ncelikle ÅŸu endpointleri kullanabilir:

```text
GET /api/v1/health
GET /api/v1/meta/difficulties
POST /api/v1/labs
GET /api/v1/labs/{session_id}
POST /api/v1/labs/{session_id}/deploy
POST /api/v1/labs/{session_id}/validate
POST /api/v1/labs/{session_id}/destroy
```

Frontend ilk aÅŸamada gerÃ§ek backend baÄŸlantÄ±sÄ± kurmadan Ã¶nce `frontend-mocks/lab-session-response.json` dosyasÄ±nÄ± mock data/sahte veri olarak kullanabilir.

Backend Ã§alÄ±ÅŸtÄ±ÄŸÄ±nda frontend base URL olarak ÅŸunu kullanmalÄ±dÄ±r:

```text
http://127.0.0.1:8000/api/v1
```

---

# Sprint 2 Backend Addendum

Sprint 2 ile backend tarafinda su guncellemeler yapildi:

- Containerlab Adapter artik gercek deploy, inspect ve destroy komutlarini calistirir.
- Topology Generator difficulty seviyesine gore easy, medium veya hard template secip session ozel lab.clab.yml uretir.
- Error Injection v1 injected_errors.json ve device config dosyalari uretir.
- Validation Service v1 config dosyalarini okuyarak check, score ve recommendation uretir.
- Session Persistence v1 session bilgisini session.json dosyasinda saklar.

## New Endpoint

GET /labs/{session_id}/inspect

Bu endpoint Containerlab uzerinden lab durumunu kontrol eder.

## Updated ActionResponse

Deploy, inspect ve destroy endpointleri artik su ek alanlari doner:

- command
- return_code
- stdout
- stderr

## Generated Session Files

Yeni session icin su dosyalar uretilir:

- containerlab/generated/<session_id>/lab.clab.yml
- containerlab/generated/<session_id>/session.json
- containerlab/generated/<session_id>/errors/injected_errors.json
- containerlab/generated/<session_id>/configs/r1.conf
- containerlab/generated/<session_id>/configs/r2.conf

Hard difficulty icin r3.conf ve r4.conf dosyalari da olusabilir.

## Validation v1 Behavior

Validation servisi injected_errors.json dosyasini ve configs/<device>.conf dosyalarini okur. Hata kodu config icinde duruyorsa check basarisiz, hata kodu kaldirilmissa check basarili kabul edilir.

## Session Persistence

Backend restart edilse bile GET /labs/{session_id} endpointi session bilgisini session.json dosyasindan geri yukleyebilir.


---

# Sprint 5 Backend Addendum - Student-Safe Lab Responses

Sprint 5 ile backend tarafında student-safe response / öğrenciye güvenli yanıt ve instructor/debug response / eğitmen veya debug yanıtı ayrımı eklenmiştir.

## Main Rule

Default student-facing endpoints must not expose injected_errors / enjekte edilen hatalar.

Student-facing frontend must use:

`	ext
POST /api/v1/labs
GET /api/v1/labs/{session_id}
GET /api/v1/labs/{session_id}/cli
POST /api/v1/labs/{session_id}/deploy
GET /api/v1/labs/{session_id}/inspect
POST /api/v1/labs/{session_id}/validate
POST /api/v1/labs/{session_id}/destroy

Instructor/debug tools may use:

GET /api/v1/labs/{session_id}/debug
Student-Safe Create Lab Response
{
  "success": true,
  "session_id": "lab-abc12345",
  "student_id": "demo-student",
  "difficulty": "medium",
  "status": "created",
  "topology": {
    "name": "autonetlab-lab-abc12345",
    "nodes": [],
    "links": []
  },
  "cli_access": [],
  "hints": [
    "Check IP addressing and subnet masks.",
    "Verify interface status before testing connectivity.",
    "Review routing and default gateway configuration.",
    "Compare addressing, interfaces, and routing step by step across the topology."
  ],
  "message": "Lab session created successfully."
}
Student-Safe Get Lab Response
{
  "success": true,
  "session_id": "lab-abc12345",
  "student_id": "demo-student",
  "difficulty": "medium",
  "status": "created",
  "topology": {
    "name": "autonetlab-lab-abc12345",
    "nodes": [],
    "links": []
  },
  "cli_access": [],
  "hints": [
    "Check IP addressing and subnet masks.",
    "Verify interface status before testing connectivity.",
    "Review routing and default gateway configuration.",
    "Compare addressing, interfaces, and routing step by step across the topology."
  ],
  "message": "Lab session retrieved successfully."
}
Debug/Instructor Get Lab Response
{
  "success": true,
  "session_id": "lab-abc12345",
  "student_id": "demo-student",
  "difficulty": "medium",
  "status": "created",
  "topology": {
    "name": "autonetlab-lab-abc12345",
    "nodes": [],
    "links": []
  },
  "cli_access": [],
  "hints": [
    "Check IP addressing and subnet masks.",
    "Verify interface status before testing connectivity.",
    "Review routing and default gateway configuration."
  ],
  "injected_errors": [
    {
      "code": "MISSING_ROUTE",
      "topic": "Routing",
      "device": "r2",
      "description": "Required static route is missing on r2.",
      "severity": "medium"
    }
  ],
  "message": "Debug lab session retrieved successfully."
}
Frontend Adaptation Note for Muhammed

Muhammed frontend tarafında student view / öğrenci ekranı için injected_errors alanını kullanmamalıdır.

Student screen must use:

POST /api/v1/labs
GET /api/v1/labs/{session_id}

Debug or instructor-only screen may use:

GET /api/v1/labs/{session_id}/debug

Topology visualization / topoloji görselleştirme için frontend şu alanları kullanmalıdır:

topology.name
topology.nodes[].id
topology.nodes[].label
topology.nodes[].kind
topology.nodes[].image
topology.links[].source.node
topology.links[].source.interface
topology.links[].target.node
topology.links[].target.interface
cli_access[].device_id
cli_access[].name
cli_access[].container_name
cli_access[].command
hints[]

Student-safe response içinde şu alanlar bulunmamalıdır:

injected_errors
expected_fix
solution
answer
debug

---

# Sprint 6 Backend Addendum - Instructor Analytics

Sprint 6 ile backend tarafına instructor dashboard / eğitmen paneli için read-only analytics endpointleri eklenmiştir.

Bu endpointler lab runtime state / lab çalışma durumunu değiştirmez. Sadece mevcut session metadata / oturum metadata dosyalarını okur.

## Added Endpoints

```text
GET /api/v1/instructor/analytics/summary
GET /api/v1/instructor/analytics/difficulty-distribution
GET /api/v1/instructor/analytics/topic-weaknesses
GET /api/v1/instructor/sessions/recent
---

# 10. Sprint 7 Recommendation Endpoint

This endpoint returns explanatory recommendation data for the frontend recommendation UI.

Bu endpoint, frontend tarafındaki recommendation UI / öneri arayüzü için açıklamalı öneri verisi döner.

## Request

GET /labs/{session_id}/recommendations

## Example Full URL

http://127.0.0.1:8000/api/v1/labs/lab-abc12345/recommendations

## Response after validation

```json
{
  "success": true,
  "session_id": "lab-abc12345",
  "status": "validated",
  "score": 40,
  "passed": false,
  "source": "rule_based",
  "fallback_used": true,
  "recommendations": [
    {
      "topic": "ip_addressing",
      "label": "IP Addressing",
      "reason": "Failed validation checks indicate weakness in IP Addressing.",
      "explanation": "1 validation check(s) related to IP Addressing failed. The topic failure rate is 100.0%. Current score: 40. The student should focus on this topic before attempting a harder lab.",
      "priority": "high",
      "confidence": 0.9,
      "source": "rule_based",
      "next_actions": [
        "Review IP address and subnet mask configuration.",
        "Compare both router interfaces that are connected to the same link.",
        "Run basic connectivity tests after fixing addressing issues."
      ],
      "related_failed_checks": [
        {
          "check_id": "check_1_ip_address_mismatch",
          "topic": "IP Addressing",
          "message": "IP Addressing issue still exists on r1."
        }
      ]
    }
  ],
  "message": "Rule-based fallback recommendations generated successfully. ML prototype was unavailable or did not produce a reliable prediction."
}

## Response before validation

```json
{
  "success": true,
  "session_id": "lab-abc12345",
  "status": "created",
  "score": null,
  "passed": null,
  "source": "rule_based",
  "fallback_used": true,
  "recommendations": [],
  "message": "No validation result found yet. Run validation before requesting personalized learning recommendations."
}
Source field values
ValueMeaning
rule_basedRecommendation was generated by deterministic validation rules.
ml_prototypeRecommendation was generated by the optional ML prototype.
hybridRule-based signals and ML prototype output were combined.
Frontend guidance for Muhammed

Muhammed frontend tarafında:

priority alanını badge olarak gösterebilir: high, medium, low.
confidence alanını yüzde olarak gösterebilir.
source alanı kullanıcıya dürüst şekilde gösterilebilir.
fallback_used = true ise "Reliable rule-based fallback is active." benzeri bir bilgi gösterilebilir.
recommendations boşsa validation henüz çalışmamıştır; empty state gösterilmelidir.
reason, explanation, next_actions alanları recommendation card içinde kullanılabilir.
related_failed_checks alanı expandable detail olarak gösterilebilir.

