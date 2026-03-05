#!/usr/bin/env bash

# Arch Linux - Otomatik Kurulum ve Özelleştirme Betiği
# Konu: Paru, Chrome, ZSH, Oh-My-Zsh, PowerLevel10k, JDK, İkon Teması, Terminal Eklentileri
# Hata anında betiği durdurmak için:
set -e

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

# 1. Root (Sudo) Kontrolü
# AUR paketleri (paru vb.) root olarak kurulamayacağı için bu kontrol şarttır.
if [ "$EUID" -eq 0 ]; then
  hata "Bu betik root olarak çalıştırılamaz! Lütfen normal kullanıcı yetkisiyle (sudo olmadan) çalıştırın."
  exit 1
fi

# Kurulum başarısız paketleri takip etmek için
BASARISIZ_PAKETLER=""

echo -e "${MAVI}═══════════════════════════════════════════════════════════════╗${SIFIRLA}"
echo -e "${MAVI}║     ARCH LINUX - KAPSAMLI KURULUM VE YAPILAN              ║${SIFIRLA}"
echo -e "${MAVI}║                                                             ║${SIFIRLA}"
echo -e "${MOR}║  • Paru (AUR Helper)                                        ║${SIFIRLA}"
echo -e "${MOR}║  • Google Chrome                                            ║${SIFIRLA}"
echo -e "${MOR}║  • ZSH + Oh-My-Zsh + PowerLevel10k                          ║${SIFIRLA}"
echo -e "${MOR}║  • JDK-OpenJDK                                              ║${SIFIRLA}"
echo -e "${MOR}║  • Qogir Icon Theme                                         ║${SIFIRLA}"
echo -e "${MOR}║  • Nerd Fontlar (Meslo + Hack)                              ║${SIFIRLA}"

echo -e "${MAVI}═══════════════════════════════════════════════════════════════╝${SIFIRLA}\n"

# 2. Pacman veritabanı güncelleme (ilk çalışmada gerekli olabilir)
bilgi "Pacman veritabanı güncelleniyor..."
sudo pacman -Sy --noconfirm

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

# 6. AUR Paketlerinin Kurulumu
bilgi "AUR paketleri kuruluyor..."
AUR_PAKETLER="google-chrome qogir-icon-theme ttf-meslo-nerd-font-powerlevel10k ttf-hack-nerd-font"

for paket in $AUR_PAKETLER; do
    if ! paru -S --needed --noconfirm "$paket"; then
        BASARISIZ_PAKETLER="$BASARISIZ_PAKETLER $paket"
        uyari "Uyarı: $paket kurulamadı, devam ediliyor..."
    else
        kontrol "$paket kuruldu."
    fi
done

# 7. Oh-My-Zsh Kurulumu (Varsa kontrol et)
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    bilgi "Oh-My-Zsh kuruluyor..."
    # --unattended parametresi kurulum bittiğinde otomatik olarak zsh'a düşmesini engeller
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

# 8. ZSH Eklentileri ve Powerlevel10k Teması
ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"

bilgi "Powerlevel10k teması ve ZSH eklentileri indiriliyor..."

# Powerlevel10k
if [ ! -d "$ZSH_CUSTOM/themes/powerlevel10k" ]; then
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$ZSH_CUSTOM/themes/powerlevel10k"
    kontrol "PowerLevel10k kuruldu."
else
    basari "PowerLevel10k zaten yüklü."
fi

# Zsh-autosuggestions
if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
    git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    kontrol "Zsh-autosuggestions kuruldu."
else
    basari "Zsh-autosuggestions zaten yüklü."
fi

# Zsh-syntax-highlighting
if [ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
    kontrol "Zsh-syntax-highlighting kuruldu."
else
    basari "Zsh-syntax-highlighting zaten yüklü."
fi



basari "Tüm tema ve eklentiler başarıyla ayarlandı."

# 9. .zshrc Yapılandırması (Yedekleme ve Temayı Ayarla)
bilgi "~/.zshrc dosyası yapılandırılıyor..."

# Eğer eski bir .zshrc varsa yedekle (sadece varsa)
if [ -f ~/.zshrc ]; then
    cp ~/.zshrc ~/.zshrc.backup_$(date +%Y%m%d_%H%M%S)
    kontrol ".zshrc yedeklendi."
fi

# Temayı değiştir
sed -i 's/^ZSH_THEME=.*/ZSH_THEME="powerlevel10k\/powerlevel10k"/g' ~/.zshrc

# Eklentileri aktif et (Eğer plugins satırı varsa, yoksa ekle)
if grep -q "^plugins=" ~/.zshrc; then
    sed -i 's/^plugins=.*/plugins=(git zsh-autosuggestions zsh-syntax-highlighting)/g' ~/.zshrc
else
    echo "plugins=(git zsh-autosuggestions zsh-syntax-highlighting)" >> ~/.zshrc
fi

basari ".zshrc eklentileri yapılandırıldı."

# 10. ZSH RENK AYARLARINI .ZSHRC'YE EKLE
if ! grep -q "ZSH GÜÇLENDİRİLMİŞ RENK AYARLARI" ~/.zshrc; then
    bilgi "Özel ZSH renk yapılandırması dosyanın sonuna ekleniyor..."
    cat << 'EOF' >> ~/.zshrc

# --- ZSH GÜÇLENDİRİLMİŞ RENK AYARLARI ---
# Bu blok dosyanın EN SONUNDA olmalı.

# 1. Renklendirici modüllerini (Highlighters) aktif et
# 'main' standart olandır, 'pattern' ise bizim özel kurallarımızdır.
ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern cursor)

# 2. ÖZEL KURAL (BALYOZ): ./ ile başlayan her şeyi ZORLA beyaz yap
# Bu komut diğer tüm kuralları ezer.
typeset -A ZSH_HIGHLIGHT_PATTERNS
ZSH_HIGHLIGHT_PATTERNS+=('./*' 'fg=15,bold')

# 3. Standart Komutlar (Yine de dursunlar)
typeset -A ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[command]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[builtin]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[alias]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[function]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[hashed-command]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[precommand]='fg=15,bold'

# 4. Yollar ve Diğerleri
ZSH_HIGHLIGHT_STYLES[path]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[path_prefix]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[path-separator]='fg=15,bold'
ZSH_HIGHLIGHT_STYLES[default]='fg=15,bold'
EOF
    basari "Renk yapılandırması başarıyla eklendi."
else
    uyari "Renk yapılandırması ~/.zshrc içinde zaten mevcut, atlanıyor."
fi

# 11. Varsayılan Shell'i ZSH Yap
KULLANICI_SHELL=$(basename "$SHELL")
if [ "$KULLANICI_SHELL" != "zsh" ]; then
    bilgi "Varsayılan terminal ZSH olarak değiştiriliyor..."
    chsh -s $(which zsh)
    basari "Default shell ZSH yapıldı."
else
    basari "Default shell zaten ZSH."
fi

# 12. GNOME DESKTOPü İÇİN İMLEÇ TEMASI OTOMATIK AYARLA
if command -v gsettings &> /dev/null; then
    bilgi "GNOME imleç teması Qogir olarak ayarlanıyor..."
    gsettings set org.gnome.desktop.interface cursor-theme 'Qogir'
    basari "GNOME imleç teması ayarlandı."
fi

# 13. KONTROL: TÜM KURULU PAKETLER VE ARAÇLAR
echo -e "\n${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}"
echo -e "${MOR}[KONTROL] KURULUM SONRASI DOĞRULAMA${SIFIRLA}"
echo -e "${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}\n"

# İlgili araçların yüklü olup olmadığını kontrol et
KONTROL_ARACLARI=(
    "paru:Paru (AUR Helper)"
    "google-chrome:Google Chrome"
    "zsh:ZSH Shell"
    "java:JDK-OpenJDK"
    "curl:CURL (Web Download)"
    "git:Git"
)

echo -e "${YESIL}Yüklü araçlar:${SIFIRLA}"
for item in "${KONTROL_ARACLARI[@]}"; do
    KOMUT="${item%:*}"
    ISIM="${item#*:}"
    
    if command -v "$KOMUT" &> /dev/null; then
        VERSION=$(command -v "$KOMUT" 2>&1)
        kontrol "$ISIM → ✓"
    else
        hata "$ISIM → ✗ (KURULANMADI!)"
    fi
done

echo -e "\n${YESIL}Kontrol edilecek dizinler:${SIFIRLA}"
# Oh-My-Zsh, Powerlevel10k, Eklentiler kontrolü
KONTROL_DIZINLERI=(
    "$HOME/.oh-my-zsh:Oh-My-Zsh"
    "$HOME/.oh-my-zsh/custom/themes/powerlevel10k:PowerLevel10k Teması"
    "$HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions:Zsh-Autosuggestions"
    "$HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting:Zsh-Syntax-Highlighting"

)

for item in "${KONTROL_DIZINLERI[@]}"; do
    DIZIN="${item%:*}"
    ISIM="${item#*:}"
    
    if [ -z "$DIZIN" ] || [ -z "$ISIM" ]; then
        continue
    fi
    
    if [ -d "$DIZIN" ]; then
        kontrol "$ISIM → ✓"
    else
        hata "$ISIM → ✗ (KURULU DEĞİL!)"
    fi
done

echo -e "\n${YESIL}Font kontrolü:${SIFIRLA}"
# Fontlar yüklü mü kontrol et (fc-list varsa)
if command -v fc-list &> /dev/null; then
    fc-list | grep -q "Meslo" && kontrol "Meslo Nerd Font → ✓" || hata "Meslo Nerd Font → ✗"
    fc-list | grep -q "Hack" && kontrol "Hack Nerd Font → ✓" || hata "Hack Nerd Font → ✗"
else
    uyari "fc-list komutu bulunamadı, fontlar kontrol edilemedi."
fi

# 14. ÖZET SONUÇ
echo -e "\n${MOR}═══════════════════════════════════════════════════════════════${SIFIRLA}"

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

echo -e "\n${SARI}SONRAKI ADIMLAR:${SIFIRLA}"
echo -e "${MAVI}1.${SIFIRLA} ${SARI}YENIDEN BAŞLATINIZ${SIFIRLA} (veya ${MAVI}source ~/.zshrc${SIFIRLA} komutu çalıştırın)"
echo -e "${MAVI}2.${SIFIRLA} Terminali ilk açtığınızda ${MOR}p10k configure${SIFIRLA} sihirbazı başlatılacaktır"
echo -e "${MAVI}3.${SIFIRLA} İmleç teması otomatik olarak ${MOR}Qogir${SIFIRLA} olarak ayarlandı"
echo -e "${MAVI}4.${SIFIRLA} Terminal Ayarları'ndan font olarak: ${MOR}Meslo Nerd Font${SIFIRLA} seçiniz"
echo -e "\n${YESIL}Kurulum betiki başarıyla bitti! İyi kullanımlar! 🎉${SIFIRLA}\n"

# Eğer ZSH henüz aktif değilse, isteğe bağlı olarak başlat
read -p "Hemen ZSH'a geçmek ister misiniz? (e/h): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ee]$ ]]; then
    exec zsh
fi