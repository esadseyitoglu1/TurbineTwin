# NOTLAR — Rüzgar Türbini Dijital İkiz

Bu dosya, mülakat hazırlığı için tutulan çalışma notu. Her adımda alınan kararlar
ve gerekçeleri buraya işleniyor.

## Faz 1 — Veri ve Model

### Adım 0 — Proje iskeleti

- `.venv` sanal ortamı `--system-site-packages` ile kuruldu: Python 3.14 çok yeni
  olduğu için bazı bilimsel paketlerin bu sürüme hazır wheel'i olmayabilir. Bu
  bayrak, global olarak zaten çalıştığı doğrulanmış pandas/numpy/sklearn/matplotlib'i
  miras alırken, yeni kurulacak paketleri (fastapi gibi) izole tutuyor.
- `src/turbinetwin/` bir Python paketi olarak kuruldu, çünkü Faz 2'nin FastAPI'si
  ve Faz 5'in MCP sunucusu aynı fonksiyonları (`deviation.py`, `anomaly.py`) import
  edecek — kod tekrarını baştan önlüyor.
- **Beklenmedik bulgu:** `C:\Users\Monster` kökünde boş, kazara açılmış bir git
  repo bulundu. Silinip `TurbineTwin` içinde doğru scope'ta yeniden açıldı.
  Ders: `git add` öncesi her zaman `git status` ile nerede olduğunu kontrol et.

### Adım 1 — Veri temini

- Kaggle'daki T1.csv indirildi, `data/raw/`'a konuldu (gitignored — lisanslı veri,
  public repo'da yeniden dağıtılmıyor).
- Dosyada `31 12 2018` satırı bulundu: 31 hiçbir zaman ay olamayacağı için, format
  kesin olarak **gün-önce** (`DD MM YYYY`) olduğu kanıtlandı — tahmin değil.

### Adım 2 — Doğru yükleme

- `pd.to_datetime()` `format=` verilmeden çalıştırıldığında **gerçekten çöktü**:
  `"13 01 2018 00:00" doesn't match format "%m %d %Y %H:%M"`. pandas ay-önce
  varsaymış, 13'ü ay sanıp patlamış.
- **Kritik içgörü:** Eğer veri setinde 12'den büyük gün numarası hiç olmasaydı,
  bu hata hiç gelmezdi — pandas sessizce yanlış tarihler üretirdi (örn. "05 03"
  gibi belirsiz satırlarda ay ve gün yer değiştirirdi). Crash bir şanstı, güvence
  değildi. `format='%d %m %Y %H:%M'` açıkça vererek bu belirsizliği ortadan kaldırdık.
- Kolon isimleri snake_case'e çevrildi (`LV ActivePower (kW)` → `active_power_kw`
  gibi) — yazması kolay, tutarlı bir sözleşme.
- `theoretical_power_kw` kolonunun tepe değeri tam **3600 kW** çıktı — bu türbinin
  gerçek anma (nameplate) gücü. `RATED_POWER`'ı ileride hardcode etmek yerine
  veriden (`.max()`) türeteceğiz.
- Not: `Theoretical_Power_Curve (KWh)` kolon adındaki birim (`KWh`) hatalı —
  gerçekte `kW` (anlık güç), `kWh` (zaman içinde biriken enerji) değil. Kod
  içinde doğru isimle (`theoretical_power_kw`) çağırarak bu düzeltildi.

### Adım 3 — Veri kalitesi raporu (temizlik değil)

- Beklenenin aksine veri setinde hiç `NaN`, hiç tekrar eden zaman damgası yok
  ve satırlar zaten sıralı. Asıl eksiklik farklı bir biçimde: **2030 zaman
  aralığı baştan hiç yok** (52.560 beklenirken 50.530 satır var). En büyük
  boşluk 26-30 Ocak arası 4 gün 8 saat — muhtemelen planlı bakım.
- 57 satırda küçük negatif güç var (-2.47 ile -0.0005 kW arası), hepsi düşük
  rüzgarda (2-4.6 m/s, cut-in'e yakın). **Bunlar silinmedi/sıfırlanmadı** —
  türbinin bekleme modunda kendi elektroniğini şebekeden beslemesinin gerçek
  fiziksel sonucu, sensör hatası değil.
- **Çerçeveleme kararı:** fonksiyona `clean()` değil `report_data_quality()`
  adı verildi, çünkü hiçbir satır silinmedi/değiştirilmedi — sadece veri
  setinin sınırları belgelendi. Ham SCADA verisini kendi varsayımımızla
  bozmamak, "temizlik" ile "raporlama" arasındaki bilinçli seçim.
- Savunma amaçlı (defensive) `drop_duplicates` + `sort_values` kod içinde
  tutuldu, bugün hiçbir satırı etkilemese de: farklı bir export'ta veya farklı
  bir türbin verisinde bu garanti olmayabilir.
