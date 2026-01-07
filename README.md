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
cp .env.example .env
# .env dosyasını düzenleyin
```

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

## 🔒 GDPR / KVKK Uyumu

- **Otomatik Silme**: Yüklenen dosyalar işlem sonrası otomatik silinir
- **Yerel İşleme**: LM Studio ile veriler sunuculara gönderilmez
- **Veri Minimizasyonu**: Sadece gerekli alanlar çıkarılır
- **Audit Log**: Tüm işlemler loglanır

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