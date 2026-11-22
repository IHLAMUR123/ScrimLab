# Changelog

## 1.1.0

Yayın temizliği. Davranış aynı, yapılandırma dışarı taşındı.

### Eklendi
- `core/config.py`: tüm guild / kanal / rol / emoji ID'leri ortam değişkeninden okunur.
- `LICENSE` (MIT), `version.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`.
- `tests/test_config.py` ve GitHub Actions CI (compile + pytest).
- README: kurulum, Docker, yapılandırma tablosu, lisans ve krediler.

### Değişti
- Veritabanı: her sorguda yeni bağlantı yerine tek paylaşılan bağlantı, WAL ve `busy_timeout`.
- `check_testmode` artık parametreli sorgu kullanıyor.
- Bot token'ı yoksa başlangıçta anlaşılır hata veriyor.
- Güncelleme kontrolü yalnızca HTTP 200'de yorum yapıyor.

### Kaldırıldı
- `core/__credits__.py` içindeki "bütünlük kontrolü" (yazar adı değişince botu durduran kontrol).
- `discord.py` bağımlılığı (proje `disnake` kullanıyor).
- `package-lock.json` (Python projesinde gereksiz).

### Notlar
- `WARNING_ROLE_ID` varsayılanı `0` (devre dışı). Eski kod buraya yanlışlıkla bir kanal ID'si yazıyordu.
- Emoji ID'leri sizin sunucunuza ait değilse `.env` üzerinden değiştirin ya da unicode kullanın.
