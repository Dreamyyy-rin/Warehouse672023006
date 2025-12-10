import http from 'k6/http';
import { check, sleep } from 'k6';

// Konfigurasi Load Testing: Beban Sedang untuk Read Operations
export let options = {
    // Stages: Beban lebih ringan untuk local testing
    stages: [
        { duration: '30s', target: 15 },  // Naik ke 15 VUs 
        { duration: '1m', target: 15 },   // Pertahankan 15 VUs
        { duration: '15s', target: 0 },   
    ],
    thresholds: {
        // Target P95 yang realistis untuk operasi baca di local environment
        'http_req_duration': ['p(95)<800'], 
        'checks': ['rate>0.97'], // Tingkat keberhasilan 97%
    },
    ext: {
        loadimpact: {
            projectID: 3514930, 
            name: 'Warehouse Read Item List Load Test',
        },
    },
};

const BASE_URL = 'http://localhost:8080';
const USERNAME = 'superadmin';
const PASSWORD = 'admin123';

export default function () {
    // --- Langkah 1: Login (Pastikan sesi tetap aktif) ---
    const loginData = { username: USERNAME, password: PASSWORD };
    
    const loginRes = http.post(`${BASE_URL}/login`, loginData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }); 
    
    check(loginRes, {
        'Login berhasil': (r) => (r.status === 200 || r.status === 302) && !r.body.includes('salah'),
    });
    
    // Hanya lanjutkan jika login berhasil
    if ((loginRes.status === 200 || loginRes.status === 302) && !loginRes.body.includes('salah')) {
        
        // --- Langkah 2: GET Item List (Operasi Baca) ---
        const listUrl = `${BASE_URL}/items`; 

        const res = http.get(listUrl);

        // 3. Verifikasi respons
        check(res, {
            'Status 200 (Read Success)': (r) => r.status === 200,
            'Contains items page': (r) => r.body.includes('items.html') || r.body.includes('Items') || r.body.includes('Barang'),
            'Not redirected to login': (r) => !r.url.includes('/login'),
        });
    }

    // Istirahat lebih lama untuk menghindari rate limit
    sleep(__VU % 3 == 0 ? 2 : 1); 
}