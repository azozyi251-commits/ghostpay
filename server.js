const express = require('express');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname)));

// قاعدة بيانات وهمية في الذاكرة (تستبدل لاحقاً بقاعدة بيانات حقيقية مثل PostgreSQL أو MySQL)
const usersDB = new Map(); // تخزين حسابات المستخدمين والمحافظ
const licensesDB = new Map(); // تخزين التراخيص المفعلة

// مسار رئيسي لعرض الواجهة
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// 1. مسار تسجيل الدخول التجريبي المباشر (لربط حساب المستخدم)
app.get('/auth/login', (req, res) => {
    // تجربة تسجيل دخول افتراضية لمستخدم النظام
    const demoEmail = "admin@ghostpay.work";
    usersDB.set(demoEmail, {
        email: demoEmail,
        earnedBalance: 0.0000,
        purchaseBalance: 1000.0000 // رصيد تجريبي للشراء
    });
    
    // إعادة توجيه المستخدم للرئيسية بعد تسجيل الدخول
    res.redirect('/?user=' + encodeURIComponent(demoEmail));
});

// 2. مسار جلب بيانات الحساب والمحفظة
app.get('/api/v1/user/profile', (req, res) => {
    const userEmail = req.query.email || "admin@ghostpay.work";
    const user = usersDB.get(userEmail) || { earnedBalance: 0, purchaseBalance: 0 };
    res.json({ status: "SUCCESS", user });
});

// 3. مسار معالجة التحويل والأسعار وبدء الشراء (Checkout Gateway)
app.post('/api/v1/billing/checkout', (req, res) => {
    const { serviceType, price } = req.body;
    
    // التحقق من الباقات وأسعارها المعتمدة في المنظومة
    const validPrices = { 'WEB_SHIELD': 299, 'GAME_SHIELD': 499, 'HWID_GUARD': 399 };
    if (!validPrices[serviceType] || validPrices[serviceType] !== price) {
        return res.status(400).json({ status: "ERROR", message: "Invalid service tier or price mismatch." });
    }

    // محاكاة الخصم من رصيد الشراء أو التوجيه لبوابة دفع خارجية (مثل Stripe/Moyasar)
    const licenseKey = 'GP_SHIELD_' + crypto.randomBytes(16).toString('hex').toUpperCase();
    
    // حفظ الترخيص المفعل
    licensesDB.set(licenseKey, {
        serviceType,
        createdAt: new Date(),
        status: "ACTIVE"
    });

    // إرجاع تفاصيل النجاح والمفتاح المولد
    return res.json({
        status: "SUCCESS",
        message: `Successfully subscribed to ${serviceType}!`,
        licenseKey: licenseKey,
        redirectUrl: `/?success=true&key=${licenseKey}`
    });
});

app.listen(PORT, () => {
    console.log(`GhostPay Billing & Security Engine running on port ${PORT}`);
});
