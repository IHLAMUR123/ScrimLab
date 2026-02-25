# 🏆 ScrimLab - League of Legends Scrim & Arena Bot

ScrimLab, League of Legends toplulukları için geliştirilmiş; scrim (takım antrenmanı), 1v1 Arena ve gelişmiş takım yönetim sistemine sahip profesyonel bir Discord botudur.

---

## ✨ Özellikler

- **🛡️ Kalıcı Yazar İmzası:** Botun geliştiricisi **IHLAMUR** olarak sisteme işlenmiştir ve güvenlik korumalıdır.
- **🎮 LoL Odaklı Yapı:** Gereksiz tüm oyunlardan arındırılmış, sadece League of Legends için optimize edilmiştir.
- **⚔️ 1v1 Arena:** Otomatik oda ismi ve şifre oluşturma sistemi ile hızlı rekabet.
- **🥇 Takım Sistemi:** Kendi takımınızı kurun, kaptanlık yapın ve istatistiklerinizi takip edin.
- **🔄 Otomatik Güncelleyici:** Bot her başladığında GitHub (IHLAMUR123/ScrimLab) üzerinden sürüm kontrolü yapar.
- **📊 Gelişmiş Veritabanı:** MMR sistemi ve maç geçmişi kayıtları.

---

## 🛠️ Kurulum Rehberi (Adım Adım)

Botu sorunsuz bir şekilde ayağa kaldırmak için aşağıdaki adımları takip edin:

### 1. Dosyaları İndirin
```bash
git clone https://github.com/IHLAMUR123/ScrimLab.git
cd ScrimLab
```

### 2. Sanal Ortam Oluşturun (Önerilir)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

### 3. Gerekli Kütüphaneleri Kurun
```bash
pip install -r requirements.txt
```

### 4. Ayarları Yapılandırın (.env)
Ana dizinde bir `.env` dosyası oluşturun ve içine şunları yapıştırın:
```env
TOKEN=Discord_Bot_Tokeniniz
TOP_GG_TOKEN=Opsiyonel_TopGG_Tokeniniz
GUILD_ID=Ana_Sunucu_IDniz
```

### 5. Botu Başlatın
```bash
python3 main.py
```

---

## 🚀 Önemli Notlar

- **Erişim Sorunu:** Eğer Türkiye'den çalıştırıyorsanız, Discord erişim engeli nedeniyle botun bağlanma sorunu (Timeout) yaşamaması için **VPN** veya **Yurt dışı lokasyonlu bir VDS** kullanmanız önerilir.
- **Güvenlik:** `core/` dizini altındaki dosyalar botun bütünlük kontrolünü sağlar. Bu dosyaların (özellikle `__credits__.py`) değiştirilmesi botun hata verip kapanmasına neden olur.

---

## 👨‍💻 Geliştirici
**IHLAMUR** tarafından özel olarak hazırlanmıştır.
GitHub: [IHLAMUR123](https://github.com/IHLAMUR123)

---
*İyi Scrim'ler!* 🎮✨
