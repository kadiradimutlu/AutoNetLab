# AutoNetLab API Contracts

This document defines the REST/HTTP JSON API contracts between the AutoNetLab Backend API and the Web Dashboard frontend.

Bu dosya, AutoNetLab Backend API ile Web Dashboard frontend arasındaki REST/HTTP JSON sözleşmelerini tanımlar.

---

## Base URL

```text
http://127.0.0.1:8000/api/v1
```

Local development / yerel geliştirme sırasında backend bu adres üzerinden çalışacaktır.

---

# 1. Health Check

Health Check endpoint/uç noktası backend servisinin çalışıp çalışmadığını kontrol etmek için kullanılır.

Bu endpoint genellikle frontend tarafından da kullanılabilir ama asıl amacı geliştirme sırasında backend ayakta mı diye hızlı kontrol yapmaktır.

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

Backend API çalışıyor demektir.

---

# 2. Get Difficulty Levels

Bu endpoint/uç nokta frontend’e kullanılabilir zorluk seviyelerini döner.

Muhammed bu response/cevap sayesinde ekranda şu seçenekleri gösterebilir:

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

Bu endpoint/uç nokta yeni bir lab session / laboratuvar oturumu oluşturur.

Frontend kullanıcının seçtiği zorluk seviyesini backend’e gönderir. Backend ise yeni bir session oluşturur, topology/topoloji bilgisini üretir, injected errors/enjekte edilen hataları belirler ve frontend’e JSON olarak döner.

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
| student_id | string | yes | Öğrenci kullanıcı adı veya ID bilgisi |
| difficulty | string | yes | Lab zorluk seviyesi: easy, medium veya hard |
| topology_template | string | yes | Kullanılacak topology/topoloji şablonu |

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
| session_id | string | Oluşturulan lab session/lab oturumu ID bilgisi |
| student_id | string | Öğrenci ID bilgisi |
| difficulty | string | Seçilen zorluk seviyesi |
| status | string | Session durumu |
| topology | object | Frontend’in topology görselleştirmesi için kullanacağı veri |
| injected_errors | array | Sistemin lab içine eklediği hatalar |
| cli_access | array | Öğrencinin CLI üzerinden bağlanacağı cihaz komutları |
| message | string | Kullanıcıya gösterilecek açıklama mesajı |

---

# 4. Get Lab Session

Bu endpoint/uç nokta daha önce oluşturulmuş bir lab session/lab oturumunu getirir.

Frontend, sayfa yenilendiğinde veya session detayını göstermek istediğinde bu endpoint’i kullanabilir.

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

Bu endpoint/uç nokta lab ortamını çalıştırmak için kullanılır.

Sprint 1 MVP aşamasında bu endpoint gerçek Containerlab komutu çalıştırmayacak. Şimdilik mock/sahte cevap dönecek.

İleride burada şu komut backend tarafından çalıştırılacak:

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

Bu endpoint/uç nokta öğrencinin yaptığı düzeltmelerden sonra validation/doğrulama işlemini başlatır.

Sprint 1 MVP aşamasında gerçek network validation/doğrulama yapılmayacak. Mock/sahte validation sonucu dönecek.

İleride burada Python validation scripts/doğrulama scriptleri çalıştırılacak.

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
| session_id | string | Validation/doğrulama yapılan session ID |
| status | string | Session durumu |
| passed | boolean | Genel başarı durumu |
| score | integer | 0-100 arası puan |
| checks | array | Her validation kontrolünün sonucu |
| recommendations | array | Öğrenciye önerilen tekrar konuları |

---

# 7. Destroy Lab

Bu endpoint/uç nokta çalışan lab ortamını kapatmak için kullanılır.

İleride backend bu endpoint içinde şu Containerlab komutunu çalıştıracak:

```bash
containerlab destroy -t path/to/topology.clab.yml
```

Sprint 1 MVP aşamasında mock/sahte cevap döner.

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

Backend tarafında session/lab oturumu şu durumlardan birine sahip olabilir:

| Status | Meaning |
|---|---|
| created | Lab session oluşturuldu ama henüz deploy edilmedi |
| deployed | Lab ortamı çalıştırıldı |
| validated | Validation/doğrulama yapıldı |
| destroyed | Lab ortamı kapatıldı |
| error | Bir hata oluştu |

---

# 9. Difficulty Values

| Difficulty | Error Count | Description |
|---|---:|---|
| easy | 2 | Başlangıç seviyesi |
| medium | 3 | Orta seviye |
| hard | 5 | Zor seviye |

---

# 10. Frontend Notes for Muhammed

Muhammed frontend tarafında öncelikle şu endpointleri kullanabilir:

```text
GET /api/v1/health
GET /api/v1/meta/difficulties
POST /api/v1/labs
GET /api/v1/labs/{session_id}
POST /api/v1/labs/{session_id}/deploy
POST /api/v1/labs/{session_id}/validate
POST /api/v1/labs/{session_id}/destroy
```

Frontend ilk aşamada gerçek backend bağlantısı kurmadan önce `frontend-mocks/lab-session-response.json` dosyasını mock data/sahte veri olarak kullanabilir.

Backend çalıştığında frontend base URL olarak şunu kullanmalıdır:

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

