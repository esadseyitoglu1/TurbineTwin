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

## Ben Ne Anladım — Faz 1

> **Not (süreç şeffaflığı için):** Bu bölüm normal akıştan farklı yazıldı.
> Beş soruyu tek tek kendi cümleleriyle cevaplama sürecinde (payda/`in_range`
> sıralaması üzerine iyi bir soru sorduktan sonra) yorulup "sen yaz, ben
> kontrol ederim" dedi. Kural gereği bu normalde reddedilir (tanıma ≠ hatırlama,
> mülakatta önünde bu metin olmayacak) ama tek seferlik bir esneme olarak kabul
> edildi. **İleride benzer bir "sen yaz" isteği gelirse bu esneme referans
> alınmasın** — varsayılan hâlâ "önce sen dene" olmalı.

**1. Proje ne yapıyor:** Gerçek bir rüzgar türbininin 1 yıllık SCADA verisini
kullanarak, her 10 dakikalık ölçümde **gerçek üretilen güç ile üreticinin
belirlediği teorik güç eğrisi arasındaki sapmayı** hesaplıyor. Sapma, türbinin
çalışması gereken bir rüzgar aralığındayken (cut-in/cut-out arası) yeterince
büyükse, bu satır **bakım sinyali** olarak otomatik işaretleniyor. Aynı işi
hem kendi kural tabanlı yöntemimizle hem sklearn'ün Isolation Forest'ıyla
yapıp, ikisinin nerede anlaştığını/ayrıştığını karşılaştırıyoruz.

**2. `deviation_norm` neden `deviation_rel` yerine:** `deviation_rel = (gerçek
- teorik) / teorik`'te payda (teorik değer) cut-in altında sıfıra çok yakın
veya tam sıfır oluyor — canlı olarak `NaN` (0/0) ve `inf` (sayı/0) ürettiğini
gördük. `deviation_norm = (gerçek - teorik) / 3600`'de payda sabit ve asla
sıfır olmadığı için bu patlama yapısal olarak imkânsız. Ayrıca istatistiksel
olarak da farklı bir şey ölçüyorlar: aynı 25 kW'lık mutlak kayıp, düşük
rüzgarda `deviation_rel`'i çok büyütüyor (küçük teorik değere bölündüğü için),
`deviation_norm` ise rüzgar hızından bağımsız hep aynı ağırlıkta sayıyor —
gerçek enerji kaybını daha tutarlı yansıtıyor.

**3. `in_range` neden ayrı bir kontrol:** `deviation_norm` küçük olsa bile,
büyük olsa bile, türbin zaten cut-in altında/cut-out üstünde çalışmaması
gereken bir bölgedeyse, o sapmaya güvenmiyoruz. `in_range` **olduğu için**,
türbinin tasarımı gereği kendini kapattığı anlar (örn. düşük rüzgarda sıfır
üretim) anomali sayılmıyor — `in_range & (deviation_norm < threshold)`
formülünde `in_range=False` olan satırlar otomatik `False` oluyor. Bu, "ne
kadar sapma var" (deviation_norm) ile "bu sapmaya güvenilir mi" (in_range)
sorularını ayırıyor; ikisi farklı sorular, biri diğerinin yerine geçemez.

**4. Yüzdebirlik neden ortalama-3σ yerine:** Dağılımımız çarpık — ana yığın
0'a yakın kümelenirken, -1.0'a kadar uzanan ince ama gerçek bir kuyruk var
(990 satır < -0.5). Ortalama ve σ bu kuyruktaki aşırı değerlerden etkileniyor
(σ şişiyor), bu da ortalama-3σ eşiğini gevşetiyor. Somut kanıt: yüzdebirlik
eşiği 428 satır işaretlerken (%1), ortalama-3σ **1152 satır** (%2.69) —
neredeyse 3 kat daha fazla, gerçekte alarm yorgunluğuna yol açardı. Yüzdebirlik
sıralamaya dayandığı için bu aşırı değerlerden etkilenmiyor.

**5. Isolation Forest farkı:** IForest teorik eğriyi hiç bilmiyor, sadece
rüzgar-güç noktalarının 2 boyutlu uzayda ne kadar seyrek/yoğun olduğuna
bakıyor. Bizim 428 anomalimizin sadece %39'unda (166/428) IForest de aynı
fikirde. Geri kalan 262 satırda (sadece IForest'in işaretlediği) rüzgar çok
yüksekti (~20 m/s) ama güç tam teorik platodaydı — türbin sağlıklıydı, IForest
sadece o kadar yüksek rüzgarın nadir esmesi yüzünden işaretledi. Bu, CEO'nun
"tasarım değerlerinden sapma" kavramının **karşıtı**: istatistiksel nadirlik,
tasarımdan sapmayla aynı şey değil. Bakım ekibine bu 262 satırı göndermek
gereksiz kontrole (false positive) yol açardı.

### Adım 10 (devamı) — Sanity testleri

- `pytest` venv'e kuruldu (`requirements.txt`'e eklendi) — Faz 1 boyunca ilk
  kez venv'in izolasyonu gerçekten fark yarattı: paket sadece proje içinde,
  global Python'a bulaşmadı.
- 3 test yazıldı (`tests/test_deviation.py`): sıfıra yakın teorik → `inf`
  üretmemeli, cut-in altı asla `is_anomaly=True` olmamalı, teoriğe tam uyan
  satırda sapma = 0.
- **Test yazarken gerçek bir hata bulundu:** ilk test tek satırlık bir sahte
  veri (`theoretical_power_kw=0.0`) ile yazıldığında **başarısız oldu** —
  çünkü `add_normalized_deviation()`, `RATED_POWER`'ı `theoretical_power_kw
  .max()` ile hesaplıyor, ve tek satırlık veride bu `.max()` de `0.0` çıkıp
  `RATED_POWER=0` oluyor, aynı `inf` hatasını farklı bir açıdan yeniden
  üretiyor. Düzeltme: fixture'a anma-gücünde ikinci bir satır eklendi.
  **Ders:** `RATED_POWER`'ı veriden türetmek (Adım 5'in kararı) gerçek,
  büyük veri setinde güvenli ama **küçük/izole test verisinde gizli bir
  varsayım** taşıyor — "en az bir satırda teorik değer anma gücünde olacak."
  Bu varsayım testte açıkça görünür hale geldi.
- **README.md profesyonel hale getirildi** (İngilizce, başvuru için sunum
  metni): proje açıklaması, tasarım kararlarının kısa gerekçesi, kurulum/
  çalıştırma talimatları (PowerShell ile canlı test edildi), üç grafiğin
  gömülü hali, proje yapısı. `NOTLAR.md`'den farkı: README sonuç odaklı ve
  dışarıdan bakan biri için, `NOTLAR.md` süreç odaklı ve mülakat savunması
  için — ikisi farklı okuyucuya hizmet ediyor.

## Faz 1 tamamlandı

10 adım, 19 commit, 3 grafik, 3 sanity test. Sıradaki: Faz 2 (FastAPI ile
veriyi "canlı akıyormuş gibi" stream eden servis).

## Faz 2 — Backend (FastAPI Streaming Servisi)

### Adım 2.1 — Web Sunucusu ve API Kavramları

Faz 1'de yazdığımız her şey bir **kütüphaneydi (library)**. Fonksiyonları yazdık, `run_phase1.py` içinde *biz* çağırdık, çalıştı, grafikleri üretti ve program kapandı.
Faz 2'de ise bu fonksiyonları bir **API (Application Programming Interface)** haline getireceğiz. Yani kodumuzu **başkası** (bir web tarayıcısı, başka bir program vb.) çağıracak.

Bunu yapmak için bir **Web Sunucusu (Web Server)** kuracağız. Temel kavramlar:

- **İstemci (Client) ve Sunucu (Server):** Tarayıcı (veya Faz 3'te yazacağımız arayüz) istemcidir. Bizim FastAPI uygulamamız sunucudur. İstemci sorar, sunucu cevaplar.
- **Sunucunun doğası:** Unity'deki oyun döngüsüne (`while(true)` / `Update()`) çok benzer. Ancak Unity kare hızına (fps) göre dönerken, web sunucusu ağ isteklerine (network requests) göre döner. Program hiç kapanmaz, sürekli açıktır, belli bir **portu** (örneğin 8000) dinler ve ağdan bir istek gelene kadar bekler.
- **İstek (Request) ve Yanıt (Response):** İstemci bir istek gönderir. İsteğin bir adresi (Path: `/api/health`) ve türü (Method: `GET`) vardır. Sunucu ilgili kodu çalıştırır ve bir yanıt döndürür.
- **Port ve 127.0.0.1:** 127.0.0.1 (localhost) kendi bilgisayarın anlamına gelir. IP adresini bir apartman olarak düşünürsek, Port (örn. 8000) o apartmandaki daire numarasıdır.
- **HTTP Durum Kodları (Status Codes):** Yanıtın nasıl sonuçlandığının özetidir. 200 = Her şey yolunda, 404 = Sayfa bulunamadı, 422 = Geçersiz veri gönderildi, 500 = Sunucuda hata (bizim kodumuz patladı).
- **JSON (JavaScript Object Notation):** Veri taşıma formatıdır. Python dict'lerine çok benzer ama dilden bağımsızdır.
- **Uvicorn ve FastAPI iş bölümü:** Sunucu iki parçadır. `uvicorn` kapıcıdır, ağı dinler ve gelen paketleri karşılar. `FastAPI` ise yöneticidir, "bu paket `/api/health` adresine gelmiş, şu fonksiyonu çalıştırayım" diyerek yönlendirme (routing) yapar.

### Adım 2.2 — FastAPI Kurulumu ve İlk Endpoint

- `pip install fastapi` ile pakedi kurduk. Hatırlarsan Adım 0'da sanal ortamı `--system-site-packages` ile kurmuştuk. Pandas/Numpy gibi paketler globalden gelirken, FastAPI direkt olarak bizim sanal ortamımıza (veya sistem izolasyonuna göre user site-packages'a) güvenle yüklendi.
- `src/turbinetwin/api.py` dosyasını oluşturduk. İçinde türbinle ilgili hiçbir şey yok; amacımız sunucunun ayaklanabildiğini görmek.
- **`@app.get(...)` Dekoratorü (Decorator):** Bu, Python'da var olan bir fonksiyona "sen artık `/api/health` adresine gelen GET isteklerine cevap vereceksin" deme yöntemidir. C# (Unity) dünyasındaki `[HttpGet("/api/health")]` attribute'una çok benzer. Dekoratorü kaldırırsak Python fonksiyonu hâlâ orada durur, ama web sunucusu ona giden yolu unutur.
- **`async` kullanmadık:** Şu anki fonksiyonumuz düz `def health_check()`. FastAPI senkron fonksiyonları da harika yönetir. `async` (eşzamanlılık) kavramını gereksiz yere baştan eklemedik, Adım 2.7'de stream yaparken gerçek bir işe yaradığında kullanacağız.
- **Otomatik JSON Dönüşümü:** Fonksiyonumuz sadece bir Python sözlüğü (`{"status": "ok"}`) döndürüyor. FastAPI bunu otomatik olarak JSON metnine çevirip tarayıcıya yollar. İstemci tarafındaki biri Python bilmese bile JSON'ı anlayabilir.

### Bilinçli kapsam dışı: gerçek zamanlı veri kabulü

- Şu anki API bir **replay** (yeniden oynatma) sistemi — 2018'e ait, zaten
  tamamlanmış veriyi zaman sırasına göre "canlıymış gibi" sunuyor. Gerçek bir
  türbinden sürekli yeni ölçüm gelen (örn. her 10 dakikada bir) bir sisteme
  genişletme fikri değerlendirildi ve **bilinçli olarak kapsam dışı bırakıldı**.
- **Sebep:** `STATE`'i (Adım 2.3'te kuracağımız bellek-içi veri) yazılabilir
  hale getirmek, eşzamanlılık (concurrency) sorununu açar — her istek onu
  okurken, veri giren bir işlem aynı anda ona yazmaya çalışırsa çakışma riski
  oluşur. Bunu doğru çözmek kilitleme mekanizmaları veya bir mesaj kuyruğu
  (Kafka/RabbitMQ gibi) gerektirir — prototip ölçeğinin belirgin şekilde
  ötesinde, gerçek altyapı işi.
- **Karar tarzı:** CARE to Compare veri setini araştırıp T1.csv lehine
  reddetmemizle aynı desen — "düşünmedik" değil, "düşündük, ölçtük/tarttık,
  bilinçli olarak dışarıda bıraktık." README'ye de "Future Work" bölümü
  olarak eklendi, başvuru sırasında görünür olsun diye.

### Adım 2.3 — Veriyi başlangıçta bir kez yükle (`lifespan`)

- `@asynccontextmanager` ile `lifespan(app)` fonksiyonu yazıldı. **`yield`
  satırının öncesi Unity'nin `Awake()`'i gibi** — sunucu ayağa kalkarken bir
  kez çalışıyor: Faz 1'in tüm zinciri (`load_raw` → `add_normalized_deviation`
  → `add_operating_state` → `derive_threshold` → `flag_anomalies` →
  `run_isolation_forest`) burada işleniyor, sonucu `STATE` adlı modül
  seviyesi bir dict'e yazılıyor. `yield`'den sonrası sunucu kapanırken
  çalışan temizlik kodu.
- `STATE` bilinçli olarak düz bir Python dict — `Map<string, object>` gibi
  düşünülebilir. `app.state` (FastAPI'ye özgü, tipsiz) ve `Depends`
  (dependency injection, bu ölçekte karşılıksız ek kavram) reddedildi.
- **Isolation Forest başlangıçta çalıştırılıyor** (ölçülen maliyet ~0.4s,
  bedava) ama API yanıtında **yer almayacak** — Adım 2.5'te bilerek `STATE`
  içinde tutulup NaN duvarına canlı çarpılacak, sonra bir tasarım kararı
  olarak (geçici çözüm değil) yanıttan çıkarılacak.
- **Canlı doğrulama:** sunucu ayağa kaldırılıp `/api/health`'e istek atıldı,
  yanıt `{"status":"ok","rows_loaded":50530}` — `lifespan`'in gerçekten
  çalıştığının ve `STATE`'in dolduğunun kanıtı.
- **Araç notu:** Bash arka plan job + `curl` kombinasyonu Windows'ta stdout'u
  güvenilir yakalayamadı (boş çıktı); Python'un kendi `subprocess.Popen` +
  `urllib.request`'i ile, **mutlak yol** ve doğru `cwd` vererek test edildi.
  Göreli yol (`.venv/Scripts/python.exe`) `subprocess.Popen`'de
  `FileNotFoundError` verdi — bash'in `cd` ile değiştirdiği çalışma dizini,
  Windows'un `CreateProcess` API çağrısına farklı şekilde ulaşıyor.

### Adım 2.4 — Pencere endpoint'i, planı düzelten canlı bulgu

- `/api/window?start=0&limit=100` eklendi: `start`/`limit` query parametreleri
  (tip ipucu → otomatik doğrulama), `.iloc[start:start+limit]`,
  `.to_dict(orient="records")`.
- **Planımızın yanıldığı nokta:** `pd.Timestamp`'in JSON'a çevrilemeyeceği için
  çökeceğini bekliyorduk. **Çökmedi.** Sebebi canlı incelendi: `pd.Timestamp`,
  Python'un yerleşik `datetime.datetime` sınıfından türetilmiş
  (`isinstance(ts, datetime)` → `True`), ve FastAPI'nin kendi
  `jsonable_encoder`'ı bu tipi tanıyıp otomatik olarak ISO-8601 string'ine
  çeviriyor (`2018-01-01T00:00:00`). Düz `json.dumps()` bunu yapamazdı
  (Adım 2.0'da test etmiştik) ama FastAPI'nin sarmalayıcısı daha akıllı.
- **Gerçek çökme, beklenen yerden değil `is_anomaly_iforest`'ten geldi:**
  `?start=384&limit=1` (cut-in altı bir satır, Faz 1'den biliniyor) istendiğinde
  sunucu **500 Internal Server Error** verdi: `ValueError: Out of range float
  values are not JSON compliant: nan`.
- **Bu, planlanan NaN tuzağının aynısı ama farklı bir katmanda yakalandı:**
  düz `json.dumps()` NaN'ı sessizce geçersiz JSON'a çevirir (`{"v": NaN}`,
  daha önce doğrulanmıştı); FastAPI'nin kendi serileştiricisi ise NaN'ı görünce
  **hata fırlatıyor** (muhtemelen `allow_nan=False` ile çağırıyor). Yani FastAPI
  bizi sessiz bozukluktan koruyor ama yine de biz bu hatayı çözmek zorundayız —
  ders aynı kalıyor (`is_anomaly_iforest`'i yanıttan çıkarmak, Adım 2.5), sadece
  hatanın *nerede* ortaya çıktığı planımızdan farklı çıktı. **Ders:** varsayımı
  ("X çökecek") canlı test etmeden plana yazmak riskli — gerçek davranış bazen
  kütüphanenin kendi iç güvenlik ağı yüzünden farklı bir yerden patlıyor.

### Adım 2.5 — Serileştirmeyi elle düzelt (SEN YAZDIN)

- `src/turbinetwin/serialization.py` → `row_to_dict(row)`: 7 alan
  (`timestamp`, `wind_speed`, `active_power_kw`, `theoretical_power_kw`,
  `deviation_norm`, `in_range`, `is_anomaly`) elle seçilip döndürülüyor.
  `is_anomaly_iforest` **bilerek dışarıda** — Faz 1'de zaten "analiz artefaktı,
  canlı ikiz sinyali değil" kararı verilmişti, bu da Adım 2.4'teki 500 hatasını
  aynı anda çözüyor (bir tasarım kararının yan etkisi, geçici çözüm değil).
- **`bool(row["in_range"])` neden gerekli — canlı doğrulandı:**
  `np.bool_(True)` ile `bool(np.bool_(True))` **aynı değeri** taşıyor
  (`True == True`) ama **farklı tipte**: `numpy.bool` vs `bool`. `json.dumps`
  sadece Python'un kendi yerleşik tiplerini tanıyor; `np.bool_` üzerinde
  `TypeError` verirken, `bool(...)`'a çevrilmiş hali `{"v": true}` üretiyor.
  `bool(...)` çağrısı **sayıya çevirmiyor** (1/0 değil), sadece numpy'nin özel
  kutusundan Python'un standart kutusuna taşıyor.
- **`wind_speed`/`active_power_kw` gibi float alanlar elle `float(...)`'a
  çevrilmedi** — Adım 2.0'da zaten `np.float64`'ün `json.dumps`'ta sorunsuz
  çalıştığı doğrulanmıştı, `np.bool_`'un aksine.
- `get_window` içinde `.to_dict(orient="records")` yerine
  `[row_to_dict(row) for _, row in rows.iterrows()]` kullanıldı. `.iterrows()`
  bir DataFrame'in satırları üzerinde `(index, row)` çiftleri olarak dönmeyi
  sağlıyor; index kullanılmadığı için `_` ile işaretlendi.
- **Canlı doğrulama:** hem normal bir satır (0-2) hem de daha önce 500
  hatası veren cut-in altı satır (384, `in_range=false`) test edildi —
  **ikisi de artık 200 OK**, NaN kaynaklı çökme tamamen ortadan kalktı.

### Adım 2.6 — Pydantic yanıt modeli

- `src/turbinetwin/schemas.py` → `TurbinePoint(BaseModel)`: 7 alan, C#/Java
  DTO'suna birebir benzeyen bir tipli sınıf. `@app.get("/api/window",
  response_model=list[TurbinePoint])` ile FastAPI'ye "bu endpoint'in
  döndürdüğü her şey bu şemaya süzülsün" dendi.
- **`bool(row["in_range"])` gibi elle dönüşümler `serialization.py`'den
  kaldırıldı** — Pydantic, `np.bool_`'u otomatik olarak Python `bool`'una
  çeviriyor. Canlı doğrulandı: `bool(...)` sarmalaması olmadan bile yanıtta
  `in_range`/`is_anomaly` doğru şekilde `true`/`false` çıktı.
- **`deviation_pct` = `deviation_norm * 100`** — brief "sapma yüzdesi" istediği
  için API sözleşmesi, iç kolon adından (`deviation_norm`) bilerek farklı.
  Canlı doğrulandı: `deviation_norm=-0.0100781` iken `deviation_pct=-1.0078`.
- **`is_anomaly_iforest` hâlâ yanıtta yok** — ama artık sadece bizim onu
  `row_to_dict()`'e eklemememize değil, `TurbinePoint` şemasında hiç
  tanımlanmamasına bağlı: yanlışlıkla `row_to_dict()`'e eklense bile,
  Pydantic onu şemada olmadığı için sessizce **filtreler**, sızdırmaz.
- **`/openapi.json` üzerinden doğrulandı:** `TurbinePoint` şeması tam olarak
  7 alanı, tiplerini (`string`/`number`/`boolean`) ve `required` listesini
  içeriyor — `/docs` (Swagger UI) bunu görsel bir tablo olarak render edecek.

### Adım 2.7 — SSE Stream + Async Generator

- `event_generator()`: `async def` + `yield` ile bir **async generator**
  yazıldı — her satırda bir `TurbinePoint` üretip SSE formatında
  (`data: {...}\n\n`) yolluyor, sonra `await asyncio.sleep(1)` ile "bekliyorum,
  event loop başka işe baksın" diyor. `/api/stream` endpoint'i bunu
  `StreamingResponse(..., media_type="text/event-stream")` ile sarmalıyor.
- **`yield`'in iki farklı kullanımı ayrıştırıldı:** Adım 2.3'teki `lifespan`
  içinde `yield` **bir kez** duruyordu (başlangıç/bitiş ayırıcı); burada
  **her satırda bir kez**, tekrar tekrar duruyor (generator). Aynı anahtar
  kelime, farklı bağlamda farklı iş görüyor.
- **Canlı doğrulama 1 — artımlı akış:** stream'in ilk 3 satırı okunup varış
  zamanları ölçüldü: `0.02s`, `1.04s`, `2.05s` — satırlar gerçekten ~1 saniye
  arayla geliyor, tek seferde dökülmüyor.
- **Canlı doğrulama 2 — event loop kilitlenmiyor:** stream bağlantısı açık
  tutulurken (arka plan thread'inde), aynı anda `/api/health`'e istek atıldı
  ve **0.001 saniyede** cevap geldi. Bu, `await asyncio.sleep(1)`'in event
  loop'u bloklamadığının somut kanıtı — `time.sleep(1)` kullansaydık bu istek,
  stream'in beklemesi bitene kadar askıda kalırdı.
- `point.model_dump_json()` — Adım 2.6'da FastAPI'nin `response_model=` ile
  otomatik yaptığı JSON dönüşümünü, burada (SSE formatını elle kurduğumuz
  için) kendimiz çağırıyoruz. `TurbinePoint(**row_to_dict(row))` ile önce
  gerçek bir Pydantic nesnesi oluşturup sonra JSON'a çeviriyoruz.

### Adım 2.8 — Hız kontrolü

- `config.py`'ye `SIMULATED_INTERVAL_SECONDS = 1.0` eklendi. `event_generator`,
  `interval = SIMULATED_INTERVAL_SECONDS / speed` formülüyle bekleme süresini
  hesaplıyor; `/api/stream?speed=1|10|100`.
- **Planımız `Literal[1, 10, 100]` kullanmayı öngörmüştü, ama canlı test
  bunun çalışmadığını gösterdi:** Pydantic 2.13.4, query parametresinden gelen
  string `"10"`'u int-tipli `Literal` üyelerine **otomatik çevirmiyor** —
  hem FastAPI üzerinden hem doğrudan Pydantic'e karşı test edilip doğrulandı
  (`Test(speed="10")` bile `ValidationError` veriyor: "Input should be
  1, 10 or 100", `input_type=str`). `Query(default=1)` ile sarmalamak da
  sorunu çözmedi.
- **Çözüm:** `speed: int = 1` (normal int, otomatik string→int dönüşümü
  çalışıyor) + elle yazılmış bir kontrol: `if speed not in (1, 10, 100):
  raise HTTPException(422, ...)`. Aynı sonucu (422) veriyor ama doğrulamayı
  kütüphaneye değil bizim kodumuza bırakıyor. **Ders:** planlanan bir kütüphane
  davranışını canlı doğrulamadan güvenmek riskli — burada iki farklı yaklaşım
  (Literal, Query) denenip ikisi de beklendiği gibi çalışmayınca üçüncü,
  garantili bir yola geçildi.
- **Canlı ölçüm — `speed=10`:** satırlar arası gerçek süre ~0.11-0.12s
  (teorik: 0.1s) — yakın.
- **Canlı ölçüm — `speed=100`, planlanan Windows zamanlayıcı sınırı
  doğrulandı:** teorik bekleme `1/100 = 0.01s` iken, **gerçek ortalama
  0.0186s** ölçüldü (ilk birkaç değer daha yüksek, sonra ~0.015s'de
  kararlılaştı) — yaklaşık **%86 daha yavaş**, tam olarak Windows'un ~15ms
  zamanlayıcı çözünürlüğü sınırına denk geliyor. Yani `speed=100` pratikte
  gerçek 100x değil, ~54x civarı bir hızlanma sağlıyor. Teoriyle tam
  uyuşmayan, ölçülüp dürüstçe kaydedilen bir bulgu.
- `speed=7` gibi geçersiz bir değer canlı test edildi, `422` ve açıklayıcı
  mesaj (`"speed must be one of (1, 10, 100)"`) doğrulandı.

### Adım 2.9 — Faz 2'yi kapatma: bağımlılıklar, testler, README

~5 haftalık bir aradan sonra fark edildi: `requirements.txt` hâlâ sadece
Faz 1'in paketlerini listeliyordu (`fastapi`/`uvicorn`/`pydantic`/`httpx`
eksikti) — yani repoyu klonlayan biri `pytest tests/` bile çalıştıramazdı.
Üç iş yapıldı:

- **`requirements.txt`** güncellendi: `fastapi`, `uvicorn`, `pydantic`,
  `httpx` (test-only, `TestClient` bunu gerektiriyor) eklendi.
- **`tests/test_api.py`** eklendi (`/api/health`, `/api/window`, `/api/stream`
  için 6 test). **Canlı bulgu:** `client.stream(...)`'in `with` bloğundan
  çıkmak — `iter_lines()` hiç çağrılmasa bile — `TestClient`'ın altındaki
  taşıyıcının response'u kapatmak için generator'ı **tüketmeye** çalışmasına
  yol açıyor. `event_generator` tüm veri setini (~50.530 satır) dolaştığı
  için `speed=100`'de bile bu dakikalar sürer ve test asılı kalır (üç kez
  yaşandı, süreç elle sonlandırıldı). **Çözüm:** stream'i hiç HTTP/ASGI
  katmanından tüketmemek — `stream_data()` ve `event_generator()`
  fonksiyonlarını `asyncio.run()` ile **doğrudan** çağırıp `__anext__()` ile
  tek bir kayıt çekmek. Bu hem `StreamingResponse`'un `media_type`'ını hem
  gerçek bir SSE satırının üretildiğini doğruluyor, generator'ı hiç
  sonuna kadar tüketmeden. **Ders:** bir generator'ı test ederken "sadece
  ilk elemanı okuyorum" sanmak yetmez — sarmalayan taşıyıcının (burada
  TestClient) kapanışta ne yaptığını da hesaba katmak gerekiyor.
- **README** güncellendi: `## API server` bölümü eklendi (`uvicorn` ile
  çalıştırma, üç endpoint'in özeti), `## Status` Faz 2'yi tamamlandı olarak
  işaretliyor, sıradaki Faz 3 (istemci tarafı) olarak güncellendi.
- **Doğrulama:** `pytest tests/` → 9/9 geçti, 5.13s.

## Faz 2 tamamlandı

8 alt-adım (2.1–2.8) + kapanış (2.9), toplamda backend artık hem çalışıyor
hem test edilmiş hem çalıştırılabilir durumda. Sıradaki: Faz 3 (dashboard /
istemci tarafı arayüz, `/api/stream`'i tüketip canlıymış gibi görselleştiren).

## Faz 3 — Dashboard (Vanilla JS, build adımı yok)

**Karar:** React değil. Bu ölçekte (1 sayfa, 1 veri kaynağı, birkaç görsel
eleman) React'ın çözdüğü problem — çoklu bileşen arası state yönetimi — hiç
yok; backend zaten tek state kaynağı (`STATE`). `EventSource` tarayıcının
yerleşik SSE istemcisi, hiçbir kütüphane gerektirmiyor. Faz 1/2'deki
"karmaşıklığı sadece gerekçesi varsa ekle" deseniyle aynı karar tarzı
(IForest karşılaştırmasında da görüldüğü gibi, daha gelişmiş araç otomatik
olarak daha doğru cevap vermiyor).

### Adım 3.1 — Statik dosya servisi

- `static/index.html` (yer tutucu) oluşturuldu, `src/turbinetwin/api.py`'ye
  `app.mount("/", StaticFiles(directory=PROJECT_ROOT / "static",
  html=True), name="static")` eklendi.
- **Sıra bilinçli olarak son:** mount, tüm `/api/*` route'larından **sonra**
  tanımlandı. FastAPI route'ları kayıt sırasına göre eşleştiriyor — `/` bir
  mount ile en başta tanımlansaydı, ondan sonra gelen her `/api/*` isteği de
  bu mount'a düşüp 404 (statik dosya olarak `api/health` aranıp
  bulunamayacağı için) verebilirdi. Bu yüzden mount dosyanın en altına,
  `stream_data`'dan sonraya konuldu.
- `html=True`: `/` isteği otomatik olarak `static/index.html`'e çözülüyor,
  elle bir `@app.get("/")` yazmaya gerek kalmadı.
- **Same-origin, CORS yok:** sayfa da API de aynı `uvicorn` sürecinden,
  aynı origin'den (`127.0.0.1:8123`) servis ediliyor. Bu yüzden sayfadaki
  JS'in `/api/stream`'e `EventSource` ile bağlanması için CORS ayarı
  (`CORSMiddleware`) gerekmiyor — farklı bir origin'den (örn. ayrı bir
  frontend sunucusu, `localhost:3000` gibi) servis edilseydi gerekirdi.
- **Canlı doğrulama:** `uvicorn` `subprocess.Popen` ile ayağa kaldırıldı
  (Adım 2.3'teki gibi mutlak yol + doğru `cwd` ile), hem `/` (200,
  `text/html`, sayfa içeriği doğru) hem `/api/health` (200,
  `{"status":"ok","rows_loaded":50530}`) test edildi — mount'un `/api/*`
  route'larını gölgelemediği kanıtlandı.
- Mevcut 9 test (`pytest tests/`) hâlâ geçiyor — statik dosya değişikliği
  API davranışını bozmadı.

### Adım 3.2 — Canlı güç eğrisi grafiği

- `static/index.html` gerçek içerikle dolduruldu: Chart.js (CDN'den,
  `<script src="https://cdn.jsdelivr.net/...">`, `npm install` yok) ile
  çizilen bir çizgi grafik, `EventSource` ile `/api/stream?speed=10`'a
  bağlanıp her `data:` olayında ölçülen ve teorik gücü grafiğe ekliyor.
- **`EventSource` neden tercih edildi:** SSE için tarayıcının **yerleşik**
  istemcisi — `fetch`/websocket kütüphanesi gibi bir şey kurmaya gerek
  yok. `onmessage` callback'i her `data: ...\n\n` bloğunda otomatik
  tetikleniyor, bağlantı koptuğunda **kendiliğinden yeniden bağlanmayı da**
  deniyor (bizim elle yazmadığımız bir davranış).
  - **`MAX_POINTS = 120` ile kayan pencere:** stream ~50.530 satırı
    oynatıyor; grafiğin veri dizisini sınırsız büyütmek tarayıcının kendi
    render döngüsünü zamanla durma noktasına getirirdi. Her yeni noktada
    en eski nokta `shift()` ile atılıyor — sabit boyutlu bir "kayan pencere"
    (rolling window).
- **`chart.update("none")` ve `options.animation: false`:** Chart.js
  varsayılan olarak her güncellemeyi animasyonla çiziyor. `speed=10`'da
  saniyede birkaç nokta geldiği için her birini animasyonla kaydırmak
  gereksiz iş — kapatılınca grafik anında güncelleniyor, CPU'yu boşuna
  meşgul etmiyor.
- **Same-origin doğrulandı:** sayfa da API de aynı `uvicorn` sürecinden
  (`app.mount` Adım 3.1) servis edildiği için `EventSource("/api/stream")`
  göreli bir yol — CORS ayarı hiç gerekmedi.
- **Canlı doğrulama:** sunucu ayağa kaldırılıp (1) `/`'in döndürdüğü HTML
  içinde hem `chart.umd.min.js` referansının hem `EventSource` çağrısının
  bulunduğu, (2) `/api/stream?speed=100`'den okunan ilk iki satırın
  sayfanın beklediği alan adlarıyla (`timestamp`, `active_power_kw`,
  `theoretical_power_kw`) birebir eşleştiği doğrulandı. Tarayıcı içi
  render (grafiğin görsel olarak doğru çizilmesi) bu ortamda test
  edilemedi — bir sonraki adımda tarayıcıda elle kontrol edilmeli.
- Mevcut 9 test hâlâ geçiyor — bu adım sadece `static/`'i değiştirdi,
  backend'e dokunmadı.
