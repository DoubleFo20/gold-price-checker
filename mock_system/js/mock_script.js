document.addEventListener('DOMContentLoaded', () => {

    // --- START: การตั้งค่า EmailJS ---
    const EMAILJS_PUBLIC_KEY = "VWVdMGWQlikTWoRtB";
    const EMAILJS_SERVICE_ID = "service_zghhqpi";
    const EMAILJS_TEMPLATE_ID = "template_goldalert";
    // --- END: การตั้งค่า ---
    
    // [แก้ไข] ตรวจสอบว่า Key ไม่ใช่ค่าเริ่มต้น
    if (EMAILJS_PUBLIC_KEY && EMAILJS_PUBLIC_KEY !== "YOUR_PUBLIC_KEY") {
        emailjs.init(EMAILJS_PUBLIC_KEY);
        console.log("EmailJS Initialized.");
    } else {
        console.warn("EmailJS Public Key is not set. Real email sending will fail.");
    }

    const currentPriceDisplay = document.getElementById('current-price-display');
    const setAlertBtn = document.getElementById('set-alert-btn');
    const statusMessage = document.getElementById('status-message');
    
    // --- START: ส่วนควบคุมราคาจำลอง ---
    const START_PRICE = 65000;
    const END_PRICE = 60000;
    const UPDATE_INTERVAL = 3000; // อัปเดตทุก 3 วินาที
    let currentPrice = START_PRICE;
    let activeAlert = null;
    // --- END ---

    // [แก้ไข] ฟังก์ชันนี้จะทำให้ราคาวิ่ง
// (ค้นหาและแทนที่ฟังก์ชัน updateMockPrice เดิม)
function updateMockPrice() {
    // กำหนดทิศทางของราคา (true = ขาขึ้น, false = ขาลง)
    // เราใช้ตัวแปร isTrendingUp ที่อยู่นอกฟังก์ชันเพื่อให้มัน "จำ" ทิศทางเดิมได้
    if (typeof window.isTrendingUp === 'undefined') {
        window.isTrendingUp = false; // เริ่มต้นที่ขาลง
    }

    if (window.isTrendingUp) {
        // ขาขึ้น: เพิ่มราคาขึ้น
        currentPrice += (Math.random() * 250 + 50);
        if (currentPrice > START_PRICE) {
            currentPrice = START_PRICE;
            window.isTrendingUp = false; // เมื่อถึงจุดสูงสุด ให้เปลี่ยนเป็นขาลง
        }
    } else {
        // ขาลง: ลดราคาลง
        currentPrice -= (Math.random() * 250 + 50);
        if (currentPrice < END_PRICE) {
            currentPrice = END_PRICE;
            window.isTrendingUp = true; // เมื่อถึงจุดต่ำสุด ให้เปลี่ยนเป็นขาขึ้น
        }
    }

    // อัปเดตราคาบนหน้าจอ
    const formattedPrice = `฿ ${currentPrice.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (currentPriceDisplay) {
        currentPriceDisplay.textContent = formattedPrice;
    }
    
    // ตรวจสอบ Alert ทุกครั้งที่ราคาเปลี่ยน
    checkPriceForAlert();
}

    function setMockAlert() {
        const alertType = document.getElementById('alert-type').value;
        const targetPrice = parseFloat(document.getElementById('target-price').value);
        const email = document.getElementById('user-email').value;

        if (!targetPrice || targetPrice <= 0 || !email) {
            alert('กรุณากรอกข้อมูลให้ครบถ้วน');
            return;
        }
        
        activeAlert = { type: alertType, target: targetPrice, email: email };
        if (statusMessage) {
            statusMessage.textContent = `ตั้งค่าสำเร็จ! กำลังรอราคาถึงเป้าหมาย...`;
            statusMessage.style.color = 'blue';
        }
    }
    
    function checkPriceForAlert() {
        if (!activeAlert) return;

        let triggered = false;
        if (activeAlert.type === 'below' && currentPrice <= activeAlert.target) {
            triggered = true;
        } else if (activeAlert.type === 'above' && currentPrice >= activeAlert.target) {
            triggered = true;
        }

        if (triggered) {
            if (statusMessage) {
                statusMessage.textContent = 'ราคาถึงเป้าหมาย! กำลังส่งอีเมล...';
                statusMessage.style.color = 'orange';
            }

            const templateParams = {
                to_email: activeAlert.email,
                subject: `🔔 แจ้งเตือนราคาทอง - ถึงเป้าหมายแล้ว!`,
                message: `ราคาปัจจุบัน (${currentPrice.toLocaleString()}) ได้ถึงเป้าหมายที่คุณตั้งไว้ (${activeAlert.target.toLocaleString()}) แล้ว`
            };
            
            emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, templateParams)
                .then(function(response) {
                   if (statusMessage) {
                       statusMessage.textContent = `✅ ส่งอีเมลแจ้งเตือนไปที่ ${activeAlert.email} สำเร็จ!`;
                       statusMessage.style.color = 'green';
                   }
                   alert(`ส่งอีเมลแจ้งเตือนสำเร็จ!`);
                }, function(error) {
                   if (statusMessage) {
                       statusMessage.textContent = `❌ ส่งอีเมลล้มเหลว: ${error.text || 'ตรวจสอบการตั้งค่า'}`;
                       statusMessage.style.color = 'red';
                   }
                   alert(`ส่งอีเมลล้มเหลว!`);
                });
            
            activeAlert = null; 
        }
    }

    // เริ่มการทำงาน
    if (setAlertBtn) {
        setAlertBtn.addEventListener('click', setMockAlert);
    }
    
    // [สำคัญ] เริ่มต้นการเคลื่อนไหวของราคา
    setInterval(updateMockPrice, UPDATE_INTERVAL); 
    
    if (currentPriceDisplay) {
        currentPriceDisplay.textContent = `฿ ${START_PRICE.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
});