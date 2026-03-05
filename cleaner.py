#!/usr/bin/env python3

import subprocess
import os
import shutil
import sys
import argparse
from pathlib import Path

# Terminal renk kodları (Dijital titizliğe yakışır bir görünüm için)
class Renk:
    YESIL = '\033[92m'
    SARI = '\033[93m'
    KIRMIZI = '\033[91m'
    MAVI = '\033[94m'
    ACIK_MAVI = '\033[96m'
    SIFIRLA = '\033[0m'

# Global değişkenler
dry_run = False
agressive_mode = False

def bilgi(mesaj):
    print(f"{Renk.MAVI}[*]{Renk.SIFIRLA} {mesaj}")

def basari(mesaj):
    print(f"{Renk.YESIL}[+]{Renk.SIFIRLA} {mesaj}")

def uyari(mesaj):
    print(f"{Renk.SARI}[!]{Renk.SIFIRLA} {mesaj}")

def hata(mesaj):
    print(f"{Renk.KIRMIZI}[-]{Renk.SIFIRLA} {mesaj}")

def komut_calistir(komut, sudo=False):
    """Verilen komutu çalıştırır ve çıktısını/hatasını yönetir. Specific exceptions ile.."""
    if sudo:
        komut = ['sudo'] + komut
    
    if dry_run:
        bilgi(f"[DRY-RUN] Çalıştırılacak komut: {' '.join(komut)}")
        return True, ""
    
    try:
        sonuc = subprocess.run(komut, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, sonuc.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr if e.stderr else str(e)
    except PermissionError as e:
        return False, f"Yetki hatası: {str(e)}"
    except FileNotFoundError:
        return False, f"Komut bulunamadı: {komut[0]}"
    except Exception as e:
        return False, f"Komut çalıştırma hatası: {str(e)}"

def dosya_boyutu_al(yol):
    """Dosya veya dizinin toplam boyutunu byte cinsinden döndürür."""
    try:
        if os.path.isfile(yol):
            return os.path.getsize(yol)
        else:
            toplam = 0
            for root, dirs, files in os.walk(yol):
                for f in files:
                    try:
                        toplam += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
            return toplam
    except Exception:
        return 0

def boyut_formati(byte):
    """Byte'ı MB/GB formatına çevirir."""
    if byte >= 1024 * 1024 * 1024:
        return f"{byte / (1024 * 1024 * 1024):.2f} GB"
    elif byte >= 1024 * 1024:
        return f"{byte / (1024 * 1024):.2f} MB"
    elif byte >= 1024:
        return f"{byte / 1024:.2f} KB"
    else:
        return f"{byte} B"

def bos_dizinleri_temizle(anahtar_dizin):
    """Verilen dizinde dosyalar sildikten sonra boş kalan dizinleri işin kaldırır."""
    try:
        for root, dirs, files in os.walk(anahtar_dizin, topdown=False):
            for d in dirs:
                d_path = os.path.join(root, d)
                try:
                    if not os.listdir(d_path):  # Eğer boş ise
                        os.rmdir(d_path)
                except OSError:
                    pass  # Eğer silemeyişse devam et
                except Exception:
                    pass
    except Exception:
        pass

depo_raporu = {
    'cache': 0,
    'logs': 0,
    'temp': 0,
    'packages': 0,
    'symlinks': 0,
    'aur': 0,
    'toplam': 0
}

def yetim_paketleri_temizle():
    """Yöneticinin manuel olarak yüklü çıkta bağımlı olmayan paketleri siler.
    İlk soru sor, sonra sil - hiçbir çakışma yok."""
    bilgi("Yöneticinin yüklü ama bağımlı olmayan paketler taranıyor...")
    
    # Yöneticinin manual yüklüşü paketleri bul (yetim)
    durum, cikti = komut_calistir(['pacman', '-Qtdq'])
    
    if not durum or not cikti.strip():
        basari("✓ Sistem tertemiz, boş paket bulunamadı.")
        return

    paketler = cikti.strip().split('\n')
    
    print(f"\n{Renk.SARI}Bulundu {len(paketler)} adet bağımlılığı olmayan paket:{Renk.SIFIRLA}")
    for i, paket in enumerate(paketler[:15], 1):
        print(f"  {i}. {paket}")
    
    if len(paketler) > 15:
        print(f"  ... ve {len(paketler) - 15} tane daha")
    
    if dry_run:
        basari(f"[DRY-RUN] Bu {len(paketler)} paket silinecektir.")
    else:
        onay = input(f"\n{Renk.MAVI}Bu paketleri silmek istiyor musunuz? (e/H): {Renk.SIFIRLA}").lower()
        if onay == 'e':
            silme_durumu, silme_cikti = komut_calistir(['pacman', '-Rns'] + paketler + ['--noconfirm'], sudo=True)
            if silme_durumu:
                basari(f"✓ {len(paketler)} adet paket başarıyla kaldırıldı.")
            else:
                hata(f"Paketler silinirken hata oluştu")
        else:
            uyari("İptal edildi.")

def pacman_onbellek_temizle():
    bilgi("Pacman önbelleği temizleniyor (Sadece yüklü olmayanlar)...")
    durum, cikti = komut_calistir(['pacman', '-Sc', '--noconfirm'], sudo=True)
    if durum:
        basari("Pacman önbelleği temizlendi.")
    else:
        hata(f"Önbellek temizlenirken hata oluştu:\n{cikti}")

def journal_loglarini_temizle():
    bilgi("Systemd journal logları temizleniyor (Son 2 hafta tutuluyor)...")
    
    durum, cikti = komut_calistir(['journalctl', '--vacuum-time=2weeks'], sudo=True)
    if durum:
        basari(f"Loglar başarıyla daraltıldı. {cikti.strip()}") if cikti else basari("Loglar başarıyla daraltıldı.")
    else:
        hata(f"Loglar temizlenirken hata oluştu:\n{cikti}")

def flatpak_temizle():
    bilgi("Kullanılmayan Flatpak artıkları temizleniyor...")
    durum, cikti = komut_calistir(['flatpak', 'uninstall', '--unused', '-y'])
    if durum:
        basari("Kullanılmayan Flatpak paketleri temizlendi.")
    else:
        bilgi("(Flatpak yüklü olmayabilir)")

def kullanici_cache_temizle():
    bilgi("Kullanıcı önbellek dizini (~/.cache) temizleniyor...")
    cache_dir = os.path.expanduser('~/.cache')
    
    if os.path.exists(cache_dir):
        silinen_boyut = 0
        silinen_dosya = 0
        for root, dirs, files in os.walk(cache_dir):
            for f in files:
                try:
                    dosya_yolu = os.path.join(root, f)
                    silinen_boyut += os.path.getsize(dosya_yolu)
                    silinen_dosya += 1
                    if not dry_run:
                        os.remove(dosya_yolu)
                except OSError as e:
                    pass  # Yetki hatası veya dosya kilitlemi
                except Exception:
                    pass
        
        # Boş dizinleri temizle
        if not dry_run:
            bos_dizinleri_temizle(cache_dir)
        
        mb_boyut = silinen_boyut / (1024 * 1024)
        if dry_run:
            basari(f"[DRY-RUN] ~/.cache dizininden yaklaşık {mb_boyut:.2f} MB ({silinen_dosya} dosya) silinecektir.")
        elif mb_boyut > 0:
            basari(f"~/.cache dizininden yaklaşık {mb_boyut:.2f} MB veri temizlendi.")
    else:
        uyari("~/.cache dizini bulunamadı.")

def gnome_cache_temizle():
    bilgi("GNOME önbelleği temizleniyor...")
    gnome_cache = os.path.expanduser('~/.local/share/gnome-shell')
    gnome_evolution = os.path.expanduser('~/.local/share/evolution')
    
    silinen_boyut = 0
    
    for cache_path in [gnome_cache, gnome_evolution]:
        if os.path.exists(cache_path):
            try:
                for root, dirs, files in os.walk(cache_path):
                    for f in files:
                        try:
                            dosya_yolu = os.path.join(root, f)
                            silinen_boyut += os.path.getsize(dosya_yolu)
                            if not dry_run:
                                os.remove(dosya_yolu)
                        except OSError:
                            pass
                        except Exception:
                            pass
            except Exception as e:
                uyari(f"GNOME cache temizliğinde hata: {e}")
    
    # Boş dizinleri temizle
    if not dry_run:
        for cache_path in [gnome_cache, gnome_evolution]:
            if os.path.exists(cache_path):
                bos_dizinleri_temizle(cache_path)
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] GNOME cache'den yaklaşık {mb_boyut:.2f} MB silinecektir.")
        else:
            basari(f"GNOME cache'den yaklaşık {mb_boyut:.2f} MB temizlendi.")
    else:
        basari("GNOME cache temiz.")

def local_share_temizle():
    bilgi("Eski uygulama verisi (~/.local/share) temizleniyor...")
    local_share = os.path.expanduser('~/.local/share')
    
    temp_dirs = [
        'recently-used.xbel',  # Son kullanılan dosyalar
        'gvfs-metadata',
        'tracker',
    ]
    
    silinen_boyut = 0
    
    for dir_name in temp_dirs:
        dir_path = os.path.join(local_share, dir_name)
        if os.path.exists(dir_path):
            try:
                if os.path.isfile(dir_path):
                    silinen_boyut += os.path.getsize(dir_path)
                    if not dry_run:
                        os.remove(dir_path)
                else:
                    for root, dirs, files in os.walk(dir_path):
                        for f in files:
                            try:
                                f_path = os.path.join(root, f)
                                silinen_boyut += os.path.getsize(f_path)
                                if not dry_run:
                                    os.remove(f_path)
                            except OSError:
                                pass
                            except Exception:
                                pass
            except Exception as e:
                uyari(f"{dir_name} temizliğinde hata: {e}")
    
    # Boş dizinleri temizle
    if not dry_run and os.path.exists(local_share):
        bos_dizinleri_temizle(local_share)
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] ~/.local/share'den yaklaşık {mb_boyut:.2f} MB silinecektir.")
        else:
            basari(f"~/.local/share'den yaklaşık {mb_boyut:.2f} MB temizlendi.")

def broken_symlinks_temizle():
    bilgi("Kırılmış sembolik linkler (symlink) taranıyor...")
    home = os.path.expanduser('~')
    
    kırılmış_linkler = 0
    silinen_count = 0
    
    try:
        for root, dirs, files in os.walk(home, followlinks=False):
            # .cache, .local vb. gizli dizinleri atla
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for f in files:
                gidişyolu = os.path.join(root, f)
                if os.path.islink(gidişyolu) and not os.path.exists(gidişyolu):
                    kırılmış_linkler += 1
                    if not dry_run:
                        try:
                            os.remove(gidişyolu)
                            silinen_count += 1
                        except OSError:
                            pass
                        except Exception:
                            pass
    except Exception:
        pass
    
    if kırılmış_linkler > 0:
        if dry_run:
            basari(f"[DRY-RUN] {kırılmış_linkler} adet kırılmış symlink bulundu, silinecektir.")
        else:
            basari(f"{silinen_count} adet kırılmış symlink silindi.")
    else:
        basari("Kırılmış symlink bulunamadı.")

def gercek_temp_dosyalari_temizle():
    bilgi("Geçici dosyalar (/tmp, /var/tmp) temizleniyor...")
    temp_dirs = ['/tmp', '/var/tmp']
    silinen_boyut = 0
    silinen_count = 0
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    # Sistem dosyalarını atla
                    if item.startswith('.'):
                        continue
                    
                    try:
                        if os.path.isfile(item_path):
                            silinen_boyut += os.path.getsize(item_path)
                            silinen_count += 1
                            if not dry_run:
                                os.remove(item_path)
                        elif os.path.isdir(item_path):
                            for root, dirs, files in os.walk(item_path):
                                for f in files:
                                    f_path = os.path.join(root, f)
                                    try:
                                        silinen_boyut += os.path.getsize(f_path)
                                        silinen_count += 1
                                        if not dry_run:
                                            os.remove(f_path)
                                    except OSError:
                                        pass
                                    except Exception:
                                        pass
                    except Exception:
                        pass
            except Exception:
                pass
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] Geçici dosyalardan yaklaşık {mb_boyut:.2f} MB ({silinen_count} dosya) silinecektir.")
        else:
            basari(f"Geçici dosyalardan yaklaşık {mb_boyut:.2f} MB temizlendi.")
    else:
        basari("Geçici dosyalar temiz.")

def aur_cache_temizle():
    bilgi("AUR/yay/paru cache'i taranıyor...")
    aur_caches = [
        os.path.expanduser('~/.cache/yay'),
        os.path.expanduser('~/.cache/paru'),
    ]
    
    silinen_boyut = 0
    silinacak_dosya = 0
    
    for cache_path in aur_caches:
        if os.path.exists(cache_path):
            try:
                for root, dirs, files in os.walk(cache_path):
                    for f in files:
                        f_path = os.path.join(root, f)
                        try:
                            silinen_boyut += os.path.getsize(f_path)
                            silinacak_dosya += 1
                            if not dry_run:
                                os.remove(f_path)
                        except Exception:
                            pass
            except Exception:
                pass
    
    # Boş dizinleri temizle
    if not dry_run:
        for cache_path in aur_caches:
            if os.path.exists(cache_path):
                bos_dizinleri_temizle(cache_path)
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] AUR cache'den yaklaşık {mb_boyut:.2f} MB ({silinacak_dosya} dosya) silinecektir.")
        else:
            basari(f"AUR cache'den yaklaşık {mb_boyut:.2f} MB temizlendi.")
    else:
        basari("AUR cache temiz.")

def thumbnail_cache_temizle():
    """Resim thumbnail cache'lerini temizler."""
    bilgi("Thumbnail cache'leri temizleniyor...")
    
    thumbnail_dir = os.path.expanduser('~/.cache/thumbnails')
    silinen_boyut = 0
    silinen_dosya = 0
    
    if os.path.exists(thumbnail_dir):
        try:
            for root, dirs, files in os.walk(thumbnail_dir):
                for f in files:
                    f_path = os.path.join(root, f)
                    try:
                        silinen_boyut += os.path.getsize(f_path)
                        silinen_dosya += 1
                        if not dry_run:
                            os.remove(f_path)
                    except OSError:
                        pass
                    except Exception:
                        pass
        except Exception as e:
            uyari(f"Thumbnail cache temizliğinde hata: {e}")
    
    # Boş dizinleri temizle
    if not dry_run and os.path.exists(thumbnail_dir):
        bos_dizinleri_temizle(thumbnail_dir)
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] Thumbnail cache'den yaklaşık {mb_boyut:.2f} MB ({silinen_dosya} dosya) silinecektir.")
        else:
            basari(f"Thumbnail cache'den yaklaşık {mb_boyut:.2f} MB temizlendi.")

def pip_npm_cache_temizle():
    """Pip, npm ve diğer paket yöneticisi cache'lerini temizler."""
    bilgi("Paket yöneticisi cache'leri temizleniyor...")
    
    dev_caches = [
        os.path.expanduser('~/.cache/pip'),
        os.path.expanduser('~/.npm'),
        os.path.expanduser('~/.cache/npm'),
        os.path.expanduser('~/.gem'),
        os.path.expanduser('~/.cargo/registry/cache'),
    ]
    
    silinen_boyut = 0
    
    for cache_path in dev_caches:
        if os.path.exists(cache_path):
            try:
                for root, dirs, files in os.walk(cache_path):
                    for f in files:
                        f_path = os.path.join(root, f)
                        try:
                            silinen_boyut += os.path.getsize(f_path)
                            if not dry_run:
                                os.remove(f_path)
                        except Exception:
                            pass
            except Exception:
                pass
    
    # Boş dizinleri temizle
    if not dry_run:
        for cache_path in dev_caches:
            if os.path.exists(cache_path):
                bos_dizinleri_temizle(cache_path)
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] Paket yöneticisi cache'den yaklaşık {mb_boyut:.2f} MB silinecektir.")
        else:
            basari(f"Paket yöneticisi cache'den yaklaşık {mb_boyut:.2f} MB temizlendi.")

def system_cache_temizle():
    """Sistem genelinde cache'leri temizler (/var/cache vb.) - sudo yetkisi gerekir."""
    bilgi("/var/cache ve /var/crash temizleniyor...")
    
    silinen_boyut = 0
    
    # /var/cache temizliği
    try:
        durum, cikti = komut_calistir(['find', '/var/cache', '-type', 'f', '-atime', '+30'], sudo=True)
        if durum and cikti:
            files = cikti.strip().split('\n')
            for f in files:
                if f and os.path.exists(f):
                    try:
                        silinen_boyut += os.path.getsize(f)
                        if not dry_run:
                            os.remove(f)
                    except PermissionError:
                        pass  # Yetki hatası - sakinlik koruma
                    except Exception:
                        pass
    except Exception:
        pass
    
    # Crash dumps temizliği
    try:
        crash_dir = '/var/crash'
        if os.path.exists(crash_dir):
            for item in os.listdir(crash_dir):
                item_path = os.path.join(crash_dir, item)
                try:
                    if os.path.isfile(item_path):
                        boyut = os.path.getsize(item_path)
                    else:
                        boyut = dosya_boyutu_al(item_path)
                    silinen_boyut += boyut
                    
                    if not dry_run:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        else:
                            shutil.rmtree(item_path)
                except PermissionError:
                    pass  # Yetki hatası - sakinlik koruma
                except Exception:
                    pass
    except Exception:
        pass
    
    mb_boyut = silinen_boyut / (1024 * 1024)
    if mb_boyut > 0:
        if dry_run:
            basari(f"[DRY-RUN] Sistem cache'den yaklaşık {mb_boyut:.2f} MB silinecektir.")
        else:
            basari(f"Sistem cache'den yaklaşık {mb_boyut:.2f} MB temizlendi.")

def desktop_entry_temizle():
    """Kaldırılan uygulamaların .desktop dosyalarını temizler."""
    bilgi(".desktop dosyaları taranıyor...")
    
    desktop_dir = os.path.expanduser('~/.local/share/applications')
    
    if not os.path.exists(desktop_dir):
        bilgi(".desktop dizini bulunamadı.")
        return
    
    silinen_count = 0
    
    try:
        for item in os.listdir(desktop_dir):
            if item.endswith('.desktop'):
                item_path = os.path.join(desktop_dir, item)
                try:
                    with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if 'Exec=' in content:
                            exec_line = [l for l in content.split('\n') if l.startswith('Exec=')]
                            if exec_line:
                                exec_cmd = exec_line[0].split('=')[1].split()[0]
                                # Komut yürütülebilir mi kontrol et
                                if not shutil.which(exec_cmd.replace('%', '')):
                                    if not dry_run:
                                        try:
                                            os.remove(item_path)
                                            silinen_count += 1
                                        except Exception:
                                            pass
                                    else:
                                        silinen_count += 1
                except Exception:
                    pass
    except Exception:
        pass
    
    if silinen_count > 0:
        if dry_run:
            basari(f"[DRY-RUN] {silinen_count} kırılmış .desktop dosyası silinecektir.")
        else:
            basari(f"{silinen_count} kırılmış .desktop dosyası silindi.")
    else:
        bilgi(".desktop dosyaları temiz.")

def depo_analizi_yap():
    """Silinecek tüm dosyaların boyutunu analiz eder ve rapor sunar."""
    print(f"\n{Renk.ACIK_MAVI}╔══════════════════════════════════════╗{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}║     DEPOLAMA ANAL İZİ BAŞLATILIYOR      ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}╚══════════════════════════════════════╝{Renk.SIFIRLA}\n")
    
    depo_raporu.clear()
    depo_raporu['cache'] = 0
    depo_raporu['logs'] = 0
    depo_raporu['temp'] = 0
    depo_raporu['packages'] = 0
    depo_raporu['symlinks'] = 0
    depo_raporu['aur'] = 0
    toplam = 0
    
    # 1. Cache analizi
    bilgi("Cache dizinleri taranıyor...")
    cache_dir = os.path.expanduser('~/.cache')
    if os.path.exists(cache_dir):
        boyut = dosya_boyutu_al(cache_dir)
        depo_raporu['cache'] = boyut
        toplam += boyut
        print(f"  └─ ~/.cache: {boyut_formati(boyut)}")
    
    # 2. Local share öğeleri
    bilgi("Local share dizinleri taranıyor...")
    local_items = ['recently-used.xbel', 'gvfs-metadata', 'tracker']
    for item in local_items:
        item_path = os.path.expanduser(f'~/.local/share/{item}')
        if os.path.exists(item_path):
            boyut = dosya_boyutu_al(item_path)
            if boyut > 0:
                toplam += boyut
                print(f"  └─ {item}: {boyut_formati(boyut)}")
    
    # 3. Geçici dosyalar
    bilgi("Geçici dosyalar taranıyor...")
    for temp_dir in ['/tmp', '/var/tmp']:
        if os.path.exists(temp_dir):
            boyut = 0
            try:
                for item in os.listdir(temp_dir):
                    if not item.startswith('.'):
                        boyut += dosya_boyutu_al(os.path.join(temp_dir, item))
            except Exception:
                pass
            if boyut > 0:
                depo_raporu['temp'] += boyut
                toplam += boyut
                print(f"  └─ {temp_dir}: {boyut_formati(boyut)}")
    
    # 4. AUR cache
    bilgi("AUR cache taranıyor...")
    for cache_path in [os.path.expanduser('~/.cache/yay'), os.path.expanduser('~/.cache/paru')]:
        if os.path.exists(cache_path):
            boyut = dosya_boyutu_al(cache_path)
            if boyut > 0:
                depo_raporu['aur'] += boyut
                toplam += boyut
                baslik = "yay" if "yay" in cache_path else "paru"
                print(f"  └─ {baslik} cache: {boyut_formati(boyut)}")
    
    # 5. Paket bilgisi
    bilgi("Paket analizi yapılıyor...")
    durum, cikti = komut_calistir(['pacman', '-Qtdq'])
    yetim_count = len(cikti.strip().split('\n')) if durum and cikti.strip() else 0
    if yetim_count > 0:
        print(f"  └─ Yetim paketler: {yetim_count} adet")
        depo_raporu['packages'] = yetim_count
    
    # 6. Kırılmış symlinks
    home = os.path.expanduser('~')
    symlink_count = 0
    try:
        for root, dirs, files in os.walk(home, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if os.path.islink(os.path.join(root, f)) and not os.path.exists(os.path.join(root, f)):
                    symlink_count += 1
    except Exception:
        pass
    if symlink_count > 0:
        print(f"  └─ Kırılmış symlink'ler: {symlink_count} adet")
        depo_raporu['symlinks'] = symlink_count
    
    # Rapor
    print(f"\n{Renk.ACIK_MAVI}╔══════════════════════════════════════╗{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}║        DEPOLAMA ÖZETİ                  ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}╠══════════════════════════════════════╣{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}║ Cache dosyaları         │ {boyut_formati(depo_raporu['cache']):>18} ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}║ Geçici dosyalar        │ {boyut_formati(depo_raporu['temp']):>18} ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}║ AUR cache              │ {boyut_formati(depo_raporu['aur']):>18} ║{Renk.SIFIRLA}")
    print(f"{Renk.YESIL}║ Paket dosyaları        │ {depo_raporu['packages']:>18} paket ║{Renk.SIFIRLA}")
    print(f"{Renk.SARI}║ Kırılmış symlink'ler   │ {depo_raporu['symlinks']:>18} adet ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}╠══════════════════════════════════════╣{Renk.SIFIRLA}")
    print(f"{Renk.KIRMIZI}║ TOPLAM SİLİNECEK        │ {boyut_formati(toplam):>18} ║{Renk.SIFIRLA}")
    print(f"{Renk.ACIK_MAVI}╚══════════════════════════════════════╝{Renk.SIFIRLA}\n")
    
    return toplam > 0

def main():
    global dry_run, agressive_mode
    
    # Argument parser
    parser = argparse.ArgumentParser(
        description='Arch Linux GNOME Sistem Temizleyici - Dijital titizlik için!'
    )
    parser.add_argument('--dry-run', action='store_true', 
                       help='Ne silinecek göster, gerçekten silme')
    parser.add_argument('--aggressive', action='store_true',
                       help='Agresif temizlik modu: Thumbnails, pip/npm cache, sistem cache vb.')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Sadece depolama analizi yap, temizlik yapma')
    
    args = parser.parse_args()
    dry_run = args.dry_run
    agressive_mode = args.aggressive
    
    print(f"{Renk.MAVI}======================================{Renk.SIFIRLA}")
    print(f"{Renk.MAVI}   Arch Linux Sistem Temizleyici      {Renk.SIFIRLA}")
    print(f"{Renk.MAVI}======================================{Renk.SIFIRLA}")
    
    if dry_run:
        print(f"{Renk.ACIK_MAVI}[DRY-RUN MODU] - Hiçbir şey silinmeyecektir.{Renk.SIFIRLA}")
    
    if agressive_mode:
        print(f"{Renk.KIRMIZI}[AGRESİF MODU] - Daha kapsamlı temizlik yapılacak!{Renk.SIFIRLA}")
    
    print()
    
    # Analiz yap
    analiz_tamam = depo_analizi_yap()
    
    if args.analyze_only:
        print(f"{Renk.YESIL}Analiz tamamlandı.{Renk.SIFIRLA}")
        return
    
    if not analiz_tamam and not agressive_mode:
        print(f"{Renk.YESIL}Sisteminiz zaten çok temiz!{Renk.SIFIRLA}")
        return
    
    # Onay iste
    if not dry_run and (analiz_tamam or agressive_mode):
        onay = input(f"\n{Renk.KIRMIZI}⚠ Yukarıdaki dosyalar silinsin mi? (e/H): {Renk.SIFIRLA}").lower()
        if onay != 'e':
            print(f"{Renk.SARI}İptal edildi.{Renk.SIFIRLA}")
            return
    
    print(f"\n{Renk.YESIL}Temizlik işlemlerine başlıyor...{Renk.SIFIRLA}\n")
    
    # PAKET TEMİZLİĞİ
    print(f"\n{Renk.ACIK_MAVI}=== PAKET TEMİZLİĞİ ==={Renk.SIFIRLA}")
    yetim_paketleri_temizle()
    print("-" * 40)
    pacman_onbellek_temizle()
    print("-" * 40)
    journal_loglarini_temizle()
    print("-" * 40)
    flatpak_temizle()
    
    # DOSYA VE LOG TEMİZLİĞİ
    print(f"\n{Renk.ACIK_MAVI}=== DOSYA VE LOG TEMİZLİĞİ ==={Renk.SIFIRLA}")
    kullanici_cache_temizle()
    print("-" * 40)
    gnome_cache_temizle()
    print("-" * 40)
    local_share_temizle()
    print("-" * 40)
    broken_symlinks_temizle()
    print("-" * 40)
    gercek_temp_dosyalari_temizle()
    print("-" * 40)
    aur_cache_temizle()
    
    # AGRESİF TEMIZLIK
    if agressive_mode:
        print(f"\n{Renk.ACIK_MAVI}=== AGRESİF TEMIZLIK ==={Renk.SIFIRLA}")
        thumbnail_cache_temizle()
        print("-" * 40)
        pip_npm_cache_temizle()
        print("-" * 40)
        system_cache_temizle()
        print("-" * 40)
        desktop_entry_temizle()
    
    if dry_run:
        print(f"\n{Renk.ACIK_MAVI}[DRY-RUN] Kurulması için --dry-run olmadan tekrar çalıştırın.{Renk.SIFIRLA}")
    else:
        print(f"\n{Renk.YESIL}✓ Tüm temizlik işlemleri tamamlandı! Sisteminiz artık kristal temiz.{Renk.SIFIRLA}")

if __name__ == "__main__":
    main()
