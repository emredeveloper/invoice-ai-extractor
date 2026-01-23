# Prompt Yonetimi ve Versiyonlama

Bu dokuman, prompt versiyonlama ve A/B test yaklasimini tanimlar.

## Versiyonlama Politikasi

- Her prompt icin benzersiz bir `prompt_id` kullanilir.
- Semver tabanli surumleme onerilir: `major.minor.patch`.
  - **major**: cikti formatinda veya is kuralinda kirici degisiklik
  - **minor**: yeni alan/iyilestirme
  - **patch**: duzeltme veya optimizasyon

## Degisiklik Notlari

- Prompt degisiklikleri icin kisa bir changelog tutulur.
- Hangi endpoint/akislari etkiledigi belirtilir.

## A/B Test Destegi (Oneri)

- Trafik orani: `A=90%`, `B=10%` gibi kontrollu dagitim.
- KPI: dogruluk, isleme suresi, manuel duzeltme orani.
- Deneme suresi: asgari ornek sayisi belirlenir.

## Yayinlama Akisi (Oneri)

1) Staging ortaminda deneme
2) Kucuk ornekle A/B
3) Basari metri?i esigine ulasinca genisletme

## Kayit ve Izlenebilirlik

- Prompt version bilgisi audit log veya isleme kaydina eklenir.
- Ustune raporlanabilir KPI alanlari eklenir.
