import http from 'k6/http';
import { check, sleep } from 'k6';

// Konfigurasi Load Testing
export let options = {
    // Lebih ringan untuk testing lokal
    stages: [
        { duration: '20s', target: 5 },   // Naik ke 5 VUs 
        { duration: '1m30s', target: 5 }, // Pertahankan beban puncak
        { duration: '10s', target: 0 },   
    ],
    thresholds: {
        // Waktu respons lebih tinggi karena ada I/O DB, target P95 < 1500ms
        'http_req_duration': ['p(95)<1500'], 
        // Toleransi error lebih tinggi untuk operasi DB
        'checks': ['rate>0.90'], 
    },
    ext: {
        loadimpact: {
            projectID: 3514930, 
            name: 'Warehouse Add Item Peak Load Test',
        },
    },
};

const BASE_URL = 'http://localhost:8080';
const USERNAME = 'superadmin'; // Asumsi user dengan role admin
const PASSWORD = 'admin123';

// Fungsi utama
export default function () {
    // --- Langkah 1: Login (Untuk mendapatkan sesi/cookie) ---
    const loginPayload = {
        username: USERNAME,
        password: PASSWORD,
    };
    
    const loginRes = http.post(`${BASE_URL}/login`, loginPayload, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    
    check(loginRes, {
        'Login Status 200/302': (r) => r.status === 200 || r.status === 302, 
        'Login tidak gagal': (r) => !r.body.includes('salah'),
    });

    // Hanya lanjutkan ke langkah 2 jika login berhasil
    if ((loginRes.status === 200 || loginRes.status === 302) && !loginRes.body.includes('salah')) {
        
        // --- Langkah 2: POST Data Item Baru ke /items/add ---
        
        // Buat data item unik per VU/iterasi untuk menghindari error duplikat
        const namaBarang = `Item Load Test ${__VU}-${__ITER}-${Date.now()}`;

        const addPayload = JSON.stringify({
            name: namaBarang,
            price: Math.floor(Math.random() * 100000) + 10000, // Harga acak: 10k-110k
            category_id: '', // Optional, bisa dikosongkan
            supplier_id: '', // Optional, bisa dikosongkan
        });

        // Endpoint yang benar adalah /items/add
        const addUrl = `${BASE_URL}/items/add`; 

        const res = http.post(addUrl, addPayload, {
            headers: {
                'Content-Type': 'application/json',
                // Cookie otomatis dibawa setelah login
            }
        });

        // 3. Verifikasi respons
        check(res, {
            'Status 200 (Item added)': (r) => r.status === 200,
            'Response contains success': (r) => r.body.includes('success') && r.body.includes('Item added'),
            'Mendapatkan item_id': (r) => r.body.includes('item_id'),
        });
    }

    // Istirahat lebih lama karena proses penulisan lebih berat
    sleep(__VU % 2 == 0 ? 2 : 3); 
}