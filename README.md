
Proje OpenCV ve Python kullanılarak geliştirilmiş olup; sürgülü (yana kayan) veya menteşeli (eklemli) her türlü kapı mekanizmasında %100 otonom çalışacak şekilde "Ölçekten Bağımsız (Scale-Invariant)" ve "Öğrenen (Commissioning)" bir mimariyle tasarlanmıştır.
## 🚀 Temel Özellikler
- **Tam Otonom Öğrenme (Commissioning):** Robot, bir dolabı hayatında ilk kez görüyorsa o anki durumunu (kapalı referansını) öğrenir ve yerel veritabanına (`baselines.json`) kaydeder. Sonraki geçişlerinde bu referansı kullanır. İşçilerin QR kodları yapıştırma mesafesi veya hataları sisteme etki etmez.
- **Ölçekten Bağımsızlık (Scale-Invariant):** Robotun dolaba 1 metre veya 5 metre uzakta olması fark etmez. Sistem piksel saymaz, geometrik oranları (Mesafe / QR Genişliği) kullanır.
- **Perspektif Bağımsızlığı:** Menteşeli kapılar açıldığında oluşan açı bozulmaları ve perspektif çarpılmaları anında tespit edilir.
- **Titreme Engelleyici (Temporal Smoothing):** Kamera titremeleri veya ışık parlamalarından kaynaklanan anlık hataları engellemek için son 15 karenin sonucunu oylayarak (debounce) kararlı bir çıktı verir.
## 🧠 Sistemin Çalışma Mantığı
Sistem temel olarak iki kapağa yapıştırılmış iki farklı QR kod (Örn: `https://a.com` ve `https://b.com`) üzerinden çalışır.
1. **Öğrenme Aşaması (Devreye Alma):**
   - Robot iki QR kodu okur ve aralarındaki piksel mesafesini QR kodların ortalama genişliğine böler. Bu sayede robota uzaklıktan bağımsız sabit bir **"Mesafe Oranı"** elde edilir.
   - Kod içerikleri (`a.com` ve `b.com`) anahtar kelime yapılarak bu oran `baselines.json` dosyasına kaydedilir.
2. **Denetim (Otonom Devriye) Aşaması:**
   - Robot aynı kabine tekrar geldiğinde anlık oranı hesaplar ve JSON dosyasındaki orijinal oran ile karşılaştırır.
   - **Sürgülü Kapı Kontrolü:** Oran referanstan %15 (tolerans) daha büyükse, kapak yana kaymış demektir -> `AÇIK (Aralanmış)`
   - **Menteşeli Kapı Kontrolü:** QR kodun "En-Boy Oranı" 1.0'dan farklıysa (yamulmuşsa), kapak dışa doğru açılmış demektir -> `AÇIK (Eklemli Açılmış)`
   - **Görünürlük Kontrolü:** QR kodlardan biri kameranın açısından çıkmış veya kapanmışsa -> `AÇIK (Eksik QR)`
## 📂 Kod Yapısı ve Dosyaların İşlevleri
Sistem Endüstriyel Sınıf (Industrial Grade) prensiplerine ve Nesne Yönelimli Programlama (OOP) standartlarına uygun olarak modüllere ayrılmıştır:
* `src/main.py`: Projenin ana döngüsüdür. Kamerayı açar, görüntüleri çeker, analizöre gönderir ve sonuçları arayüze (ekrana) çizer.
* `src/config.py`: Tüm sistem ayarlarının (kamera ID'si, tolerans yüzdeleri, yazı boyutları vb.) merkezi olarak tutulduğu yapılandırma dosyasıdır.
* `src/analyzer.py`: Sistemin beynidir. Matematiksel hesaplamaları (merkez bulma, oran hesaplama, json veritabanına kayıt etme ve okuma) ve karar algoritmalarını barındırır. Titreme önleyici tampon burada çalışır.
* `src/qr_detector.py`: OpenCV'nin dahili `QRCodeDetector` sınıfını sarmalayan, kare içindeki QR kodların konumlarını (points) ve içeriklerini (data) çıkaran modüldür.
* `src/camera.py`: Kamera bağlantısını yönetir. Video dosyasından veya canlı webcam'den (`cv2.VideoCapture`) güvenli okuma yapar.
* `src/logger.py`: Endüstriyel sistemler için arka planda çalışan olayları, hataları ve "YENİ KABİN ÖĞRENİLDİ" gibi bilgileri konsola yazdıran loglama modülüdür.
* `src/baselines.json`: Robotun sahada öğrendiği kabinlerin referans oranlarını otomatik olarak kaydettiği yerel veritabanı dosyasıdır. (İlk çalışmada otomatik oluşur).
## 🛠️ Kurulum ve Kullanım
1. Gerekli kütüphaneyi kurun:
   ```bash
   pip install opencv-python numpy
   ```
2. Projeyi çalıştırın:
   ```bash
   python src/main.py
   ```
3. Test için kapaklara içerikleri birbirinden farklı 2 adet kare formda QR kod yapıştırın (Etrafında beyaz boşluk/quiet zone bırakmayı unutmayın).
4. Sistemi kapatmak için ekrandayken `Q` tuşuna basın.
