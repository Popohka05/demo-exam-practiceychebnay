import csv
import glob
import os
import re
from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Product


class Command(BaseCommand):
    help = 'Import ALL CSVs automatically'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', nargs='?', type=str)

    def handle(self, *args, **options):
        import_path = r"D:\django.demo\Прил_ОЗ_КОД 09.02.07-2-2026\БУ\Модуль 1\import"
        csv_files = glob.glob(os.path.join(import_path, "*.csv"))
        
        if options['csv_file']:
            csv_files = [options['csv_file']] + csv_files
            
        total = 0
        for csv_file in csv_files:
            if not os.path.exists(csv_file): 
                continue
                
            self.stdout.write(f"📁 {os.path.basename(csv_file)}")
            imported = 0
            
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            sku = (row.get('код') or row.get('артикул') or 
                                  row.get('sku') or row.get('Код') or 
                                  str(hash(str(row)))[:50])[:50]
                            
                            name = (row.get('название') or row.get('товар') or 
                                   row.get('Наименование') or 
                                   list(row.values())[0] or 'Unnamed')[:100]
                            
                            price_str = next((v for v in row.values() 
                                            if re.search(r'\d', str(v))), '0')
                            price = Decimal(str(price_str).replace(',', '.').replace(' ', '') or '0')
                            
                            Product.objects.update_or_create(
                                sku=sku,
                                defaults={'name': name, 'price': price}
                            )
                            imported += 1
                        except: pass
                        
            except Exception as e: 
                self.stdout.write(f" {e}")
                continue
                
            self.stdout.write(f" {imported}")
            total += imported
        
        self.stdout.write(self.style.SUCCESS(f"🎉 TOTAL IMPORTED: {total}"))
