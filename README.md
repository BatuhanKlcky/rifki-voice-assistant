<div align="center">
  
# 🤖 RIFKI
**AI-Powered Desktop Assistant**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-UI%20Framework-brightgreen)](https://pypi.org/project/PyQt5/)
[![Google Gemini API](https://img.shields.io/badge/Gemini%20API-Powered-orange)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Akıllı, bağlam farkındalığına sahip ve tamamen sesle kontrol edilebilen masaüstü asistanı.*

</div>

---

## 🚀 Proje Hakkında

**RIFKI**, Google Gemini API'sinin mantıksal yürütme gücünü yerel bilgisayar işlemleriyle birleştiren gelişmiş bir masaüstü asistanıdır. Standart "sohbet botu" mantığından farklı olarak **LLM Tool-Calling (Function Calling)** mimarisi üzerine inşa edilmiştir. Bu sayede sadece sorulara cevap vermekle kalmaz; dosya yönetimi, sistem analizi, web araması ve uygulama kontrolü gibi işlemleri bilgisayarınızda otonom olarak gerçekleştirebilir.

![RIFKI HUD Interface](https://via.placeholder.com/800x450.png?text=Buraya+Rıfkı'nın+Arayüz+Ekran+Görüntüsünü+veya+GIF'ini+Ekle)

## ✨ Temel Mühendislik Özellikleri

* 🧠 **LLM Tool-Calling Mimarisi:** Gemini'nin doğrudan Python fonksiyonlarını (dosya oluşturma, uygulama açma, sistem kapatma) parametreleriyle birlikte tetiklemesini sağlayan dinamik yönlendirme (router) sistemi.
* ⚡ **Asenkron & Multi-Threaded Yapı:** Ses tanıma (STT) ve yapay zeka (API) ağ çağrıları sırasında kullanıcı arayüzünün (HUD) donmasını kesin olarak engelleyen `QThread` tabanlı izole işçi (worker) mimarisi.
* 💾 **Kalıcı Hafıza Entegrasyonu:** Kısa süreli bağlamın (context) ötesinde, kullanıcının "bunu hatırla" dediği verileri yapılandırılmış olarak **SQLite** veritabanında saklayan Long-Term Memory (LTM) modülü.
* 🛡️ **Güvenlik & Onay Katmanı:** Kritik sistem operasyonları (dosya silme, bilgisayarı kapatma) için AI ile işletim sistemi arasına yerleştirilmiş kullanıcı onay mekanizması (`core/security.py`).
* 🖥️ **Sci-Fi HUD Arayüzü:** Iron Man 'Arc Reactor' konseptinden ilham alan, `PyQt5 QPainter` ile geliştirilmiş donanım dostu animasyonlar ve gerçek zamanlı sistem kaynağı (CPU/RAM/Disk) izleme panelleri.

## 🛠️ Teknoloji Yığını

- **Çekirdek:** Python 3.10+
- **Yapay Zeka (LLM):** `google-genai` (Gemini 2.5 Flash)
- **Arayüz (GUI):** PyQt5
- **Ses Tanıma (STT):** SpeechRecognition (Google Web Speech API)
- **Metin Okuma (TTS):** gTTS / pyttsx3
- **Sistem Entegrasyonu:** psutil, win10toast, pycaw

## 📂 Mimari & Klasör Yapısı

```text
RIFKI/
├── core/                  # Çekirdek motor (AI bağlantısı, Tool-Router, Hafıza, Güvenlik)
├── voice/                 # Asenkron ses işleme (Wake-word, STT, TTS)
├── tools/                 # LLM tarafından tetiklenebilen bağımsız eklenti fonksiyonları
├── ui/                    # PyQt5 animasyonları, HUD bileşenleri ve Main Window
├── config/                # Çevresel değişkenler (.env) ve merkezi ayarlar
├── database/              # SQLite hafıza veritabanı (Çalışma zamanında oluşur)
└── main.py                # Sistem başlatıcı ve donanım doğrulama
