Proje ve Algoritma Rehberi
Bu belge, kameradan QR kod okuyarak kapıların "Açık/Kapalı" durumunu analiz eden ve robotik sistemlere (robot köpek, robot kol, otonom araç) rehberlik eden Otomasyon Komuta Merkezi projesinin nasıl çalıştığını anlatmak için hazırlanmıştır. Hiçbir teknik bilgisi olmayan birinin bile anlayabileceği kadar sadeleştirilmiştir.

1. Bu Proje Ne İşe Yarıyor?
Düşünün ki fabrikada gezen otonom bir robot köpeğiniz veya malzeme taşıyan bir AGV (Otonom Yönlendirmeli Araç) var. Bu robotun bir dolaptan malzeme alması gerekiyor. Ancak oraya gittiğinde dolabın kapakları açık mı, yoksa kapalı mı olduğunu bilemezse kaza yapabilir.

Bu sistem; dolabın iki kapağına yapıştırılan standart QR kodlara kamerayla uzaktan bakarak:

Kapakların açık mı kapalı mı olduğunu,
Bu dolabın fabrikanın tam olarak hangi koordinatlarında (X, Y, Z) bulunduğunu robota bildirir.
2. Sistemin Kalbi: Algoritma Nasıl Çalışıyor?
Kamera, sadece QR kodları okumakla kalmaz; o kodların görüntü içindeki geometrisini inceler. Algoritmamız 4 temel adımda karar verir:

Adım 1: Merkez Noktalarını Bulma
Kamera iki ayrı QR kod tespit ettiğinde, her iki kodun da tam orta (merkez) noktalarını hesaplar.

Adım 2: Pisagor Teoremi ile İki QR Arasındaki Piksel Uzaklığını Bulma
Liseden hatırlayacağınız Pisagor Teoremi kullanılarak (A² + B² = C²), ekran üzerindeki 1. QR merkezinden 2. QR merkezine olan "Piksel uzaklığı" (uzunluğu) hassas bir şekilde ölçülür. Ancak tek başına piksel uzaklığı yanıltıcıdır, çünkü kamera dolaba yaklaşırsa pikseller büyür. İşte bu yüzden bir sonraki adıma (Oranlama) geçilir.

Adım 3: Derinlik Yanılsamasını Çözme (Genişlik Orantısı / Baseline Ratio)
Kamera dolaba yaklaşırsa QR'lar birbirinden uzaklaşıyormuş gibi görünür, kamera uzaklaşırsa QR'lar yakınlaşıyor gibi görünür (Tıpkı bir nesnenin uzaktayken küçük görünmesi gibi). Çözüm: Sistem, Adım 2'de bulduğu o ham mesafeyi, QR kodların kendi fiziksel genişliğine böler. Böylece ortaya "Kamera mesafesinden bağımsız" evrensel bir Genişlik Oranı (Ratio) çıkar. Kamera ne kadar yaklaşıp uzaklaşırsa uzaklaşsın, dolap kapalı olduğu sürece bu oran sabit kalır. Sistemi kusursuz kılan asıl sır bu orantıdır.

Adım 4: Öğrenme ve Tolerans Kontrolü
Öğrenme: Sistem bir dolaba ilk kez baktığında o anki konumu "KAPALI" kabul eder ve o oranı hafızasına kaydeder.
Tolerans: Sonraki her okumada yeni oranı hafızasındaki ile kıyaslar. Eğer kapak hafif aralanmışsa iki QR birbirinden uzaklaşmış demektir. Fark, sizin belirlediğiniz Mesafe Toleransı'nı (Örn: 0.05) aşarsa sistem anında durumu AÇIK (Aralanmış) olarak işaretler.
Açı Kontrolü: Menteşeli kapılarda kapak açıldığında QR kod yamulur (Açısı değişir). Sistem kodun en-boy oranındaki bozulmayı tespit ederek Açı Toleransı limitini aştığında kapının AÇIK (Eklemli Açılmış) olduğuna karar verir.
3. Neden X, Y ve Z Koordinatları Var?
Ekranda gördüğünüz X, Y, Z koordinatları, robot köpeğin veya otonom sistemin 3 boyutlu uzayda yönünü bulması (Navigasyon) içindir.

X Koordinatı: Fabrika zeminindeki sağ/sol düzlemi.
Y Koordinatı: Fabrika zeminindeki ileri/geri düzlemi.
Z Koordinatı: Dolabın yerden yüksekliği (Kabin yüksekliği).
Siz "Boya Kabini 1" otomasyonunu başlattığınızda, kamera kapı durumunu analiz ederken, aynı zamanda robota "Hedefine X: 15, Y: 4, Z: 2 noktalarına giderek ulaşabilirsin" mesajını da iletir.

4. Yeni Klasör ve Mimari Yapısı (React vs HTML/CSS)
Sistem artık çok daha büyük projelerde kullanılabilecek iki ayrı versiyona sahiptir. Projeyi sunarken ikisinden de bahsedebilirsiniz:

Versiyon 1: Klasik HTML/CSS (Klasör: htmlcss/)
İçerisinde web_app.py isimli yekpare bir Python dosyası barındırır. Web sayfası (HTML) ve Analiz motoru (Python) aynı sistem üzerinde çalışır. Hızlıca ayağa kalkar, basittir ve küçük sistemler için idealdir.

Versiyon 2: Modern Enterprise React (Klasör: react/)
Profesyonel şirketlerin kullandığı, iki parçalı büyük mimaridir.

Backend (Arka Uç - Python): Artık sadece analiz yapar ve API üzerinden verileri dağıtır. Kodlar (Tarayıcı, Analizör, Veritabanı) ayrı ayrı dosyalara bölünmüş, sistem çok daha hafif ve güçlü hale gelmiştir.
Frontend (Ön Yüz - React): Kullanıcı arayüzü artık sayfayı hiç yenilemeyen, çok akıcı, modern ve mobil uyumlu bir "Single Page Application" (Tek Sayfa Uygulaması) olarak baştan yazılmıştır. Büyük veri panelleri için çok daha performanslıdır.
TIP

Eğer sistemin sadece arka planda çalışmasını ve verileri başka bir robota/uygulamaya servis etmesini istiyorsanız react/backend yapısını kullanmalısınız. Eğer tek bir bilgisayardan ekrana bakarak kontrol edecekseniz htmlcss sürümü hızlıca işinizi çözecektir.

5. React Mimarisindeki Dosyalar Ne İşe Yarıyor?
react klasörüne girdiğinizde sistemin birbirine konuşan iki ayrı koldan oluştuğunu göreceksiniz. Bu dosyaların herbirinin görevi tıpkı bir fabrikadaki farklı departmanlar gibidir:

A) Arka Uç (Backend) Dosyaları (react/backend/)
Bu klasör sistemin beynidir. Görüntüyü işler ve matematiksel kararları alır.

config.py: Sistemin genel ayarlarının yapıldığı merkezdir. Hangi kameranın kullanılacağı, tolerans limitleri gibi sabit veriler burada tutulur.
database.py: Veritabanı yöneticisidir. Sistemin "öğrendiği" kapı oranlarını ve otomasyon hedeflerini data klasöründeki JSON dosyalarına kaydeder ve gerektiğinde oradan okur.
scanner.py: Kameranın "Gözü"dür. Görüntüdeki siyah-beyaz QR kodları tarar, çerçevelerini bulur ve içindeki metinleri okuyup analizöre teslim eder.
analyzer.py: Sistemin "Karar Mekanizması"dır. Tarayıcıdan (scanner.py) gelen koordinatları alır, Pisagor denklemlerini kurar ve kapının AÇIK mı KAPALI mı olduğuna karar verir.
app.py: Dış dünya ile iletişim kuran sekreterdir (API Sunucusu). Ön yüzün (React) istediği verileri verir, gönderdiği yeni otomasyonları kaydeder ve kameranın görüntüsünü web sayfasına aktarır.
B) Ön Yüz (Frontend) Dosyaları (react/frontend/src/)
Bu klasör sistemin vitrinidir. Kullanıcının tıkladığı, gördüğü arayüz bileşenlerini içerir.

App.jsx: Arayüzün ana omurgasıdır. Sayfalar arası geçişleri (Routing) kontrol eder, hangi ekrandaysak o ekranı gösterir.
index.css: Sayfanın makyajıdır. Buton renkleri, yuvarlak köşeler, yazı tipleri, tabloların tasarımları bu dosyanın içindedir.
main.jsx: Tüm React bileşenlerini toplayıp tarayıcıya (Chrome, Edge vb.) "Bu uygulamayı ekrana çiz" emrini veren motor parçasıdır.
Bileşenler (Components ve Pages)
Ön yüz, lego parçaları gibi küçük bileşenlere bölünmüştür:

components/Header.jsx: Ekranın en üstündeki lacivert, logolu "Robotik Otomasyon Müdürlüğü" isimli başlık çubuğudur.
components/BottomNav.jsx: Ekranın en altındaki "Ana Ekran" ve "Otomasyon Ekranı" sekmeleri arasında geçiş yapmamızı sağlayan menüdür.
pages/MainScreen.jsx: Sistemin kalbinin attığı yer. Sol tarafta güncel durumu ve sayıları (Açık/Kapalı), sağ tarafta ise kameranın canlı yayınını gösteren bileşendir.
pages/AutomationScreen.jsx: Yeni dolapların/hedeflerin sisteme kaydedildiği, silinebildiği, X, Y, Z koordinatlarının girildiği formları ve tabloları içeren yönetim ekranıdır.
