# Changelog

## 1.2.0

### Eklendi
- `automatic_backup.sh`: WAL-güvenli SQLite online yedek, saklama süresi ve `--docker` modu.
- `backup.ps1`: aynı davranışın Windows sürümü (gzip, saklama süresi).
- `assets/flow.svg`: 5v5 akış diyagramı.
- `assets/setup.gif`: gerçek `build.bat` çıktısından üretilen kurulum animasyonu.
- README: yedekleme bölümü, geri yükleme ve cron örneği.
- README: katlanabilir İngilizce özet (uluslararası görünürlük için).

### Değişti
- Sürüm 1.2.0.
- `.gitignore`: `backups/`.

## 1.1.0

Yayın temizliği. Davranış aynı, yapılandırma dışarı taşındı.

### Eklendi
- `core/config.py`: tüm guild / kanal / rol / emoji ID'leri ortam değişkeninden okunur.
- `LICENSE` (MIT), `version.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`.
- `tests/test_config.py` ve GitHub Actions CI (compile + pytest).
- `build.bat` (tek tık kurulum) ve `start.bat` (başlatma).
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
- Python 3.15 uyumluluğu: `aiohttp>=3.14.5`, `pillow>=13`, `audioop-lts` (3.13+) ve
  disnake 2.7 için event-loop shim'i. `topggpy` kaldırıldı; top.gg gönderimi artık
  doğrudan HTTP ile yapılıyor (discord.py bağımlılığı tamamen kalktı).
- `build.bat` uçtan uca test edildi: venv → bağımlılıklar → config → derleme → testler.
