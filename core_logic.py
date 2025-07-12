# core_logic.py
import re
import csv
import logging

logger = logging.getLogger(__name__)

def parse_txt_file_smartly(file_path: str) -> dict:
    contacts, invalid_lines, was_structured = [], 0, False
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = [next(f, '').strip() for _ in range(5)]
            if any(',' in line and any(c.isalpha() for c in line) for line in first_lines): was_structured = True
            f.seek(0)
            if was_structured:
                reader = csv.reader(f)
                try:
                    header_line = next(reader)
                    header_map = {h.lower().strip().replace(' ', ''): i for i, h in enumerate(header_line)}
                    name_col, phone_col = header_map.get('nama') or header_map.get('name'), header_map.get('telepon') or header_map.get('phone') or header_map.get('nomorhp')
                    if name_col is None or phone_col is None: was_structured = False
                except StopIteration: was_structured = False
                if was_structured:
                    for row in reader:
                        try:
                            name, phone = row[name_col].strip(), row[phone_col].strip()
                            if name and phone: contacts.append({'Name': name, 'Phone': re.sub(r'[\s-]', '', phone)})
                            else: invalid_lines += 1
                        except IndexError: invalid_lines += 1
            if not was_structured:
                f.seek(0); content = f.read()
                found_numbers = re.findall(r'\+?\d[\d\s-]{7,}', content)
                for num in found_numbers: contacts.append({'Name': '', 'Phone': re.sub(r'[\s-]', '', num)})
        unique_contacts = {contact['Phone']: contact for contact in contacts if contact['Phone']}
        return {'contacts': list(unique_contacts.values()), 'invalid_lines': invalid_lines, 'was_structured': was_structured and bool(unique_contacts)}
    except Exception as e:
        logger.error(f"Gagal mem-parsing file {file_path}: {e}")
        return {'contacts': [], 'invalid_lines': 0, 'was_structured': False}

def write_contact_files(contacts: list, output_dir: str, **kwargs) -> tuple[list, int]:
    contacts_per_file, custom_filename, export_format, base_name = kwargs.get('contacts_per_file'), kwargs.get('custom_filename', 'kontak'), kwargs.get('export_format', 'vcf'), kwargs.get('base_name', '')
    output_files, contact_index, file_index, out_file = [], 0, 1, None
    total_contacts = len(contacts)
    for contact in contacts:
        if contacts_per_file and contact_index % contacts_per_file == 0:
            if out_file: out_file.close()
            start_num, end_num = (file_index - 1) * contacts_per_file + 1, min(file_index * contacts_per_file, total_contacts)
            fname = f"{custom_filename}_{start_num}-{end_num}.{export_format}"
            output_path = os.path.join(output_dir, fname); output_files.append(output_path)
            out_file = open(output_path, 'w', encoding='utf-8')
            if export_format == 'csv': out_file.write("Name,Phone\n")
            file_index += 1
        elif not out_file:
            output_path = os.path.join(output_dir, f"{custom_filename}.{export_format}"); output_files.append(output_path)
            out_file = open(output_path, 'w', encoding='utf-8')
            if export_format == 'csv': out_file.write("Name,Phone\n")
        contact_name, phone_number = contact.get('Name') or f"{base_name} {contact_index + 1}", contact.get('Phone', '')
        if export_format == 'vcf': out_file.write(f'BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name}\nTEL;TYPE=CELL:{phone_number}\nEND:VCARD\n\n')
        else: out_file.write(f'"{contact_name}","{phone_number}"\n')
        contact_index += 1
    if out_file: out_file.close()
    return output_files, total_contacts