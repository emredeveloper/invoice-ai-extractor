# 🧾 Invoice AI - Akıllı Fatura Veri Çıkarma Sistemi

AI destekli, ölçeklenebilir fatura veri çıkarma platformu. PDF, resim ve metin formatındaki faturalardan otomatik olarak yapılandırılmış veri çıkarır.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Özellikler

### 🔐 Güvenlik & Kimlik Doğrulama
- **JWT Authentication** - Access ve Refresh token desteği
- **API Key** - Harici uygulamalar için API anahtarı
- **Rate Limiting** - IP ve kullanıcı bazlı hız sınırlaması
- **CORS** - Yapılandırılabilir cross-origin desteği

### 📊 Veri İşleme
- **Multi-page PDF** - Çok sayfalı PDF'lerin tamamını işleme
- **Vision AI** - Resim tabanlı OCR ve veri çıkarma
- **Batch Processing** - 50'ye kadar fatura toplu işleme
- **Dinamik Vergi** - %1, %8, %18, %20 vb. tüm oranları destekleme

### 🔗 Entegrasyonlar
- **Webhook** - İşlem sonrası HTTP callback bildirimleri
- **Export** - CSV ve Excel formatında dışa aktarma
- **Prometheus** - Metrik izleme ve monitoring
- **Grafana** - Görsel dashboard'lar

### 🌐 LLM Desteği
- **Google Gemini** - Bulut tabanlı AI işleme
- **LM Studio** - Yerel Qwen-VL vision modeli
- **Esnek Mimari** - Kolay provider değiştirme
- Detaylar: [docs/llm-strategy.md](docs/llm-strategy.md)
- Prompt yonetimi: [docs/prompt-management.md](docs/prompt-management.md)

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose
- (Opsiyonel) LM Studio - Yerel model için

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/your-repo/invoice-ai.git
cd invoice-ai
```

### 2. Ortam Değişkenlerini Ayarlayın
```bash
# Docker'sız (lokal)
cp .env.local.example .env

# Docker ile
# cp .env.docker.example .env
```
Not: Lokal kullanımda `DISABLE_CELERY=true` ve `DISABLE_RATE_LIMIT=true` ile Redis olmadan çalıştırabilirsiniz (task durumları ve rate-limit RAM'de tutulur).

### 3. Docker ile Başlatın
```bash
docker-compose up --build
```

### 4. Servislere Erişin
| Servis | URL |
|--------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:8000 (veya frontend klasörü) |
| Redis UI | http://localhost:8001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

## 📚 API Endpoints

### Kimlik Doğrulama
```
POST /auth/register     - Yeni kullanıcı kaydı
POST /auth/login        - Giriş yap (JWT token al)
POST /auth/refresh      - Token yenile
GET  /auth/me           - Kullanıcı bilgileri
POST /auth/api-key      - API anahtarı oluştur
```

### Fatura İşleme
```
POST /upload            - Tek fatura yükle
GET  /status/{task_id}  - İşlem durumu sorgula
POST /upload/public     - Kimlik doğrulamasız yükleme (düşük limit)
```

### Fatura Yönetimi
```
GET    /invoices          - Faturaları listele (filtre, sayfalama)
GET    /invoices/stats    - Dashboard istatistikleri
GET    /invoices/{id}     - Fatura detayı
DELETE /invoices/{id}     - Fatura sil
POST   /invoices/export   - CSV/Excel export
```

### Toplu İşlem
```
POST /batch/upload      - Çoklu fatura yükle (maks. 50)
GET  /batch/{id}        - Toplu iş durumu
GET  /batch             - Toplu iş listesi
```

### Webhooks
```
GET    /webhooks          - Webhook listesi
POST   /webhooks          - Yeni webhook
GET    /webhooks/{id}     - Webhook detayı
PATCH  /webhooks/{id}     - Webhook güncelle
DELETE /webhooks/{id}     - Webhook sil
POST   /webhooks/{id}/test - Webhook test et
```

### Metrikler
```
GET /metrics            - Prometheus metrikleri
GET /health             - Sağlık kontrolü
Detayli ornekler ve hata semalari: [docs/api-examples.md](docs/api-examples.md)
```

## 🔧 Yapılandırma

### LLM Provider
```env
# Gemini (Cloud)
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_api_key

# Local (LM Studio)
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=qwen/qwen3-vl-4b
```

### Rate Limiting
```env
DEFAULT_RATE_LIMIT=60/minute
UPLOAD_RATE_LIMIT=10/minute
```

### PDF İşleme
```env
MAX_PDF_PAGES=10        # Maksimum sayfa sayısı
PDF_DPI_SCALE=1.5       # Görüntü kalitesi
```

## 📁 Proje Yapısı

```
├── app/
│   ├── api/
│   │   ├── main.py          # FastAPI ana uygulama
│   │   ├── invoices.py      # Fatura CRUD
│   │   ├── webhooks.py      # Webhook yönetimi
│   │   ├── batch.py         # Toplu işlem
│   │   └── schemas.py       # Pydantic modeller
│   ├── auth/
│   │   ├── router.py        # Auth endpoints
│   │   ├── jwt_handler.py   # JWT işlemleri
│   │   ├── dependencies.py  # FastAPI bağımlılıklar
│   │   └── schemas.py       # Auth şemaları
│   ├── core/
│   │   ├── extraction_engine.py  # LLM entegrasyonu
│   │   ├── prompts.py            # AI promptları
│   │   ├── validators.py         # Veri doğrulama
│   │   ├── export_service.py     # CSV/Excel export
│   │   ├── webhook_service.py    # Webhook gönderimi
│   │   ├── rate_limiter.py       # Hız sınırlama
│   │   └── metrics.py            # Prometheus metrikleri
│   ├── database/
│   │   ├── connection.py    # SQLAlchemy bağlantı
│   │   └── models.py        # Veritabanı modelleri
│   └── worker/
│       └── tasks.py         # Celery görevleri
├── frontend/
│   ├── index.html           # Ana sayfa
│   ├── styles.css           # CSS stilleri
│   └── app.js               # JavaScript
├── tests/
├── docker-compose.yml
├── Dockerfile
├── prometheus.yml
└── requirements.txt
```

## 🧪 Test

```bash
# Birim testleri çalıştır
pytest tests/

# API test et
python tests/auto_test.py

# LM Studio bağlantı testi
python tests/lmstudio-test.py
```

Detayli test kapsam? ve strateji: [TESTING.md](TESTING.md)


## 📈 Metrikler

### Prometheus Metrikleri
- `invoice_api_requests_total` - Toplam API istekleri
- `invoices_processed_total` - İşlenen fatura sayısı
- `invoice_processing_time_seconds` - İşlem süresi histogramı
- `auth_attempts_total` - Kimlik doğrulama denemeleri
- `webhook_calls_total` - Webhook çağrıları

### Grafana
Varsayılan şifre: `admin/admin`
Prometheus veri kaynağı URL: `http://prometheus:9090`
Detaylar: [docs/observability.md](docs/observability.md)

## 🔒 GDPR / KVKK Uyumu

- **Otomatik Silme**: Yüklenen dosyalar işlem sonrası otomatik silinir
- Detaylar: [docs/data-retention.md](docs/data-retention.md)
- **Yerel İşleme**: LM Studio ile veriler sunuculara gönderilmez
- **Veri Minimizasyonu**: Sadece gerekli alanlar çıkarılır
- **Audit Log**: Tüm işlemler loglanır
- Detaylar: [docs/audit-log.md](docs/audit-log.md)

## 🧭 Dokümasyon Geliştirme Notları

### Yükleme Sonrası Durum Göstergesi
- **Task progress görselleştirme**: Yükleme sonrası görev durumunu ilerleme barı, adım listesi ve tahmini süre ile göstermek.
- **Batch sonucu tablosu**: Toplu işler için özet tablo, durum filtreleri ve hata detaya gitme kısayolu.

### Audit Log Stratejisi
- **Format**: `event_type`, `actor_id`, `resource_id`, `status`, `duration_ms`, `ip`, `user_agent`, `timestamp` alanlarını içeren JSONL.
- **Saklama**: Varsayılan 30 gün; müşteriye göre 7/30/90/365 gün seçenekleri.
- **Arama/Filtreleme**: Zaman aralığı, event tipi, kullanıcı, fatura id, batch id filtreleri.

### KVKK / GDPR Veri Saklama Politikası
- **Otomatik silme** mevcut; **konfigürasyon opsiyonları** dokümante edilmeli.
- Örnek: `RETENTION_DAYS`, `AUTO_DELETE_UPLOADS`, `PURGE_SCHEDULE` değişkenleri ile özelleştirme.

### Model Seçim Stratejisi
- **Karşılaştırma**: LM Studio vs Gemini için performans/accuracy/latency tablosu.
- **Önerilen senaryolar**: On-prem hassas veri için yerel model, hızlı prototip ve yüksek kalite için bulut.

### Prompt Yönetimi
- **Versiyonlama politikası**: Prompt id, semver ve değişiklik notları.
- **A/B test desteği**: Trafik bölme, KPI takibi ve kazanım metrikleri.

### Kuyruk Gözlemlenebilirliği
- **Celery metrikleri**: Worker sayısı, queue length, task latency, retry count.
- **Prometheus entegrasyonu**: Metrik isimleri ve hedef scrape ayarları.

### Test Kapsamı ve Strateji
- **Kapsam**: Unit/API/e2e/batch/işleme doğrulama testleri net listelenmeli.
- **Test dokümanı**: `TESTING.md` gibi ayrı bir doküman önerilir.

### Load/Stress Testleri
- **Araçlar**: k6 veya Locust ile rate limit ve batch senaryoları.
- **Senaryolar**: 429 davranışı, sıra taşması, webhook gecikmesi.

### API Örnekleri ve Hata Şemaları
- **Örnekler**: Tekli yükleme, batch upload, webhook test.
- **Hata şemaları**: Standart error envelope (code, message, details, request_id).

## 🗺 Roadmap Öncelikleri

1) API örnekleri + hata şemaları (entegrasyonu kolaylaştırır)
2) Test kapsamı ve kalite dokümasyonu (güveni artırır)
3) Gözlemlenebilirlik (tracing/logging) (operasyonel sürdürülebilirlik)
4) LLM kullanım stratejisi & prompt versiyonlama (model kalitesi ve yönetilebilirlik)

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Değişiklikleri commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'i push edin (`git push origin feature/amazing`)
5. Pull Request açın

## 📄 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

**QIT AI Assessment** için geliştirilmiştir. 🚀
