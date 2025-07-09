from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pandas as pd
import os
import random
import string
from werkzeug.utils import secure_filename

# مسیر ذخیره فایل‌ها
DATA_DIR = r"C:\Users\MANDEGAR\Desktop\project\data"
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "lottery_data.xlsx")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "receipts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# تابع نرمال‌سازی شماره موبایل
def normalize_phone(phone):
    phone = phone.strip()
    if phone.startswith('+98'):
        phone = phone[3:]
    if phone.startswith('0'):
        phone = phone[1:]
    return phone


# تابع تولید کپچای ترکیبی حروف و عدد
def generate_captcha(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


# 🔁 روت دریافت کپچای جدید برای AJAX
@app.route('/refresh_captcha')
def refresh_captcha():
    new_captcha = generate_captcha()
    session['captcha'] = new_captcha
    return jsonify({'captcha': new_captcha})


# 🧾 روت اصلی فرم
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        phone = request.form.get('phone', '').strip()
        card_used = request.form.get('card_used', '').strip()
        card_owner = request.form.get('card_owner', '').strip()
        receipt = request.files.get('receipt')
        captcha_input = request.form.get('captcha', '').strip()

        correct_captcha = session.get('captcha', '')

        # بررسی کپچا به صورت case-insensitive
        if not captcha_input or captcha_input.lower() != correct_captcha.lower():
            flash("❌ کد امنیتی اشتباه است.", "danger")
            session['captcha'] = generate_captcha()
            return render_template('form.html', captcha=session['captcha'])

        # بررسی کامل بودن فرم
        if not (fullname and phone and card_used and card_owner and receipt):
            flash("لطفاً همه فیلدها را پر کنید.", "danger")
            session['captcha'] = generate_captcha()
            return render_template('form.html', captcha=session['captcha'])

        phone_normalized = normalize_phone(phone)

        # چک تکراری بودن شماره
        if os.path.exists(DATA_FILE):
            df = pd.read_excel(DATA_FILE, dtype={'phone': str})
            if 'phone' in df.columns:
                phones_normalized = df['phone'].astype(str).apply(normalize_phone)
                if phone_normalized in phones_normalized.values:
                    flash("❌ این شماره قبلاً ثبت شده است.", "danger")
                    session['captcha'] = generate_captcha()
                    return render_template('form.html', captcha=session['captcha'])

        # ذخیره فایل فیش
        ext = os.path.splitext(secure_filename(receipt.filename))[1]
        filename = f"{phone}{ext}"
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        receipt.save(receipt_path)

        # ذخیره اطلاعات
        data = {
            "fullname": fullname,
            "phone": phone,  # ذخیره دقیق واردشده توسط کاربر
            "card_used": card_used,
            "card_owner": card_owner,
            "receipt_file": receipt_path,
        }

        if os.path.exists(DATA_FILE):
            df = pd.read_excel(DATA_FILE, dtype={'phone': str})
        else:
            df = pd.DataFrame(columns=data.keys())

        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_excel(DATA_FILE, index=False)

        flash("✅ اطلاعات با موفقیت ذخیره شد. نتیجه پس از بررسی به تلگرام ارسال می‌گردد.", "success")
        return redirect(url_for('index'))

    # GET: فرم را با کپچا نمایش بده
    session['captcha'] = generate_captcha()
    return render_template('form.html', captcha=session['captcha'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

