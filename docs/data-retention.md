# KVKK/GDPR Veri Saklama Politikasi

Bu dokuman, veri saklama ve otomatik silme davranisini nasil konfigurasyon ile yonetilecegini anlatir.

## Temel Ilkeler

- Isleme tamamlaninca yuklenen dosyalar otomatik silinir.
- Fatura metaverisi ve audit loglari, saklama politikasina gore tutulur.
- Multeci (tenant) ortamlarda saklama suresi tenant bazli ayarlanabilir.

## Konfigurasyon (Oneri)

A?a??daki degiskenler, veri saklama davranisini ayarlamak icin kullanilabilir:

```env
# Veri saklama suresi (gun)
RETENTION_DAYS=30

# Y?klenen dosyalari otomatik sil
AUTO_DELETE_UPLOADS=true

# Periyodik temizlik zamani (cron ifadesi)
PURGE_SCHEDULE=0 3 * * *
```

## Davranis Detaylari

- `RETENTION_DAYS`: Fatura ve ilgili log verilerinin saklanma suresi.
- `AUTO_DELETE_UPLOADS`: Isleme sonrasi dosyalarin silinmesini kontrol eder.
- `PURGE_SCHEDULE`: Temizlik jobunun calisma zamanini belirler.

## Uyumluluk Notlari

- Gerektiginde veri minimizasyonu icin alan bazli redaksiyon uygulanabilir.
- Silme islemleri audit loglariyla kayit altina alinmalidir.
