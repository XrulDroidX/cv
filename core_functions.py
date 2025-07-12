# core_functions.py

import os
import csv

# --- Definisi Field Kontak ---
# Ini memungkinkan kita untuk mudah menambahkan field baru di masa depan
CONTACT_FIELDS = ['FN', 'TEL;TYPE=CELL', 'EMAIL', 'ADR', 'ORG', 'TITLE', 'BDAY', 'NOTE']
CSV_HEADERS = ['Name', 'Phone', 'Email', 'Address', 'Organization', 'Job Title', 'Birthday', 'Notes']

def parse_vcf_file(file_path):
    """Membaca file VCF dan mengubahnya menjadi daftar dictionary kontak."""
    contacts = []
    with open(file_path, 'r', encoding='utf-8') as f:
        current_contact = {}
        for line in f:
            line = line.strip()
            if line.upper() == 'BEGIN:VCARD':
                current_contact = {key: '' for key in CSV_HEADERS}
            elif line.upper() == 'END:VCARD':
                if current_contact.get('Name') or current_contact.get('Phone'):
                    contacts.append(current_contact)
            else:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    field, value = parts
                    # Mencocokkan field VCF dengan header CSV kita
                    if field.upper().startswith('FN'): current_contact['Name'] = value
                    elif field.upper().startswith('TEL'): current_contact['Phone'] = value
                    elif field.upper().startswith('EMAIL'): current_contact['Email'] = value
                    elif field.upper().startswith('ADR'): current_contact['Address'] = value.replace(';', ' ').strip()
                    elif field.upper().startswith('ORG'): current_contact['Organization'] = value
                    elif field.upper().startswith('TITLE'): current_contact['Job Title'] = value
                    elif field.upper().startswith('BDAY'): current_contact['Birthday'] = value
                    elif field.upper().startswith('NOTE'): current_contact['Notes'] = value
    return contacts

def parse_txt_file(file_path, has_header=True):
    """Membaca file TXT/CSV dan mengubahnya menjadi daftar dictionary kontak."""
    contacts = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        if has_header:
            try:
                header = next(reader)
            except StopIteration:
                return [] # File kosong
        else:
            # Jika tidak ada header, asumsikan urutannya standar
            header = CSV_HEADERS
        
        for row in reader:
            contact = {key: '' for key in CSV_HEADERS}
            for i, value in enumerate(row):
                if i < len(header):
                    contact[header[i]] = value
            if contact.get('Name') or contact.get('Phone'):
                contacts.append(contact)
    return contacts

def deduplicate_contacts(contacts):
    """Menghapus kontak duplikat berdasarkan nomor telepon."""
    unique_contacts = {}
    for contact in contacts:
        phone = contact.get('Phone')
        if phone:
            # Jika nomor belum ada, tambahkan. Ini akan mengabaikan duplikat berikutnya.
            if phone not in unique_contacts:
                unique_contacts[phone] = contact
    return list(unique_contacts.values())

def merge_contacts(list_of_contacts, deduplicate=True):
    """Menggabungkan beberapa daftar kontak menjadi satu."""
    merged = []
    for contact_list in list_of_contacts:
        merged.extend(contact_list)
    
    if deduplicate:
        return deduplicate_contacts(merged)
    return merged

def write_vcf_file(contacts, output_path):
    """Menulis daftar dictionary kontak ke dalam format file VCF."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for contact in contacts:
            f.write('BEGIN:VCARD\n')
            f.write('VERSION:3.0\n')
            if contact.get('Name'): f.write(f"FN:{contact['Name']}\n")
            if contact.get('Phone'): f.write(f"TEL;TYPE=CELL:{contact['Phone']}\n")
            if contact.get('Email'): f.write(f"EMAIL:{contact['Email']}\n")
            if contact.get('Address'): f.write(f"ADR;TYPE=HOME:;;{contact['Address']}\n")
            if contact.get('Organization'): f.write(f"ORG:{contact['Organization']}\n")
            if contact.get('Job Title'): f.write(f"TITLE:{contact['Job Title']}\n")
            if contact.get('Birthday'): f.write(f"BDAY:{contact['Birthday']}\n")
            if contact.get('Notes'): f.write(f"NOTE:{contact['Notes']}\n")
            f.write('END:VCARD\n\n')
    return len(contacts)

def write_csv_file(contacts, output_path, format_type='standard'):
    """Menulis daftar dictionary kontak ke dalam file CSV dengan format tertentu."""
    # Format Google CSV memerlukan header spesifik
    google_headers = [
        'Name', 'Given Name', 'Additional Name', 'Family Name', 'Yomi Name', 'Given Name Yomi', 
        'Additional Name Yomi', 'Family Name Yomi', 'Name Prefix', 'Name Suffix', 'Initials', 
        'Nickname', 'Short Name', 'Maiden Name', 'Birthday', 'Gender', 'Location', 'Billing Information', 
        'Directory Server', 'Mileage', 'Occupation', 'Hobby', 'Sensitivity', 'Priority', 'Subject', 
        'Notes', 'Language', 'Photo', 'Group Membership', 'E-mail 1 - Type', 'E-mail 1 - Value', 
        'Phone 1 - Type', 'Phone 1 - Value', 'Address 1 - Type', 'Address 1 - Formatted'
    ]
    
    headers = google_headers if format_type == 'google' else CSV_HEADERS
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        
        for contact in contacts:
            if format_type == 'google':
                google_contact = {
                    'Name': contact.get('Name'),
                    'Birthday': contact.get('Birthday'),
                    'Notes': contact.get('Notes'),
                    'E-mail 1 - Type': '* Other',
                    'E-mail 1 - Value': contact.get('Email'),
                    'Phone 1 - Type': 'Mobile',
                    'Phone 1 - Value': contact.get('Phone'),
                    'Address 1 - Type': 'Home',
                    'Address 1 - Formatted': contact.get('Address')
                }
                writer.writerow(google_contact)
            else: # Format standar
                writer.writerow(contact)
                
    return len(contacts)