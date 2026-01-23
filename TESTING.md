# Test Stratejisi ve Kapsam

Bu dokuman, mevcut testlerin kapsamini ve calistirma adimlarini ozetler. Hedef, kritik akislari hizli dogrulamak ve regresyon riskini azaltmaktir.

## Kapsam

### Unit
- Validator ve isleme mantigi icin birim testleri (pytest altyapisi).
- Hata senaryolari ve alan dogrulama kurallari odaklidir.

### API ve Entegrasyon
- Temel API akislari ve yukleme senaryolari (otomasyon testi).
- Webhook tetikleme ve geri donus dogrulamasi.

### Sistem ve Ajan Testleri
- Sistem testi: tam akisin uctan uca kontrolu.
- Agent testi: LLM tabanli akislarda minimum davranis dogrulamasi.

### LLM Baglanti Dogrulamasi
- LM Studio baglantisi ve model yaniti icin baglanti testi.

## Test Dosyalari

- `tests/auto_test.py` - API yukleme akislari (smoke/acceptance)
- `tests/webhook_test.py` - Webhook akislari
- `tests/system_test.py` - Uctan uca sistem testi
- `tests/agent_test.py` - Agent/LLM davranis testi
- `tests/lmstudio-test.py` - LM Studio baglanti testi

## Calistirma

```bash
# Pytest tabanli unit testleri
pytest tests/

# API smoke testleri
python tests/auto_test.py

# Webhook akislari
python tests/webhook_test.py

# Sistem testi
python tests/system_test.py

# Agent/LLM testi
python tests/agent_test.py

# LM Studio baglanti testi
python tests/lmstudio-test.py
```

## Ortam Onkosullari

- `docker-compose up --build` ile servislerin ayakta olmasi onerilir.
- LLM testleri icin `LLM_PROVIDER` ve ilgili anahtarlar/URL'ler ayarlanmalidir.
- Ornek PDF'ler `samples/` altinda bulunur.

## Beklenen Ciktilar

- API testleri icin HTTP 200/201 yanitlari ve task durumlarinin tamamlanmasi.
- Webhook testinde hedef endpoint'e basarili istek.
- LLM testlerinde ornek bir yanit alinmasi.

## Kapsam Bosluklari (Backlog)

- Load/stress test senaryolari (k6/Locust).
- Prometheus metrikleri icin otomatik dogrulama testleri.
- Batch islemler icin daha genis veri setiyle regresyon paketi.
