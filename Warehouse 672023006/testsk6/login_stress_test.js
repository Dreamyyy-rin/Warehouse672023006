import http from 'k6/http';
import { check, sleep } from 'k6';

// Konfigurasi Load Testing
export let options = {
    // Tahap pengujian (Stages) untuk mencapai beban puncak 10 VU (lebih ringan untuk local testing)
    stages: [
        { duration: '30s', target: 10 },  // Naik ke 10 VUs dalam 30 detik
        { duration: '1m30s', target: 10 }, // Pertahankan 10 VUs selama 1.5 menit (Stress)
        { duration: '20s', target: 0 },   // Turun ke 0 VUs dalam 20 detik (Ramp Down)
    ],
    
    // Batasan Kinerja (Thresholds)
    thresholds: {
        // 95% dari waktu respons harus kurang dari 1000ms
        'http_req_duration': ['p(95)<1000'], 
        // Tingkat keberhasilan harus lebih dari 95%
        'checks': ['rate>0.95'], 
    },
    // Pengaturan HTTP
    ext: {
        loadimpact: {
            projectID: 3514930, // Ganti dengan ID proyek k6 Anda jika menggunakan k6 Cloud
            name: 'Warehouse Login Stress Test',
        },
    },
};

// URL Dasar Aplikasi Anda
const BASE_URL = 'http://localhost:8080'; 

export default function () {
    // Endpoint Login
    const loginUrl = `${BASE_URL}/login`;
    
    // Data login sebagai form data (bukan JSON)
    const payload = {
        username: 'superadmin', // Ganti jika kredensial default berbeda
        password: 'admin123', 
    };

    const params = {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    };

    // 1. Kirim permintaan POST untuk Login
    const res = http.post(loginUrl, payload, params);

    // 2. Verifikasi respons
    check(res, {
        'Status is 200/302 (Success)': (r) => r.status === 200 || r.status === 302,
        'Redirect ke Dashboard': (r) => r.headers['Location'] && r.headers['Location'].includes('/dashboard'), 
        'Tidak ada error message': (r) => !r.body.includes('salah'),
    });

    // Istirahat 2-3 detik (Think time) - lebih lama karena rate limiting
    sleep(__VU % 2 == 0 ? 2 : 3); 
}