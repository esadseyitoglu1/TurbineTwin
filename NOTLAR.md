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
- **Tek `above_cut_out` satırının incelenmesi:** 2018-02-04 00:10, rüzgar
  25.21 m/s, güç hâlâ tam kapasitede (3600.78 kW) — ilk bakışta "pitch kontrolü
  tepki vermemiş, tehlikeli" gibi görünebilir. Ama komşu satırlara bakınca
  (23:40'tan 00:40'a kadar rüzgar 23-24 m/s bandında dolaşıyor, sadece bu tek
  ölçümde 25.2'ye sıçramış) bunun **anlık bir rüzgar darbesi (gust)** olduğu
  anlaşıldı — kontrol sisteminin tepki vermesi için yeterli süre bile geçmemiş,
  rüzgar zaten kendiliğinden geri düşmüş. Gerçek bir alarm durumu, rüzgarın
  **ardışık birden fazla ölçüm boyunca** 25 m/s üstünde kalmasına rağmen gücün
  düşmemesi olurdu — tek bir cut-out satırı tek başına yeterli kanıt değil.

### Adım 7 — Dağılım + eşik türetimi

- `derive_threshold()`: sadece `in_range=True` satırlarda (`df.loc[mask, col]`
  ile filtrelenerek) `deviation_norm`'un 1. yüzdebirliği (`np.nanpercentile`)
  ve ortalama−3σ yan yana hesaplandı.
- **Gerçek veride sonuç:** 1. yüzdebirlik = **-0.784**, ortalama−3σ = **-0.441**.
  Yüzdebirlik daha sıkı (daha negatif) çıktı çünkü dağılım çarpık: histogramda
  ana yığın 0.0 civarında yoğunlaşmışken (~15.000 satır tek çubukta), sola
  doğru ince ama uzun bir kuyruk var (-1.0'a kadar birkaç yüz satır).
  `deviation_norm < -0.5` olan 990 satırın hepsi incelenince: rüzgar 13-15 m/s
  (anma rüzgar hızının üstü, teorik tam 3600 kW) ama gerçek güç **tam sıfır**
  — Adım 4'te grafikte gördüğümüz "teoriğin altında kalan bulut"un somut
  karşılığı, muhtemelen ardışık satırlar halinde (uzun bir duruş dönemi).
- **Neden yüzdebirlik daha güvenilir burada da doğrulandı:** ortalama ve σ,
  bu uzun kuyruktaki aşırı değerlerden etkileniyor (σ şişiyor, eşik gevşiyor);
  yüzdebirlik sıralamaya dayandığı için bu aşırı değerler eşiği kaydırmıyor,
  sadece "en kötü %1"in neresi olduğunu doğru yansıtıyor.
- `plot_deviation_distribution()`: histogram + eşik çizgisi (`ax.axvline`)
  `outputs/figures/deviation_distribution.png`'ye kaydedildi.
- **İki eşiğin gerçekte işaretlediği satır sayısı:** yüzdebirlik (-0.784) →
  **428 satır (%1.00)**; ortalama-3σ (-0.441) → **1152 satır (%2.69)**.
  Ortalama-3σ, yüzdebirliğin **2.7 katı** kadar satırı işaretliyor. Histogramda
  bu fark görsel olarak küçük duruyor (o bölgedeki çubuklar zaten kısa, gözle
  ayırt etmesi zor) ama sayıca 724 satırlık bir oynama var. Pratik sonucu:
  ortalama-3σ ile gidilseydi bakım ekibine ~2.7 kat daha fazla alarm gider,
  bu da "alarm yorgunluğu" (alarm fatigue) riskini artırır. Yüzdebirliğin
  daha sıkı/seçici olması, bilinçli tercih sebebimizin somut kanıtı.

### Adım 8 — Eşik tabanlı anomali tespiti

- `flag_anomalies(df, threshold)`: `is_anomaly` kolonu, `in_range & (deviation_norm
  < threshold)` — iki koşulun **ikisi de** doğru olmalı. Gerçek veride
  doğrulama: 428 satır işaretlendi (Adım 7'nin sayısıyla birebir tutarlı),
  menzil-içi satırlarda oran tam **%1.0004** (tanım gereği beklenen), ve
  menzil-dışı satırlarda işaretlenen: **0** (in_range=False & ... her zaman
  False üretiyor, doğrulandı).
- `plot_anomalies()`: güç eğrisi grafiğine kırmızı noktalar olarak katman
  eklendi (`outputs/figures/anomalies.png`). **Görsel sonuç net:** işaretlenen
  428 nokta neredeyse tamamen 10-19 m/s aralığında, güç 0-800 kW civarında
  toplanmış — tam olarak Adım 4'te keşfettiğimiz "teoriğin altında kalan
  bulut"un dedektör tarafından otomatik yakalanmış hali. Bu, projenin en
  somut görsel kanıtı: teorik eğri yüksek güç bekliyorken (rüzgar bol), gerçek
  güç neredeyse sıfırda kalan anlar kırmızıyla işaretleniyor.
- **Zamansal kümelenme analizi:** 428 anomali satırının zaman damgaları arası
  farka bakıldığında, **324 tanesi** bir öncekinden tam 10 dakika sonra geliyor
  (yani ardışık, boşluksuz). Toplam 428 satır sadece **104 ayrı bloğa**
  ayrılıyor — ortalama blok uzunluğu birkaç saat. Bu, Adım 4'te tartıştığımız
  "kasıtlı duruş mu, gerçek arıza mı" ikileminde **duruş/bakım tarafını
  güçlendiriyor**: rastgele bir sensör arızası dağınık, tekil anlar üretirdi
  (zaman farkları çoğunlukla 10 dakikadan büyük çıkardı); burada tam tersi,
  uzun kesintisiz bloklar var. Kesin kanıt değil (durum kodu kolonu yok) ama
  güçlü bir istatistiksel ipucu.

### Adım 9 — Isolation Forest karşılaştırması

- `run_isolation_forest()`: sadece `in_range=True` satırlarda, `[wind_speed,
  active_power_kw]` üzerinde `IsolationForest(contamination=0.01,
  random_state=42)` eğitildi. `predict` sonucu `-1`/`1` döndürüyor (`0`/`1`
  değil) — `predictions == -1` ile `True`/`False`'a çevrildi. Sonuç, alt
  kümenin index'i (`in_range_df.index`) üzerinden `.loc` ile orijinal `df`'e
  geri yazıldı.
- **Teknik tuzak:** `in_range=False` satırlarda `is_anomaly_iforest` hiç
  yazılmadığı için pandas o hücreleri `NaN` bıraktı, bu da kolonun tipini
  `bool` yerine `float`'a çevirdi (`NaN` bir float değeri). `~` (değilini al)
  operatörü bu karışık kolonda `TypeError` verdi — çözüm, karşılaştırmadan
  önce sadece `in_range` satırlarını alıp `.astype(bool)` ile tipi düzeltmek.
- **Karşılaştırma sonucu (`pd.crosstab`, in_range satırlarında):** ikisi de
  normal: 42.090, ikisi de anomali: **166**, sadece bizim: 262, sadece
  IForest'in: 262. Yani bizim işaretlediğimiz 428 satırın sadece **%39'unda**
  (166/428) IForest de aynı fikirde.
- **Anlaşmazlığın anatomisi — iki grup incelendi:**
  - *Sadece bizim işaretlediğimiz (262 satır):* rüzgar ort. 10.9 m/s, teorik
    ~3186 kW beklenirken gerçek güç **medyan tam sıfır** — klasik "teoriğin
    çok altında kalma", gerçek performans kaybı.
  - *Sadece IForest'in işaretlediği (262 satır):* rüzgar ort. 20.6 m/s (çok
    yüksek, nadir görülen), gerçek güç ort. 3307 kW — **teorik değere çok
    yakın, bazen üstünde bile** (`theoretical_power_kw` std=0, hepsi platoda).
  - **Yorum:** IForest teorik eğriyi hiç bilmiyor, sadece "bu nokta rüzgar-güç
    uzayında seyrek bir bölgede mi" diye bakıyor. Yüksek rüzgar veri setinde
    nadir olduğu için IForest bu noktaları "anomali" sayıyor, oysa türbin tam
    beklendiği gibi (teorik platoda) çalışıyor. **"İstatistiksel olarak nadir"
    ile "performansı düşük" farklı kavramlar** — bir bakım alarmı için bizim
    kural tabanlı yöntemimiz (teorik eğriyi kullanan) daha güvenilir, çünkü
    IForest'in işaretlediği "anomaliler" aslında sağlıklı ama nadir anlar.
- **CEO'nun "tasarım değerlerinden sapma" kavramıyla bağlantı:** IForest'in
  mantığı bu kavramın **karşıtı** — "istatistiksel olarak ne kadar sık
  görüldüğüne" bakıyor, üreticinin belirlediği güç eğrisine hiç bakmıyor. O
  262 satırda türbin tasarımına birebir uyuyor (teorik platoda); IForest'in
  onları işaretlemesinin tek sebebi, o yıl güçlü rüzgarın nadiren esmiş
  olması — türbinin davranışıyla değil, o yılki rüzgar istatistikleriyle
  ilgili. Bir bakım mühendisine bu 262 satırı göndermek gereksiz kontrole
  (false positive) yol açardı. Kural tabanlı yaklaşımımız (üreticinin güç
  eğrisinden sapmayı ölçen) CEO'nun kastettiği kavramı IForest'ten daha
  doğru yakalıyor — bu, projenin sklearn tutorial'larından ayrıldığı nokta.
