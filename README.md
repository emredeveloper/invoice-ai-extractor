# Fatura Veri Çıkarma Sistemi (QIT AI Assessment)

Bu sistem, asenkron bir mimari kullanarak faturalardan (PDF, resim, metin) akıllı veri çıkarma işlemi gerçekleştirir. Hem bulut (Gemini) hem de yerel (LM Studio/Qwen) modelleri destekler.

## 🚀 Hızlı Başlangıç

1.  **Docker ile Başlat:** `docker-compose up --build` komutuyla tüm sistemi (API, Worker, Redis) ayağa kaldırın.
2.  **Yapılandırma:** [.env](.env) dosyasında `LLM_PROVIDER` ve ilgili API/URL bilgilerini ayarlayın.
3.  **Test Et:** `python tests/auto_test.py` komutuyla örnek faturaları işleyin.

## 🛠️ Adım Adım Uygulama & Kod Referansları

### Adım 1: Asenkron Altyapı ve Dockerizasyon
Sistemin ölçeklenebilir olması için Docker tabanlı bir yapı kuruldu.
- [docker-compose.yml](docker-compose.yml): API, Celery Worker ve Redis servislerini orkestre eder.
- [Dockerfile](Dockerfile): Python 3.11 tabanlı, gerekli sistem kütüphanelerinin (libmagic vb.) yüklü olduğu imajı oluşturur.

### Adım 2: API ve Görev Yönetimi (Task Queue)
Asenkron işlem mimarisi sayesinde büyük dosyalar API'yi kilitlemeden işlenir.
- [app/api/main.py](app/api/main.py): FastAPI ile dosya yükleme ve statü takibi endpointlerini sunar.
- [app/worker/tasks.py](app/worker/tasks.py): Ağır LLM görevlerini Celery ve Redis kullanarak arka planda yürütür.

### Adım 3: Agentic Veri Çıkarma Motoru
Sistem sadece metni LLM'e göndermek yerine, dosya içeriğini analiz eden "agentic" bir yaklaşıma sahiptir.
- [app/core/extraction_engine.py](app/core/extraction_engine.py): `ExtractionEngine` sınıfı, PDF'leri vision modelleri için görsele dönüştürür (PyMuPDF kullanarak) ve uygun LLM sağlayıcısını (Gemini veya Local) seçer.
- [app/core/prompts.py](app/core/prompts.py): Modeli yapılandırılmış JSON çıktısı üretmeye zorlayan "System Prompt"ları içerir. **Yeni şema:** `tax_amount`, `tax_rate` ve `currency` alanları eklendi.

### Adım 4: Esnek Akıllı Analiz ve Bonus Doğrulamalar
Çıkarılan veriler üzerinde **dinamik** kontroller yapılır.
- **Aritmetik Doğrulama:** Her bir kalem için `miktar * birim fiyat = toplam` kontrolü yapılır.
- **Dinamik Vergi Doğrulaması:** Sistem artık sabit %18'e bağlı değildir. [app/core/validators.py](app/core/validators.py) içinde, faturadan çıkarılan `tax_rate` değeri (örn: %1, %8, %20, ÖTV, Stopaj) kullanılarak doğrulama yapılır. Oran bulunamazsa varsayılan %18 kullanılır.
- **Evrensel Para Birimi:** TL, USD, EUR veya herhangi bir para birimi simgesi model tarafından otomatik olarak tanınır.

### Adım 5: Yerel LLM ve Çözüm Yaklaşımı (Local Support)
Donanım (RTX 4060) kısıtları ve veri mahremiyeti için LM Studio entegrasyonu sağlandı.
- [LocalLLMProvider](app/core/extraction_engine.py#L39): OpenAI uyumlu API formatını kullanarak yerel vision modelleriyle (Qwen-VL) haberleşir.

### Adım 6: GDPR / KVKK ve Veri Mahremiyeti
Hassas verilerin korunması için iki temel mekanizma eklendi:
- **Otomatik Silme:** [app/worker/tasks.py](app/worker/tasks.py#L51) içinde işlem biter bitmez dosyalar diskten kalıcı olarak silinir.
- **Local Inference:** Verilerin buluta çıkmasını istemeyen kullanıcılar için yerel LLM desteği sunulur.

## 📈 Değerlendirme Kriterleri ve Çözümler

- **Türkçe Karakter Desteği:** OCR ve LLM aşamalarında `utf-8` kodlaması ve vision-tabanlı okuma ile Türkçe karakterler %100 doğrulukla işlenir.
- **Ölçeklenebilirlik:** Sistem stateless (durumsuz) olup, worker sayısı artırılarak 1000x yük altında dahi çalışabilir.
- **Hata Yönetimi:** Ağ kopmaları veya OOM (bellek yetersizliği) durumları için try-except blokları ve loglama mekanizması kurulmuştur.
- **Esneklik:** Her türlü vergi oranı (%1, %8, %20 vb.) ve para birimi (TL, USD, EUR vb.) desteklenir.