=========================================
 Gold Price Checker - Project Setup
=========================================

โปรเจกต์นี้ประกอบด้วย 2 ส่วนหลัก: Frontend (หน้าเว็บสำหรับผู้ใช้) และ Backend (ระบบจัดการหลังบ้านและ API)

-----------------------------------------
 โครงสร้างโฟลเดอร์
-----------------------------------------

/ (gold-price-checker/)
|-- api/                (Backend ทั้งหมด)
|   |-- admin/          (หน้า Admin Panel)
|   |-- api/            (API สำหรับ Auth)
|   |-- config/
|   |-- includes/       (ไฟล์ Helper ต่างๆ)
|   |-- vendor/         (ไลบรารีของ Composer)
|   |-- .env            (ไฟล์ตั้งค่า)
|   |-- bootstrap.php
|   `-- server.py       (API สำหรับราคาทอง)
|
|-- js/                 (JavaScript ของ Frontend)
|   |-- config.js
|   `-- script.js
|
`-- index.html          (ไฟล์หลักของ Frontend)


-----------------------------------------
 ขั้นตอนการติดตั้งและรันโปรเจกต์
-----------------------------------------

**สิ่งที่คุณต้องมี:**
1. XAMPP (หรือเว็บเซิร์ฟเวอร์อื่นที่มี PHP 8+ และ MySQL/MariaDB)
2. Python 3.x
3. Composer

**ขั้นตอนที่ 1: ตั้งค่า Backend (PHP)**

1.  **นำเข้าฐานข้อมูล:**
    *   สร้างฐานข้อมูลใหม่ใน phpMyAdmin ชื่อว่า `goldapidb`
    *   นำเข้า (Import) ไฟล์ `.sql` ที่อยู่ในโฟลเดอร์ `api/sql/` เข้าไปยังฐานข้อมูล `goldapidb`

2.  **ตั้งค่าการเชื่อมต่อ:**
    *   ไปที่โฟลเดอร์ `api/`
    *   คัดลอกไฟล์ `.env.example` แล้วเปลี่ยนชื่อเป็น `.env`
    *   เปิดไฟล์ `.env` แล้วตรวจสอบการตั้งค่า `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` ให้ตรงกับ phpMyAdmin ของคุณ

3.  **ติดตั้งไลบรารี PHP:**
    *   เปิด Terminal หรือ Command Prompt
    *   เข้าไปที่โฟลเดอร์ `api/` (เช่น `cd D:\xampp\htdocs\gold-price-checker\api`)
    *   รันคำสั่ง: `composer install`

**ขั้นตอนที่ 2: ตั้งค่า Backend (Python)**

1.  **ติดตั้งไลบรารี Python:**
    *   เปิด Terminal หรือ Command Prompt
    *   เข้าไปที่โฟลเดอร์ `api/` (ที่เดียวกับ `server.py`)
    *   รันคำสั่ง: `pip install -r requirements.txt` (ถ้ามีไฟล์ `requirements.txt`)
    *   หรือติดตั้งทีละตัว: `pip install Flask Flask-CORS requests beautifulsoup4`

**ขั้นตอนที่ 3: การรันโปรเจกต์**

1.  **Start XAMPP:** เปิด XAMPP Control Panel แล้ว Start **Apache** และ **MySQL**

2.  **รันเซิร์ฟเวอร์ Python:**
    *   เปิด Terminal ใหม่
    *   เข้าไปที่โฟลเดอร์ `api/`
    *   รันคำสั่ง: `python server.py`
    *   **สำคัญ:** ห้ามปิด Terminal นี้

3.  **เข้าถึงหน้าเว็บ:**
    *   **Frontend (หน้าบ้าน):** เปิดเบราว์เซอร์แล้วไปที่ `http://localhost/gold-price-checker/`
    *   **Backend (Admin Panel):** สามารถเข้าถึงได้ที่ `http://localhost/gold-price-checker/api/admin/` (หลังจากล็อกอินเป็น Admin แล้ว)

-----------------------------------------
 ข้อมูลการล็อกอินเริ่มต้น
-----------------------------------------

*   **Admin:**
    *   Email: `admin@admin.com`
    *   Password: (ระบุรหัสผ่านที่คุณตั้งไว้)admin123
*   **User:**
    *   Email: `a123@gmail.com`
    *   Password: (ระบุรหัสผ่านที่คุณตั้งไว้)

=========================================
