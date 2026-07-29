# Robotik Otomasyon Müdürlüğü - Kamera Denetim Sistemi

Bu proje, bir bilgisayara bağlı kamera üzerinden QR kodların boyut, mesafe ve açı değişimlerini analiz ederek "Kapak Açık" veya "Kapak Kapalı" durumlarını tespit eden gerçek zamanlı (MJPEG) bir bilgisayarlı görü (computer vision) web uygulamasıdır.

## Proje Gereksinimleri

Sistemi başka bir bilgisayarda (veya sunucuda) çalıştırmak için aşağıdaki bileşenlerin yüklü olması gerekir:

1. **Python 3.8+** (Python'un kurulu ve sistem PATH değişkenine ekli olduğundan emin olun).
2. **Kamera (Webcam)**: Sistemin QR kodları okuyabilmesi için bilgisayara bağlı ve çalışır durumda bir USB veya dahili kamera bulunmalıdır.
3. **C++ Yeniden Dağıtılabilir (vcredist)**: Özellikle `pyzbar` kütüphanesinin Windows'ta sorunsuz çalışabilmesi için Microsoft Visual C++ 2015-2022 Redistributable paketinin yüklü olması gerekir. (Çoğu bilgisayarda varsayılan olarak yüklüdür).

## Kurulum Adımları (Adım Adım)

1. **Projeyi Bilgisayara İndirin (Clone)**
   GitHub üzerinden projeyi indirin ve terminal/komut istemcisini projenin bulunduğu klasörde (`htmlcss` klasörü) açın.

2. **Gerekli Kütüphaneleri Yükleyin**
   Projenin çalışması için gereken paketleri yüklemek adına terminale şu komutu girin:
   ```bash
   pip install -r requirements.txt
   ```
   *Not: Bu işlem `flask`, `opencv-python`, `numpy` ve `pyzbar` kütüphanelerini indirecektir.*

3. **Uygulamayı Çalıştırın**
   Terminalde aşağıdaki komutu çalıştırarak sunucuyu başlatın:
   ```bash
   python web_app.py
   ```

4. **Arayüze Erişin**
   Uygulama çalıştıktan sonra tarayıcınızı (Google Chrome önerilir) açın ve şu adrese gidin:
   ```text
   http://127.0.0.1:5000
   ```

## Kullanım Notları
* **Kamera Ayarları:** Sistem varsayılan olarak `0` numaralı kamerayı kullanır. Eğer birden fazla kamera varsa, `src/config.py` içindeki `CAMERA_SOURCE` değerini güncelleyebilirsiniz.
* **Tolerans Ayarları:** Arayüz üzerinden yeni bir otomasyon eklerken "Kamera Uzaklığı" girdiğinizde, sistem X, Y, Z ve Açı toleranslarını ideal seviyelerde otomatik olarak hesaplar.
* Tarayıcı üzerinde değişiklikleri anında görememeniz durumunda önbellek sorunu yaşıyor olabilirsiniz. Sayfayı Gizli Sekmeden veya `Ctrl+F5` ile yenileyerek açmayı unutmayın.
