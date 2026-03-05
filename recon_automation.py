#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Set, List, Tuple
import time


class ReconAutomation:
    def __init__(self, workspace_path: str = "/home/swfsec/.bugbounty"):
        """
        Initialization fonksiyonu - tüm dosya yollarını ve oturum ayarlarını yapılandırır
        
        Args:
            workspace_path: Çalışma dizini
        """
        self.workspace_path = workspace_path
        self.domains_file = os.path.join(workspace_path, "domainler.txt")
        self.crt_output_file = os.path.join(workspace_path, "crt_subdomains.txt")
        self.subfinder_output_file = os.path.join(workspace_path, "subfinder_result.txt")
        self.final_output_file = os.path.join(workspace_path, "all_subdomains.txt")
        self.updated_domains_file = os.path.join(workspace_path, "updated_domains.txt")
        
        # Veri tutucu setler
        self.crt_subdomains: Set[str] = set()
        self.subfinder_subdomains: Set[str] = set()
        self.initial_domains: List[str] = []
        self.updated_domains: Set[str] = set()
        
        # HTTP oturumu - retry ve timeout ile
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.crt_timeout = 30
        self.crt_max_retries = 3
        self.log_quiet_mode = False
        
        self.log_message("=" * 80)
        self.log_message("HackerOne Bug Bounty Reconnaissance Automation Başlatıldı")
        self.log_message(f"Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"Çalışma Dizini: {workspace_path}")
        self.log_message("=" * 80)
    
    def log_message(self, message: str, level: str = "INFO"):
        """
        Log mesajı yazdır ve tarihstamp ekle
        
        Args:
            message: Yazdırılacak mesaj
            level: Log seviyesi (INFO, SUCCESS, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Level ikonları
        icons = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌"
        }
        
        icon = icons.get(level, "")
        print(f"[{timestamp}] {icon} {message}")
    
    def load_domains(self) -> bool:
        """
        domainler.txt dosyasından domainleri yükle ve temizle
        Wildcardları tespit et ve ana domain'i al
        
        Returns:
            bool: Başarılı ise True, hata varsa False
        """
        try:
            if not os.path.exists(self.domains_file):
                self.log_message(f"Hata: {self.domains_file} dosyası bulunamadı!", "ERROR")
                return False
            
            with open(self.domains_file, 'r', encoding='utf-8') as f:
                raw_domains = [line.strip() for line in f if line.strip()]
            
            if not raw_domains:
                self.log_message("Hata: Hiçbir domain bulunamadı!", "ERROR")
                return False
            
            # Domaini temizle (wildcard işaretlerini kaldır)
            for domain_line in raw_domains:
                clean_domain = domain_line.lstrip('*.').lower().strip()
                if clean_domain:
                    self.initial_domains.append(clean_domain)
                    self.updated_domains.add(clean_domain)
            
            # Duplikatları kaldır
            self.initial_domains = list(set(self.initial_domains))
            
            self.log_message(f"{len(self.initial_domains)} domain yüklendi:", "SUCCESS")
            for i, domain in enumerate(sorted(self.initial_domains), 1):
                self.log_message(f"   {i}. {domain}", "INFO")
            
            return True
        
        except Exception as e:
            self.log_message(f"Domain yükleme sırasında hata oluştu: {str(e)}", "ERROR")
            return False
    
    def query_crt_sh(self, domain: str) -> List[dict]:
        """
        Belirtilen domain için crt.sh API'sini sorgula
        
        API FORMAT: https://crt.sh/?q=%.domain.com&output=json
        Bu format %.domain.com'un altındaki tüm subdomainleri döndürür
        
        Args:
            domain: Sorgulanacak domain (örn: example.com)
            
        Returns:
            dict: API yanıtı (certificate listesi)
        """
        for attempt in range(1, self.crt_max_retries + 1):
            try:
                # crt.sh API endpoint - wildcard arama için %.domain.com formatı
                url = f"https://crt.sh/?q=%.{domain}&output=json"
                
                self.log_message(f"crt.sh sorgulanıyor: {domain} (Deneme {attempt}/{self.crt_max_retries})", "INFO")
                
                response = self.session.get(url, timeout=self.crt_timeout)
                response.raise_for_status()
                
                data = response.json()
                
                if isinstance(data, list):
                    self.log_message(f"   → {len(data)} sertifika bulundu", "INFO")
                    return data
                else:
                    self.log_message(f"   → Beklenmeyen API yanıtı formatı", "WARNING")
                    return []
            
            except requests.exceptions.Timeout:
                self.log_message(f"Timeout: {domain} sorgusu zaman aşımına uğradı", "WARNING")
            except requests.exceptions.ConnectionError:
                self.log_message(f"Bağlantı hatası: {domain} sorgusu başarısız", "WARNING")
            except json.JSONDecodeError:
                self.log_message(f"JSON hatası: {domain} için yanıt parse edilemedi", "WARNING")
            except Exception as e:
                self.log_message(f"Sorgulama hatası ({domain}): {str(e)}", "WARNING")
            
            # Son deneme değilse bekleme yap (rate limiting)
            if attempt < self.crt_max_retries:
                self.log_message(f"   → 2 saniye bekleniyor...", "INFO")
                time.sleep(2)
        
        return []
    
    def process_crt_certificates(self, certificates: List[dict], domain: str) -> Tuple[Set[str], Set[str]]:
        """
        crt.sh API'den gelen sertifika verilerini işle
        Subdomainleri ve wildcard domainleri ayıkla
        
        Args:
            certificates: API'den gelen sertifika listesi
            domain: Ana domain
            
        Returns:
            tuple: (subdomainler seti, wildcard domainleri seti)
        """
        subdomains = set()
        wildcards = set()
        
        for cert in certificates:
            # name_value alanı bazen virgülle ve newline ile ayrılmış adları içerir
            names_entry = cert.get('name_value', '')
            
            if not names_entry:
                continue
            
            # \n veya , ile ayrılmış names'i parse et
            names = [n.strip() for n in names_entry.replace(',', '\n').split('\n')]
            
            for name in names:
                name = name.strip().lower()
                
                if not name or name == '.':
                    continue
                
                # Wildcard domain mi kontrol et
                if name.startswith('*.'):
                    # *.api.example.com'dan api.example.com'u çıkar ve ekle
                    wildcard_domain = name[2:]  # '*.' kısmını kaldır
                    
                    # Geçerliliği kontrol et
                    if wildcard_domain and '.' in wildcard_domain and wildcard_domain not in self.updated_domains:
                        wildcards.add(wildcard_domain)
                        self.log_message(f"   → Wildcard domain keşfedildi: {wildcard_domain}", "SUCCESS")
                
                # Normal subdomain mi kontrol et
                elif name.endswith('.' + domain) or name == domain:
                    subdomains.add(name)
        
        return subdomains, wildcards
    
    def run_crt_sh_queries(self) -> bool:
        """
        Tüm domainler için crt.sh sorgularını çalıştır
        Bulduğu wildcard domainleri listeye ekle
        
        Returns:
            bool: Başarılı ise True
        """
        self.log_message("\n" + "=" * 80, "INFO")
        self.log_message("AŞAMA 1: CRT.SH SORGULAMASI BAŞLANIYOR", "INFO")
        self.log_message("=" * 80, "INFO")
        
        success_count = 0
        failed_domains = []
        
        for i, domain in enumerate(sorted(self.initial_domains), 1):
            self.log_message(f"\n[{i}/{len(self.initial_domains)}] {domain} için tarama...", "INFO")
            
            certificates = self.query_crt_sh(domain)
            
            if certificates:
                subdomains, wildcards = self.process_crt_certificates(certificates, domain)
                self.crt_subdomains.update(subdomains)
                self.updated_domains.update(wildcards)
                success_count += 1
            else:
                failed_domains.append(domain)
            
            # Rate limiting - Her talep arasında 1 saniye bekle
            time.sleep(1)
        
        self.log_message(f"\n✅ crt.sh sorgulama tamamlandı", "SUCCESS")
        self.log_message(f"   • Başarılı: {success_count}/{len(self.initial_domains)}", "INFO")
        self.log_message(f"   • Toplam Subdomain: {len(self.crt_subdomains)}", "INFO")
        self.log_message(f"   • Domain Listesi Boyutu: {len(self.updated_domains)}", "INFO")
        
        if failed_domains:
            self.log_message(f"   • Başarısız Domainler: {', '.join(failed_domains)}", "WARNING")
        
        return True
    
    def save_crt_results(self) -> bool:
        """
        crt.sh sonuçlarını dosyaya kaydet
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            self.log_message(f"\n💾 crt.sh sonuçları kaydediliyor...", "INFO")
            
            with open(self.crt_output_file, 'w', encoding='utf-8') as f:
                for subdomain in sorted(self.crt_subdomains):
                    f.write(subdomain + '\n')
            
            self.log_message(f"✅ {len(self.crt_subdomains)} subdomain kaydedildi", "SUCCESS")
            self.log_message(f"   Dosya: {self.crt_output_file}", "INFO")
            return True
        
        except Exception as e:
            self.log_message(f"crt.sh sonuçları kaydedilirken hata oluştu: {str(e)}", "ERROR")
            return False
    
    def save_updated_domains(self) -> bool:
        """
        Güncellenmiş domain listesini dosyaya kaydet
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            self.log_message(f"\n💾 Güncellenmiş domain listesi kaydediliyor...", "INFO")
            
            with open(self.updated_domains_file, 'w', encoding='utf-8') as f:
                for domain in sorted(self.updated_domains):
                    f.write(domain + '\n')
            
            new_domains = len(self.updated_domains) - len(self.initial_domains)
            self.log_message(f"✅ Güncellenmiş domain listesi kaydedildi", "SUCCESS")
            self.log_message(f"   • Orijinal: {len(self.initial_domains)}", "INFO")
            self.log_message(f"   • Yeni Wildcard: {new_domains}", "INFO")
            self.log_message(f"   • Toplam: {len(self.updated_domains)}", "INFO")
            self.log_message(f"   Dosya: {self.updated_domains_file}", "INFO")
            
            return True
        
        except Exception as e:
            self.log_message(f"Güncellenmiş domain listesi kaydedilirken hata oluştu: {str(e)}", "ERROR")
            return False
    
    def run_subfinder(self) -> bool:
        """
        Subfinder aracını güncellenmiş domain listesiyle çalıştır (-all parametresiyle)
        
        Subfinder komut satırı:
        subfinder -dL updated_domains.txt -all -o subfinder_result.txt
        
        -dL: Dosyadan domain listesini oku
        -all: Tüm aktif kaynakları kullan (Shodan API, Censys, vb)
        -o: Çıktı dosyası
        
        Returns:
            bool: Başarılı ise True
        """
        self.log_message("\n" + "=" * 80, "INFO")
        self.log_message("AŞAMA 2: SUBFINDER ARACININ ÇALIŞTIRILMASI", "INFO")
        self.log_message("=" * 80, "INFO")
        
        try:
            # Subfinder yüklü mü kontrol et
            check_cmd = subprocess.run(['which', 'subfinder'], 
                                      capture_output=True, 
                                      timeout=5,
                                      text=True)
            
            if check_cmd.returncode != 0:
                self.log_message("Subfinder aracı bulunamadı!", "ERROR")
                self.log_message("   Kurulum komutu: go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest", "INFO")
                return False
            
            self.log_message("✅ Subfinder aracı bulundu", "SUCCESS")
            subfinder_path = check_cmd.stdout.strip()
            self.log_message(f"   Yol: {subfinder_path}", "INFO")
            
            # Subfinder komutunu hazırla
            cmd = [
                'subfinder',
                '-dL', self.updated_domains_file,  # Dosyadan domain listesini oku
                '-all',                             # Tüm aktif kaynakları kullan
                '-o', self.subfinder_output_file,  # Çıktı dosyası
                '-silent'                           # Sessiz mod (sadece sonuçlar)
            ]
            
            self.log_message(f"\n🔍 Subfinder çalıştırılıyor ({len(self.updated_domains)} domain için)...", "INFO")
            self.log_message(f"   Komut: {' '.join(cmd)}", "INFO")
            self.log_message(f"   (Bu işlem birkaç dakika alabilir - oyuncak sabrını test et)", "WARNING")
            
            # Subfinder'ı çalıştır (300 saniye timeout = 5 dakika)
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  timeout=300,
                                  text=True)
            
            # Sonuç mesajlarını kontrol et
            if result.returncode != 0 and result.returncode != 1:  # 1 genellikle hiç sonuç bulunmadığında
                self.log_message(f"Subfinder uyarısı (Çıkış kodu: {result.returncode})", "WARNING")
                if result.stderr:
                    self.log_message(f"   Hata: {result.stderr[:300]}", "WARNING")
            
            # Subfinder çıktısını oku
            if os.path.exists(self.subfinder_output_file) and os.path.getsize(self.subfinder_output_file) > 0:
                with open(self.subfinder_output_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    self.subfinder_subdomains = set(line.strip().lower() for line in lines if line.strip())
                
                self.log_message(f"✅ Subfinder tamamlandı", "SUCCESS")
                self.log_message(f"   • Bulundu: {len(self.subfinder_subdomains)} subdomain", "INFO")
                self.log_message(f"   Dosya: {self.subfinder_output_file}", "INFO")
                return True
            else:
                self.log_message(f"⚠️  Subfinder çıktı dosyası oluşturulamadı", "WARNING")
                return False
        
        except subprocess.TimeoutExpired:
            self.log_message(f"Timeout: Subfinder işlemi 5 dakika içinde tamamlanamadı", "ERROR")
            return False
        except Exception as e:
            self.log_message(f"Subfinder çalıştırılırken hata oluştu: {str(e)}", "ERROR")
            return False
    
    def merge_results(self) -> bool:
        """
        crt.sh ve subfinder sonuçlarını birleştir ve deduplicate et
        
        Returns:
            bool: Başarılı ise True
        """
        self.log_message("\n" + "=" * 80, "INFO")
        self.log_message("AŞAMA 3: SONUÇLARIN BİRLEŞTİRİLMESİ", "INFO")
        self.log_message("=" * 80, "INFO")
        
        try:
            # Tüm subdomainleri birleştir (set union)
            all_subdomains = self.crt_subdomains.union(self.subfinder_subdomains)
            
            # Alfabet sırasında kaydet
            with open(self.final_output_file, 'w', encoding='utf-8') as f:
                for subdomain in sorted(all_subdomains):
                    f.write(subdomain + '\n')
            
            self.log_message(f"✅ Sonuçlar birleştirildi", "SUCCESS")
            self.log_message(f"   Dosya: {self.final_output_file}", "INFO")
            
            # İstatistikler
            self.log_message(f"\n📊 SONUÇ İSTATİSTİKLERİ:", "INFO")
            self.log_message(f"   • crt.sh subdomainleri: {len(self.crt_subdomains)}", "INFO")
            self.log_message(f"   • Subfinder subdomainleri: {len(self.subfinder_subdomains)}", "INFO")
            self.log_message(f"   • Toplam Unique Subdomainler: {len(all_subdomains)}", "SUCCESS")
            
            # Örtüşen subdomainleri göster
            overlap = self.crt_subdomains.intersection(self.subfinder_subdomains)
            self.log_message(f"   • Her iki araçta da bulunan: {len(overlap)}", "INFO")
            
            if overlap and len(overlap) <= 10:
                self.log_message(f"   • Örnekler: {', '.join(sorted(list(overlap))[:10])}", "INFO")
            
            return True
        
        except Exception as e:
            self.log_message(f"Sonuçlar birleştirilirken hata oluştu: {str(e)}", "ERROR")
            return False
    
    def print_summary(self):
        """
        İşlem özeti ve sonraki adımları yazdır
        """
        self.log_message("\n" + "=" * 80, "INFO")
        self.log_message("✅ TÜM İŞLEMLER BAŞARILI BİR ŞEKİLDE TAMAMLANDI", "SUCCESS")
        self.log_message("=" * 80, "INFO")
        
        self.log_message(f"\n📂 ÇIKTI DOSYALARI:", "INFO")
        self.log_message(f"   1. CRT.SH Subdomainleri:", "INFO")
        self.log_message(f"      {self.crt_output_file}", "INFO")
        self.log_message(f"   2. Subfinder Sonuçları:", "INFO")
        self.log_message(f"      {self.subfinder_output_file}", "INFO")
        self.log_message(f"   3. Güncellenmiş Domain Listesi (Debugging):", "INFO")
        self.log_message(f"      {self.updated_domains_file}", "INFO")
        self.log_message(f"   4. TÜM SUBDOMAINLER (MAIN OUTPUT):", "INFO")
        self.log_message(f"      {self.final_output_file}", "SUCCESS")
        
        self.log_message(f"\n💡 SONRAKI ADIMLAR:", "INFO")
        self.log_message(f"   1. Canlı host tespiti: httpx -l {self.final_output_file} -o live_hosts.txt", "INFO")
        self.log_message(f"   2. Web sunucusu tespit: whatweb -i {self.final_output_file}", "INFO")
        self.log_message(f"   3. Port taraması: nmap -iL {self.final_output_file}", "INFO")
        self.log_message(f"   4. Zafiyet taraması: nuclei -l {self.final_output_file}", "INFO")
        self.log_message(f"   5. Teknoloji tespit: wappalyzer {self.final_output_file}", "INFO")
        
        self.log_message(f"\n📋 ÖNEMLİ HATIRLATMALAR:", "WARNING")
        self.log_message(f"   • Bu araştırma sadece HackerOne kapsamında yapılmalıdır", "WARNING")
        self.log_message(f"   • İzin olmadan tarama YASAL DEĞİLDİR", "WARNING")
        self.log_message(f"   • Tüm ara dosyalar silinmemiştir - incelenmek için tutulmuştur", "WARNING")
    
    def run(self) -> bool:
        """
        Tüm recon işlemini çalıştır - ana işlem koordinatörü
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Aşama 1: Domainleri yükle
            if not self.load_domains():
                return False
            
            # Aşama 2: crt.sh sorgularını çalıştır
            if not self.run_crt_sh_queries():
                return False
            
            # Aşama 3: crt.sh sonuçlarını kaydet
            if not self.save_crt_results():
                return False
            
            # Aşama 4: Güncellenmiş domainleri kaydet
            if not self.save_updated_domains():
                return False
            
            # Aşama 5: Subfinder'ı çalıştır
            if not self.run_subfinder():
                self.log_message("Subfinder çalıştırılamadı, sonraki aşamaya geçiliyor...", "WARNING")
            
            # Aşama 6: Sonuçları birleştir
            if not self.merge_results():
                return False
            
            # Özet ve öneriler göster
            self.print_summary()
            
            return True
        
        except KeyboardInterrupt:
            self.log_message("\n⚠️  İşlem kullanıcı tarafından durduruldu (Ctrl+C)", "WARNING")
            return False
        except Exception as e:
            self.log_message(f"\n❌ Beklenmeyen bir hata oluştu: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            return False


def main():
    """
    Ana program - ReconAutomation sınıfını başlat ve çalıştır
    """
    try:
        recon = ReconAutomation()
        success = recon.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ KRITIK HATA: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
