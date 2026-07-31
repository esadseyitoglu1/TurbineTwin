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
- **Ek inceleme:** 57 negatif güç satırının 40'ı cut-in altında (zararsız, zaten
  sıfır bekleniyordu), 17'si cut-in üstünde (3.0-4.6 m/s arası). Bu 17 satır
  cut-in sınırının hemen üstünde kümelenmiş — fiziksel açıklaması, türbinin
  3 m/s'i geçer geçmez anında tam torka geçmemesi, geçiş bölgesinde kendi iç
  tüketiminin (kontrol elektroniği, yağ pompası) ürettiğinden fazla olabilmesi.
  Bu satırlar Adım 6'da `in_range=True` sayılacak ve Adım 8'in eşik dedektörüne
  aday olacak — mutlak kW olarak küçük ama anma-gücüne-normalize sapma
  metriğinde görünür olmaları bekleniyor.

### Adım 4 — Güç eğrisi grafiği

- `plot_power_curve()`: gerçek veri saydam scatter (`alpha=0.1`) olarak,
  teorik eğri rüzgar hızına göre sıralanıp çizgi olarak çizildi. S-eğrisi,
  cut-in dirseği (~3 m/s) ve anma platosu (~12 m/s'den sonra 3600 kW'ta düz)
  net görünüyor.
- **Gözlem:** 5-12 m/s aralığında, teorik eğrinin belirgin şekilde altında
  kalan (bazen ~0 kW'a yakın) yoğun bir nokta bulutu var. İki olası açıklama:
  (1) **kasıtlı duruş** — bakım, şebeke kısıtlaması (curtailment), gürültü
  kısıtlaması gibi operasyonel kararlar, anomali değil; (2) **gerçek arıza/
  performans kaybı** — kanat kirliliği, sensör hatası, yaw yanlış hizalanması,
  mekanik sürtünme, gerçek bir anomali.
- **Bilinçli sınır:** Elimizdeki veri setinde durum kodu (CARE veri setindeki
  gibi "Service"/"Derated Operation" etiketi) yok, bu yüzden bu iki senaryoyu
  tek bir satırdan kesin ayıramıyoruz. Zamansal kümelenme (saatlerce süren
  düşüş = bakım; dağınık tekil noktalar = anlık arıza) bir ipucu olabilir ama
  Faz 1'in kapsamı dışında. Bu ayrımı yapmak Faz 4'ün RAG sisteminin işi:
  "anomali tespit edildi, olası nedenler nedir" sorusunu bakım dokümanlarına
  sorup insan yorumuyla desteklemek.

### Adım 5 — Sapma metriği

- `add_naive_deviation()`: `(gerçek - teorik) / teorik` formülü **bilerek**
  korumasız bırakıldı. Gerçek veride çalıştırılınca canlı olarak doğrulandı:
  `theoretical_power_kw == 0` olan satırlarda `0/0 = NaN` (43.246/50.530 satır
  geçerli sonuç üretti, geri kalanı NaN), ama `active_power_kw` sıfırdan farklı
  küçük bir değerken `theoretical_power_kw = 0` olan satırlarda sonuç **`inf`**
  (sonsuz) çıktı — `.describe()` çağrısında `mean: NaN`, `RuntimeWarning:
  invalid value encountered` uyarısıyla yakalandı.
- **`inf` vs `NaN` ayrımı:** `inf` = sıfır olmayan sayı / sıfır (matematiksel
  olarak "sonsuza gider"); `NaN` = sıfır / sıfır (tamamen tanımsız). İkisi de
  C#'taki gibi programı çökertmiyor, sessizce üretilip hesaplamalara (örn.
  `.mean()`) karışıyor — tek bir `inf` tüm ortalamayı `NaN`'a çeviriyor.
- `add_normalized_deviation()`: `(gerçek - teorik) / RATED_POWER` formülüne
  geçildi. `RATED_POWER`, `theoretical_power_kw.max()` ile **veriden türetildi**
  (hardcode edilmedi) — tepe değer 3600 kW çıktı, Adım 2'de bulduğumuz sayıyla
  tutarlı. Aynı üç satırda karşılaştırma: `deviation_rel` üçü de `inf`,
  `deviation_norm` sırasıyla `0.0012`, `0.0024`, `0.0075` — küçük, anlamlı,
  gerçek büyüklüğü yansıtan sayılar. Tüm veri setinde (`50530` satır) `inf`/`NaN`
  sayısı: **0**. Sabit ve sıfır olmayan payda, sıfıra bölmeyi yamamak yerine
  yapısal olarak imkânsız kılıyor.

### Adım 6 — Çalışma durumu (cut-in/cut-out kuralı)

- `add_operating_state()`: `in_range` (bool) ve `state` (`"below_cut_in"` /
  `"normal"` / `"above_cut_out"`) kolonları eklendi. Sonuç: 42.780 satır
  `normal`, 7.749 satır `below_cut_in`, sadece **1** satır `above_cut_out`
  (25 m/s'i geçen tek an — gerçek fırtına seviyesinde rüzgarın ne kadar nadir
  olduğunu doğruluyor).
  `in_range` ile `state` çapraz kontrolü tutarlı: `normal` → her zaman `True`,
  diğer ikisi → her zaman `False`.
- **Bu adımın projedeki rolü:** `in_range`, sapma büyüklüğünden (`deviation_norm`)
  bağımsız, ayrı bir kapı. Sebep: cut-in altında sensör gürültüsü/rölanti
  davranışı hem küçük hem büyük sapmalar üretebilir, ama hiçbiri arıza
  sayılmaz çünkü türbin zaten o bölgede çalışmıyor olması bekleniyor.
  `deviation_norm` "ne kadar sapma var" sorusuna, `in_range` ise "bu sapmaya
  güvenilir mi / burada bakmaya değer mi" sorusuna cevap veriyor — CEO'nun
  röportajda bahsettiği "tasarım değerlerinden sapma" kavramının somut hali:
  sadece istatistiksel olarak nadir noktaları değil, türbinin **kendi tasarım
  kurallarına göre** çalışması gereken bölgede gerçekten sapan anları arıyoruz.
