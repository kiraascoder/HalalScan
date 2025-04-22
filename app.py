from flask import Flask, render_template, request, redirect, url_for
import pytesseract
from pytesseract import Output
import cv2
import sqlite3
import re
from difflib import get_close_matches
from datetime import datetime
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Konfigurasi Tesseract
pytesseract.pytesseract.tesseract_cmd = 'tesseract'
myconfig = r"--psm 11 --oem 3"

def get_db_connection():
    conn = sqlite3.connect('sertifikats.db')
    conn.row_factory = sqlite3.Row
    return conn

def find_certificate_by_last_digits(last_digits):
    conn = get_db_connection()
    cursor = conn.execute("SELECT certificate_no, product_name, company, factory_address, certificate_issued FROM certificates WHERE certificate_no LIKE ?", ('%' + last_digits,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def find_closest_match(detected_cert_no, all_certificates):
    closest_matches = get_close_matches(detected_cert_no, all_certificates, n=1, cutoff=0.6)
    return closest_matches[0] if closest_matches else None

@app.route('/')
def index():
    return render_template('ocr.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Cek apakah input manual digunakan
    manual_certificate_no = request.form.get('manual_certificate_no')
    if manual_certificate_no:
        # Bersihkan nomor sertifikat manual
        cleaned_cert_no = re.sub(r'\D', '', manual_certificate_no)
        
        # Cari sertifikat berdasarkan nomor yang dimasukkan secara manual
        matched_certificate = None
        if len(cleaned_cert_no) >= 5:
            last_five_digits = cleaned_cert_no[-5:]
            last_four_digits = cleaned_cert_no[-4:]
            
            rows_five = find_certificate_by_last_digits(last_five_digits)
            if rows_five:
                matched_certificate = rows_five[0]
            
            if not matched_certificate:
                rows_four = find_certificate_by_last_digits(last_four_digits)
                if rows_four:
                    matched_certificate = rows_four[0]

        if not matched_certificate:
            # Jika tidak ditemukan, cari dengan closest match
            conn = get_db_connection()
            cursor = conn.execute("SELECT certificate_no FROM certificates")
            all_certificates = [row['certificate_no'] for row in cursor.fetchall()]
            conn.close()

            closest_match = find_closest_match(cleaned_cert_no, all_certificates)
            if closest_match:
                rows_closest = find_certificate_by_last_digits(closest_match[-5:])
                if rows_closest:
                    matched_certificate = rows_closest[0]

        return render_template('ocr.html', matched_certificate=matched_certificate, detected_certificates=None, output_image=None)

    # Jika tidak ada input manual, proses upload gambar
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        img = cv2.imread(filepath)
        height, width, _ = img.shape

        data = pytesseract.image_to_data(img, config=myconfig, output_type=Output.DICT)

        amount_boxes = len(data['text'])
        detected_certificates = []
        for i in range(amount_boxes):
            if float(data['conf'][i]) > 20:
                (x, y, width_box, height_box) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                img = cv2.rectangle(img, (x, y), (x + width_box, y + height_box), (0, 255, 0), 2)
                text = data['text'][i]
                img = cv2.putText(img, text, (x, y + height_box + 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3, cv2.LINE_AA)
                detected_certificates.append(text.strip())

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'hasil_tampilan_{timestamp}.jpeg')
        cv2.imwrite(output_path, img)

        matched_certificate = None
        all_certificates = []

        conn = get_db_connection()
        cursor = conn.execute("SELECT certificate_no FROM certificates")
        all_certificates = [row['certificate_no'] for row in cursor.fetchall()]
        conn.close()

        for cert_no in detected_certificates:
            cleaned_cert_no = re.sub(r'\D', '', cert_no)
            if len(cleaned_cert_no) >= 5:
                last_five_digits = cleaned_cert_no[-5:]
                last_four_digits = cleaned_cert_no[-4:]
                
                rows_five = find_certificate_by_last_digits(last_five_digits)
                if rows_five:
                    matched_certificate = rows_five[0]
                    break
                
                rows_four = find_certificate_by_last_digits(last_four_digits)
                if rows_four:
                    matched_certificate = rows_four[0]
                    break

        if not matched_certificate and detected_certificates:
            for cert_no in detected_certificates:
                cleaned_cert_no = re.sub(r'\D', '', cert_no)
                closest_match = find_closest_match(cleaned_cert_no, all_certificates)
                if closest_match:
                    rows_closest = find_certificate_by_last_digits(closest_match[-5:])
                    if rows_closest:
                        matched_certificate = rows_closest[0]
                    break

        return render_template('ocr.html', matched_certificate=matched_certificate, detected_certificates=detected_certificates, output_image=output_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)