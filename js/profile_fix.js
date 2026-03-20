// Profile Modal Fix - สร้างใหม่ทั้งหมด
console.log('Loading profile fix...');

// ฟังก์ชันสร้าง modal ใหม่
function createProfileModal() {
    // ลบ modal เก่าถ้ามี
    const oldModal = document.getElementById('profileModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    // สร้าง modal ใหม่
    const modal = document.createElement('div');
    modal.id = 'profileModal';
    modal.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 999999;
            display: none;
            justify-content: center;
            align-items: center;
        ">
            <div style="
                background: white;
                padding: 40px;
                border-radius: 12px;
                max-width: 600px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
                position: relative;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            ">
                <span style="
                    position: absolute;
                    top: 15px;
                    right: 15px;
                    font-size: 28px;
                    cursor: pointer;
                    color: #666;
                " onclick="closeProfileModal()">&times;</span>
                
                <h2 style="color: #B8860B; margin-top: 0; margin-bottom: 25px;">ข้อมูลส่วนตัว</h2>
                
                <!-- ข้อมูลพื้นฐาน -->
                <div style="margin-bottom: 30px;">
                    <h3 style="color: #333; margin-bottom: 15px;">ข้อมูลผู้ใช้</h3>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: bold;">ชื่อ:</label>
                        <input type="text" id="profileName" style="
                            width: 100%;
                            padding: 12px;
                            border: 1px solid #ddd;
                            border-radius: 6px;
                            font-size: 16px;
                            box-sizing: border-box;
                        ">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: bold;">อีเมล:</label>
                        <input type="email" id="profileEmail" readonly style="
                            width: 100%;
                            padding: 12px;
                            border: 1px solid #ddd;
                            border-radius: 6px;
                            font-size: 16px;
                            box-sizing: border-box;
                            background: #f5f5f5;
                            color: #666;
                        ">
                        <small style="color: #666; font-size: 12px;">* ไม่สามารถแก้ไขได้</small>
                    </div>
                </div>
                
                <!-- การแจ้งเตือนราคาทอง -->
                <div style="margin-bottom: 30px; padding: 20px; background: #f9f9f9; border-radius: 8px;">
                    <h3 style="color: #333; margin-top: 0; margin-bottom: 15px;">การแจ้งเตือนราคาทอง</h3>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: bold;">ตั้งค่าราคาทองเมื่อถึง:</label>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <input type="number" id="alertPrice" placeholder="ระบุราคา" style="
                                flex: 1;
                                padding: 10px;
                                border: 1px solid #ddd;
                                border-radius: 6px;
                                font-size: 14px;
                            ">
                            <button onclick="saveAlertSettings()" style="
                                background: #16A085;
                                color: white;
                                border: none;
                                padding: 10px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-size: 14px;
                            ">บันทึก</button>
                        </div>
                        <small style="color: #666; font-size: 12px;">* จะแจ้งเตือนเมื่อราคาทองถึงระดับที่ตั้งไว้</small>
                    </div>
                    <div id="alertStatus" style="color: #16A085; font-size: 14px;"></div>
                </div>
                
                <!-- ประวัติการพยากรณ์ -->
                <div style="margin-bottom: 30px; padding: 20px; background: #f0f8ff; border-radius: 8px;">
                    <h3 style="color: #333; margin-top: 0; margin-bottom: 15px;">ประวัติการพยากรณ์ราคาทอง</h3>
                    <div id="forecastHistory" style="max-height: 200px; overflow-y: auto;">
                        <p style="color: #666; font-size: 14px;">กำลังโหลดข้อมูล...</p>
                    </div>
                </div>
                
                <div style="text-align: right; margin-top: 20px;">
                    <button onclick="closeProfileModal()" style="
                        background: #B8860B;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 16px;
                    ">ปิด</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    console.log('Profile modal created');
}

// ฟังก์ชันแสดง modal
function showProfileModal() {
    console.log('Show profile modal called');
    
    let modal = document.getElementById('profileModal');
    if (!modal) {
        createProfileModal();
        modal = document.getElementById('profileModal');
    }
    
    // ใช้ modal โดยตรงแทน modalOverlay
    if (modal) {
        modal.style.display = 'flex';
        console.log('Modal display set to flex');
    }
    
    // กรอกข้อมูลผู้ใช้
    if (window.currentUser) {
        const nameInput = document.getElementById('profileName');
        const emailInput = document.getElementById('profileEmail');
        if (nameInput) nameInput.value = window.currentUser.name || '';
        if (emailInput) emailInput.value = window.currentUser.email || '';
    }
    
    // โหลดข้อมูลเพิ่มเติม
    loadAlertSettings();
    loadForecastHistory();
}

// ฟังก์ชันบันทึกการแจ้งเตือน
function saveAlertSettings() {
    const alertPrice = document.getElementById('alertPrice').value;
    const statusDiv = document.getElementById('alertStatus');
    
    if (!alertPrice) {
        statusDiv.textContent = 'กรุณาระบุราคาที่ต้องการแจ้งเตือน';
        statusDiv.style.color = '#e74c3c';
        return;
    }
    
    // จำลองการบันทึก (ในระบบจริงต้องเชื่อมต่อ API)
    localStorage.setItem('goldAlertPrice', alertPrice);
    
    statusDiv.textContent = `บันทึกการแจ้งเตือนราคาทองที่ ${Number(alertPrice).toLocaleString()} บาท เรียบร้อย`;
    statusDiv.style.color = '#16A085';
    
    // ล้างข้อความหลัง 3 วินาที
    setTimeout(() => {
        statusDiv.textContent = '';
    }, 3000);
}

// ฟังก์ชันโหลดการตั้งค่าแจ้งเตือน
function loadAlertSettings() {
    const savedAlert = localStorage.getItem('goldAlertPrice');
    const alertInput = document.getElementById('alertPrice');
    if (savedAlert && alertInput) {
        alertInput.value = savedAlert;
    }
}

// ฟังก์ชันโหลดประวัติการพยากรณ์
function loadForecastHistory() {
    const historyDiv = document.getElementById('forecastHistory');
    
    // จำลองข้อมูลประวัติ (ในระบบจริงต้องดึงจาก API)
    const mockHistory = [
        { date: '12/02/2026 10:00', price: '35,200', trend: 'ขึ้น', accuracy: '85%' },
        { date: '12/02/2026 08:00', price: '35,150', trend: 'ลง', accuracy: '82%' },
        { date: '11/02/2026 18:00', price: '35,180', trend: 'ขึ้น', accuracy: '88%' },
        { date: '11/02/2026 14:00', price: '35,120', trend: 'คงที่', accuracy: '90%' }
    ];
    
    if (historyDiv) {
        if (mockHistory.length === 0) {
            historyDiv.innerHTML = '<p style="color: #666; font-size: 14px;">ยังไม่มีประวัติการพยากรณ์</p>';
        } else {
            let html = '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">';
            html += '<thead><tr style="background: #e8f4f8;">';
            html += '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">วันที่/เวลา</th>';
            html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">ราคาพยากรณ์</th>';
            html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">แนวโน้ม</th>';
            html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">ความแม่นยำ</th>';
            html += '</tr></thead><tbody>';
            
            mockHistory.forEach(item => {
                const trendColor = item.trend === 'ขึ้น' ? '#16A085' : (item.trend === 'ลง' ? '#e74c3c' : '#f39c12');
                html += '<tr style="border-bottom: 1px solid #eee;">';
                html += `<td style="padding: 8px;">${item.date}</td>`;
                html += `<td style="padding: 8px; text-align: center;">${item.price}</td>`;
                html += `<td style="padding: 8px; text-align: center; color: ${trendColor}; font-weight: bold;">${item.trend}</td>`;
                html += `<td style="padding: 8px; text-align: center;">${item.accuracy}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            historyDiv.innerHTML = html;
        }
    }
}

// ฟังก์ชันปิด modal
function closeProfileModal() {
    console.log('Close profile modal called');
    const modal = document.getElementById('profileModal');
    if (modal) {
        const overlay = modal.querySelector('#modalOverlay');
        if (overlay) {
            overlay.style.display = 'none';
            console.log('Modal display set to none');
        }
    }
}

// แทนที่ฟังก์ชันเดิม
window.showProfileModal = showProfileModal;
window.hideProfileModal = closeProfileModal;

// ผูก Event Listener ใหม่
document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile fix: DOM loaded');
    
    // สร้าง modal ทันที
    createProfileModal();
    
    // ผูกปุ่ม "ข้อมูลส่วนตัว"
    const profileLink = document.getElementById('profileLink');
    if (profileLink) {
        profileLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Profile link clicked (fixed version)');
            showProfileModal();
        });
        console.log('Profile link event attached');
    } else {
        console.warn('Profile link not found');
    }
});

console.log('Profile fix loaded successfully');
