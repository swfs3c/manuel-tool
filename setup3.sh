#!/usr/bin/env bash

# Arch Linux - Otomatik Kurulum ve Özelleştirme Betiği
# Konu: Paru, Chrome, ZSH, Oh-My-Zsh, PowerLevel10k, JDK, İkon Teması, Terminal Eklentileri, EasyEffects, Ekstra Fontlar, GNOME Eklentileri
# Hata anında betiği durdurmak için:
set -euo pipefail

# Renk Paleti
YESIL='\033[92m'
SARI='\033[93m'
KIRMIZI='\033[91m'
MAVI='\033[94m'
MOR='\033[95m'
SIFIRLA='\033[0m'

bilgi() { echo -e "${MAVI}[*]${SIFIRLA} $1"; }
basari() { echo -e "${YESIL}[+]${SIFIRLA} $1"; }
uyari() { echo -e "${SARI}[!]${SIFIRLA} $1"; }
hata() { echo -e "${KIRMIZI}[-]${SIFIRLA} $1"; }
kontrol() { echo -e "${MOR}[✓]${SIFIRLA} $1"; }

# 1. Root (Sudo) Kontrolü ve Passwordless Sudo Doğrulama
if [ "$EUID" -eq 0 ]; then
  hata "Bu betik root olarak çalıştırılamaz! Lütfen normal kullanıcı yetkisiyle (sudo olmadan) çalıştırın."
  exit 1
fi

bilgi "Sudo passwordless erişimi kontrol ediliyor..."
if ! sudo -n true 2>/dev/null; then
  hata "Sudo parola gerektiriyor! Lütfen sudoers dosyasıyla passwordless sudo ayarla: sudo visudo"
  exit 1
fi
basari "Sudo passwordless erişimi onaylandı."


# Kurulum başarısız paketleri takip etmek için
BASARISIZ_PAKETLER=""

echo -e "${MAVI}═══════════════════════════════════════════════════════════════╗${SIFIRLA}"
echo -e "${MAVI}║     ARCH LINUX - KAPSAMLI KURULUM VE YAPILANDIRMA           ║${SIFIRLA}"
echo -e "${MAVI}║                                                             ║${SIFIRLA}"
echo -e "${MOR}║  • Paru (AUR Helper)                                        ║${SIFIRLA}"
echo -e "${MOR}║  • Google Chrome                                            ║${SIFIRLA}"
echo -e "${MOR}║  • ZSH + Oh-My-Zsh + PowerLevel10k                          ║${SIFIRLA}"
echo -e "${MOR}║  • JDK-OpenJDK                                              ║${SIFIRLA}"
echo -e "${MOR}║  • Qogir Icon Theme                                         ║${SIFIRLA}"
echo -e "${MOR}║  • Çeşitli Fontlar (Meslo, Hack, MS, vb.)                   ║${SIFIRLA}"
echo -e "${MOR}║  • EasyEffects & Ses Eklentileri                            ║${SIFIRLA}"
echo -e "${MOR}║  • GNOME Eklentileri & Extension Manager                    ║${SIFIRLA}"
echo -e "${MAVI}═══════════════════════════════════════════════════════════════╝${SIFIRLA}\n"

# 2. Pacman veritabanı güncelleme
bilgi "Pacman veritabanı güncelleniyor..."
sudo pacman -Syu --noconfirm

# 3. Temel Bağımlılıkların Kurulumu
bilgi "Temel bağımlılıklar kontrol ediliyor..."
TEMEL_PAKETLER="base-devel git curl wget unzip make gcc patch"
sudo pacman -S --needed --noconfirm $TEMEL_PAKETLER
kontrol "Temel bağımlılıklar hazır."

# 4. Paru (AUR Helper) Kurulumu
if ! command -v paru &> /dev/null; then
    bilgi "Paru bulunamadı. AUR üzerinden derleniyor..."
    cd /tmp
    rm -rf paru 2>/dev/null || true
    git clone https://aur.archlinux.org/paru.git
    cd paru
    if makepkg -si --noconfirm; then
        cd ~
        basari "Paru başarıyla kuruldu."
    else
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER Paru"
        hata "Paru kurulumu başarısız!"
        exit 1
    fi
else
    basari "Paru zaten sistemde yüklü."
fi

# 5. Pacman Paketlerinin Kurulumu (JDK, ZSH, vs.)
bilgi "Pacman paketleri kuruluyor (ZSH, JDK)..."
PACMAN_PAKETLER="zsh jdk-openjdk"
if sudo pacman -S --needed --noconfirm $PACMAN_PAKETLER; then
    kontrol "Pacman paketleri kuruldu."
else
    BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER Pacman_Paketleri"
    hata "Bazı Pacman paketleri kurulamadı!"
fi

# 6. AUR ve Temel Paketlerinin Kurulumu
bilgi "Temel AUR paketleri kuruluyor..."
AUR_PAKETLER="google-chrome qogir-icon-theme meslo-nerd-font-powerlevel10k"

for paket in $AUR_PAKETLER; do
    if ! paru -S --needed --noconfirm "$paket"; then
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER $paket"
        uyari "Uyarı: $paket kurulamadı, devam ediliyor..."
    else
        kontrol "$paket kuruldu."
    fi
done

# 7. Ekstra Fontların Kurulumu
bilgi "Ekstra fontlar kontrol ediliyor ve kuruluyor..."
EKSTRA_FONTLAR="ttf-ms-fonts ttf-jetbrains-mono ttf-fira-code ttf-hack-nerd ttf-dejavu noto-fonts noto-fonts-emoji"

for font in $EKSTRA_FONTLAR; do
    if ! paru -S --needed --noconfirm "$font"; then
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER $font"
        uyari "Uyarı: $font kurulamadı, devam ediliyor..."
    else
        kontrol "$font kuruldu."
    fi
done

bilgi "Font cache güncelleniyor..."
if fc-cache -fv &>/dev/null; then
    basari "Font cache başarıyla güncellendi."
else
    uyari "Font cache güncellemesinde sorun oluştu."
fi

# 8. Oh-My-Zsh Kurulumu
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    bilgi "Oh-My-Zsh kuruluyor..."
    if RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended; then
        basari "Oh-My-Zsh kuruldu."
    else
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER Oh-My-Zsh"
        hata "Oh-My-Zsh kurulumu başarısız!"
        exit 1
    fi
else
    basari "Oh-My-Zsh zaten yüklü."
fi

# 9. ZSH Eklentileri ve Powerlevel10k Teması
ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"

bilgi "Powerlevel10k teması ve ZSH eklentileri indiriliyor..."

if [ ! -d "$ZSH_CUSTOM/themes/powerlevel10k" ]; then
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$ZSH_CUSTOM/themes/powerlevel10k"
    kontrol "PowerLevel10k kuruldu."
else
    basari "PowerLevel10k zaten yüklü."
fi

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
    git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    kontrol "Zsh-autosuggestions kuruldu."
else
    basari "Zsh-autosuggestions zaten yüklü."
fi

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
    kontrol "Zsh-syntax-highlighting kuruldu."
else
    basari "Zsh-syntax-highlighting zaten yüklü."
fi

basari "Tüm tema ve eklentiler başarıyla ayarlandı."

# P10k.zsh otomatik konfigürasyonu
bilgi "Powerlevel10k otomatik ayarları yükleniyor..."
if [ ! -f "$HOME/.p10k.zsh" ]; then
    cat << 'EOF' > "$HOME/.p10k.zsh"
# Generated by setup script. Tip: p10k configure komutunu çalıştırabilirsin.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi
EOF
    kontrol ".p10k.zsh oluşturuldu."
else
    basari ".p10k.zsh zaten mevcut."
fi

# .zshrc'ye p10k source ekleme
if ! grep -q "source ~/.p10k.zsh" ~/.zshrc; then
    echo "" >> ~/.zshrc
    echo "[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh" >> ~/.zshrc
    kontrol ".p10k.zsh kaynak eklendi."
fi

# 10. .zshrc Yapılandırması (Güvenli)
bilgi "~/.zshrc dosyası yapılandırılıyor..."

if [ -f ~/.zshrc ]; then
    cp ~/.zshrc ~/.zshrc.backup_$(date +%Y%m%d_%H%M%S)
    kontrol ".zshrc yedeklendi."
else
    touch ~/.zshrc
fi

if grep -q "^ZSH_THEME=" ~/.zshrc; then
    sed -i 's/^ZSH_THEME=.*/ZSH_THEME="powerlevel10k\/powerlevel10k"/g' ~/.zshrc
else
    echo 'ZSH_THEME="powerlevel10k/powerlevel10k"' >> ~/.zshrc
fi

if grep -q "^plugins=" ~/.zshrc; then
    sed -i 's/^plugins=.*/plugins=(git zsh-autosuggestions zsh-syntax-highlighting)/g' ~/.zshrc
else
    echo "plugins=(git zsh-autosuggestions zsh-syntax-highlighting)" >> ~/.zshrc
fi

basari ".zshrc eklentileri yapılandırıldı."

# 11. ZSH Renk Ayarları
if ! grep -q "ZSH GÜÇLENDİRİLMİŞ RENK AYARLARI" ~/.zshrc; then
    bilgi "Özel ZSH renk yapılandırması dosyanın sonuna ekleniyor..."
    cat << 'EOF' >> ~/.zshrc

# --- ZSH GÜÇLENDİRİLMİŞ RENK AYARLARI ---
ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern cursor)

typeset -A ZSH_HIGHLIGHT_PATTERNS
ZSH_HIGHLIGHT_PATTERNS+=('./*' 'fg=15,bold')

typeset -A ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[command]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[builtin]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[alias]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[function]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[hashed-command]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[precommand]='fg=15,bold'

ZSH_HIGHLIGHT_STYLES[path]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[path_prefix]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[path-separator]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[default]='fg=15,bold'
EOF
    basari "Renk yapılandırması başarıyla eklendi."
else
    uyari "Renk yapılandırması ~/.zshrc içinde zaten mevcut, atlanıyor."
fi

# 12. Varsayılan Shell Ayarı
KULLANICI_SHELL=$(basename "$SHELL")
if [ "$KULLANICI_SHELL" != "zsh" ]; then
    bilgi "Varsayılan terminal ZSH olarak değiştiriliyor..."
    if sudo usermod -s /bin/zsh "$USER"; then
        basari "Default shell ZSH yapıldı."
    else
        uyari "Varsayılan shell değiştirilirken sorun oluştu (yeniden giriş sonra etkinleşecek)."
    fi
else
    basari "Default shell zaten ZSH."
fi

# 13. GNOME İmleç Teması
if command -v gsettings &> /dev/null; then
    bilgi "GNOME imleç teması Qogir olarak ayarlanıyor..."
    gsettings set org.gnome.desktop.interface cursor-theme 'Qogir'
    basari "GNOME imleç teması ayarlandı."
fi

# 14. Ses ve EasyEffects Yapılandırması
bilgi "EasyEffects ve gerekli ses eklentileri kuruluyor..."
EASYEFFECTS_PAKETLER="easyeffects lsp-plugins calf zam-plugins rnnoise pipewire-pulse wireplumber"

if sudo pacman -S --needed --noconfirm $EASYEFFECTS_PAKETLER; then
    kontrol "EasyEffects ve eklentileri kuruldu."
    
    bilgi "Ses servisleri yeniden başlatılıyor..."
    if systemctl --user restart pipewire pipewire-pulse wireplumber 2>/dev/null || true; then
        basari "Ses servisleri başarıyla yeniden başlatıldı."
    else
        uyari "Ses servisleri yeniden başlatılırken sorun oluştu (devam ediliyor)."
    fi

    bilgi "EasyEffects önayarları (presets) yükleniyor..."
    if bash -c "$(curl -fsSL https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh)"; then
        basari "EasyEffects önayarları başarıyla kuruldu."
    else
        uyari "EasyEffects önayarları kurulurken sorun oluştu."
    fi
else
    BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER EasyEffects"
    hata "EasyEffects paketleri kurulamadı!"
fi

# 15. GNOME Eklentileri ve Extension Manager
bilgi "GNOME Eklentileri ve Extension Manager kuruluyor..."

# Resmi Depolardaki Eklentiler (Apps Menu, Places Status, Blur My Shell) ve Manager
GNOME_PACMAN_EKLENTILER="extension-manager gnome-shell-extensions gnome-shell-extension-blur-my-shell"
if sudo pacman -S --needed --noconfirm $GNOME_PACMAN_EKLENTILER; then
    kontrol "Extension Manager ve resmi repo GNOME eklentileri kuruldu."
else
    BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER GNOME_Pacman_Eklentileri"
    hata "Bazı resmi GNOME eklentileri kurulamadı!"
fi

# AUR Depolardaki Eklentiler (Caffeine, Net Speed Simplified)
GNOME_AUR_EKLENTILER="gnome-shell-extension-caffeine gnome-shell-extension-net-speed-simplified"
for eklenti in $GNOME_AUR_EKLENTILER; do
    if ! paru -S --needed --noconfirm "$eklenti"; then
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER $eklenti"
        uyari "Uyarı: $eklenti kurulamadı, devam ediliyor..."
    else
        kontrol "$eklenti kuruldu."
    fi
done

# Eklentileri Aktifleştirme
bilgi "Eklentiler aktifleştiriliyor..."
EKLENTI_UUIDLER=(
    "apps-menu@gnome-shell-extensions.gcampax.github.com"
    "places-menu@gnome-shell-extensions.gcampax.github.com"
    "blur-my-shell@aunetx"
    "caffeine@patapon.info"
    "netspeedsimplified@prateekmedia.extension"
)

for uuid in "${EKLENTI_UUIDLER[@]}"; do
    if gnome-extensions list 2>/dev/null | grep -q "$uuid"; then
        if gnome-extensions enable "$uuid" 2>/dev/null || true; then
            kontrol "$uuid başarıyla aktifleştirildi."
        else
            uyari "$uuid aktifleştirilemedi (GNOME yeniden başlatıldığında dene)."
        fi
    else
        uyari "$uuid kurulu görünmüyor, atlanıyor."
    fi
done

# 16. Kurulum Sonrası Doğrulama
echo -e "\n${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}"
echo -e "${MOR}[KONTROL] KURULUM SONRASI DOĞRULAMA${SIFIRLA}"
echo -e "${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}\n"

KONTROL_ARACLARI=(
    "paru:Paru (AUR Helper)"
    "google-chrome:Google Chrome"
    "zsh:ZSH Shell"
    "java:JDK-OpenJDK"
    "curl:CURL"
    "git:Git"
    "easyeffects:EasyEffects"
    "extension-manager:Extension Manager"
)

echo -e "${YESIL}Yüklü araçlar:${SIFIRLA}"
for item in "${KONTROL_ARACLARI[@]}"; do
    KOMUT="${item%:*}"
    ISIM="${item#*:}"
    
    if command -v "$KOMUT" &> /dev/null; then
        kontrol "$ISIM → ✓"
    else
        hata "$ISIM → ✗ (KURULANMADI!)"
    fi
done

echo -e "\n${YESIL}Kontrol edilecek dizinler:${SIFIRLA}"
KONTROL_DIZINLERI=(
    "$HOME/.oh-my-zsh:Oh-My-Zsh"
    "$HOME/.oh-my-zsh/custom/themes/powerlevel10k:PowerLevel10k Teması"
    "$HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions:Zsh-Autosuggestions"
    "$HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting:Zsh-Syntax-Highlighting"
)

for item in "${KONTROL_DIZINLERI[@]}"; do
    DIZIN="${item%:*}"
    ISIM="${item#*:}"
    
    if [ -d "$DIZIN" ]; then
        kontrol "$ISIM → ✓"
    else
        hata "$ISIM → ✗ (KURULU DEĞİL!)"
    fi
done

echo -e "\n${YESIL}Font kontrolü:${SIFIRLA}"
if command -v fc-list &> /dev/null; then
    fc-list | grep -qi "Meslo" && kontrol "Meslo Font → ✓" || hata "Meslo Font → ✗"
    fc-list | grep -qi "Hack" && kontrol "Hack Font → ✓" || hata "Hack Font → ✗"
    fc-list | grep -qi "JetBrains" && kontrol "JetBrains Mono → ✓" || hata "JetBrains Mono → ✗"
    fc-list | grep -qi "Fira Code" && kontrol "Fira Code → ✓" || hata "Fira Code → ✗"
else
    uyari "fc-list komutu bulunamadı, fontlar kontrol edilemedi."
fi

# 17. Detaylı Özet Sonuç
echo -e "\n${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}"
echo -e "${MOR}[SONUÇ] KURULUM ÖZETİ${SIFIRLA}"
echo -e "${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}\n"

echo -e "${YESIL}Kurulu Ana Paketler:${SIFIRLA}"
pacman -Q paru google-chrome zsh jdk-openjdk 2>/dev/null | while read -r paket; do
    kontrol "$paket"
done || uyari "Bazı paketler listelenemiyor."

echo -e ""
echo -e "${YESIL}Shell Ayarı:${SIFIRLA}"
KULLANICI_SHELL=$(basename "$SHELL")
if [ "$KULLANICI_SHELL" = "zsh" ]; then
    kontrol "Default shell: ZSH"
else
    uyari "Default shell: $KULLANICI_SHELL (Yeniden giriş sonra ZSH'a geçecek)"
fi

echo -e ""
if [ -z "$BASARISIZ_PAKETLER" ]; then
    echo -e "${YESIL}════════════════════════════════════════════════════════════════${SIFIRLA}"
    echo -e "${YESIL}✓ KURULUM BAŞARIYLA TAMAMLANDI!${SIFIRLA}"
    echo -e "${YESIL}════════════════════════════════════════════════════════════════${SIFIRLA}"
else
    echo -e "${SARI}════════════════════════════════════════════════════════════════${SIFIRLA}"
    echo -e "${SARI}⚠ KURULUM TAMAMLANDI AMA BAZILARI KURULANMADI:${SIFIRLA}"
    echo -e "${SARI}$BASARISIZ_PAKETLER${SIFIRLA}"
    echo -e "${SARI}════════════════════════════════════════════════════════════════${SIFIRLA}"
fi

echo -e "\n${YESIL}Kurulum betiki başarıyla bitti! İyi kullanımlar! 🎉${SIFIRLA}"
echo -e "${MOR}İlk ZSH açılışında 'p10k configure' komutunu çalıştırabilirsin.${SIFIRLA}\n"

read -p "Hemen ZSH'a geçmek ister misiniz? (e/h): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ee]$ ]]; then
    exec zsh
fi
