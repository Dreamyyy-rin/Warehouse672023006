import http from 'k6/http';
import { check, sleep } from 'k6';

// Konfigurasi Load Testing: Endurance Test - Beban Rendah selama 10 menit (lebih praktis untuk local testing)
export let options = {
    // Stages: Pertahankan 3 VUs selama 10 menit (atau ubah ke 1h jika ingin test penuh)
    stages: [
        { duration: '1m', target: 3 },    // Ramp up ke 3 VUs
        { duration: '10m', target: 3 },   // Pertahankan 3 VUs selama 10 menit (ubah ke 1h jika perlu)
        { duration: '30s', target: 0 },   // Ramp down
    ],
    // Thresholds: Harus stabil sepanjang waktu
    thresholds: {
        'http_req_duration': ['p(95)<1000'], // Lebih realistis untuk endurance test
        'checks': ['rate>0.95'], // Toleransi lebih tinggi karena test lama
    },
    ext: {
        loadimpact: {
            projectID: 3514930, 
            name: 'Warehouse Endurance Test (10 Minutes)',
        },
    },
};

const BASE_URL = 'http://localhost:8080';
const USERNAME = 'superadmin';
const PASSWORD = 'admin123';

export default function () {
    // Login hanya sekali per VU (di iterasi pertama) untuk menghindari rate limiting
    if (__ITER === 0) {
        const loginData = { username: USERNAME, password: PASSWORD };
        const loginRes = http.post(`${BASE_URL}/login`, loginData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        
        check(loginRes, {
            'Login berhasil': (r) => (r.status === 200 || r.status === 302) && !r.body.includes('salah'),
        });
        
        sleep(2); // Pause setelah login
    }
    
    // --- Operasi yang dilakukan berulang kali (simulasi user activity) ---
    
    // 1. GET Item List (Read operation)
    const itemsRes = http.get(`${BASE_URL}/items`);
    check(itemsRes, {
        'Items page loaded': (r) => r.status === 200,
        'Not redirected to login': (r) => !r.url.includes('/login'),
    });
    sleep(2 + Math.random() * 2); // Sleep 2-4 detik (simulasi user baca data)
    
    // 2. GET Dashboard (Read operation)
    const dashboardRes = http.get(`${BASE_URL}/dashboard`);
    check(dashboardRes, {
        'Dashboard loaded': (r) => r.status === 200,
    });
    sleep(2 + Math.random() * 2); // Sleep 2-4 detik
    
    // 3. GET API Items (Read operation - lebih ringan, JSON response)
    const apiRes = http.get(`${BASE_URL}/api/items`);
    check(apiRes, {
        'API items success': (r) => r.status === 200,
        'Valid JSON response': (r) => {
            try {
                JSON.parse(r.body);
                return true;
            } catch {
                return false;
            }
        },
    });
    sleep(3 + Math.random() * 3); // Sleep 3-6 detik (total cycle ~10-16 detik per iterasi)
}