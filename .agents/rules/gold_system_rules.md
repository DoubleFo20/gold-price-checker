---
description: กฎระเบียบและมาตรฐานสถาปัตยกรรมสำหรับระบบติดตามราคาทองคำ (Gold Price Checker)
globs: ["api/**", "js/**", "components/**", "*.html", "*.css"]
---

# Gold Price Checker — System Development Rules

## 1. Data Authenticity & Thai Gold Standards
- **Gold Purity Standards**: สินทรัพย์ทองคำไทยมาตรฐานสมาคมฯ ทั้ง "ทองคำแท่ง" และ "ทองรูปพรรณ" ต้องระบุเป็น **96.5%** เสมอ ห้ามระบุเป็น 90%
- **Primary Source Precedence**: แหล่งข้อมูลราคาทองคำทางการต้องอิงจากสมาคมค้าทองคำ (Thongkam.com / GTA) เป็น Priority 1 เสมอ ห้ามนำราคาหน้าร้านเอกชนมาปะปนเป็นราคากลาง

## 2. Zero-Failure Scraper & Resilient Fallback Architecture
- **No 500 on Data Failure**: ทุก Endpoint ที่ดึงข้อมูลภายนอก (`/api/thai-gold-price`, `/api/world-gold-price`) ต้องมีระบบ Fallback 4 ลำดับขั้น:
  1. Primary Scraper (Timeout <= 4.0s)
  2. In-memory Fresh/Stale Cache
  3. Local Database (`price_cache` ล่าสุด)
  4. Derived Formula / Baseline Guarantee
- ห้ามโยน Unhandled Exception ออกไปเด็ดขาด ต้องส่งสถานะ HTTP 200 พร้อมชุดข้อมูลที่ปลอดภัยเสมอ

## 3. UI/UX Accessibility & Visual Comfort (WCAG AA)
- **Contrast Ratio**: ข้อความและตัวเลขสำคัญบนพื้นหลังสว่าง ต้องมี Contrast Ratio ไม่ต่ำกว่า 4.5:1 ตามมาตรฐาน WCAG AA ห้ามใช้ `#d4af37` กับข้อความบนพื้นขาว ให้ใช้ `--brand-gold: #B8860B` หรือ `#996F00` แทน
- **No Internal Jargon**: ห้ามแสดงคำศัพท์เทคนิคของกระบวนการพัฒนา (เช่น "Minimalist", "Walk-forward backtest", "Agent A/B") ต่อผู้ใช้งานทั่วไป ให้ใช้ภาษาทางการเงินที่กระชับ ชัดเจน
- **Frictionless Utility**: ฟังก์ชันพื้นฐาน เช่น เครื่องคำนวณมูลค่าทองคำ ต้องเปิดให้ผู้ใช้งานทั่วไป (Guest) ใช้งานได้ทันทีโดยไม่ต้องบังคับล็อกอิน

## 4. Performance & Chart Decoupling
- ก่อนสร้าง Chart.js Instance ใหม่บน Canvas เดิม ต้องตรวจสอบและเรียกใช้ `chart.destroy()` เสมอ
- ในหน้า Dashboard หรือ Admin ให้แยกกระดานสรุปตัวเลข (KPI Cards) ออกจากกราฟความหนาแน่นสูง เพื่อให้หน้าเว็บพร้อมตอบสนองได้ทันที
