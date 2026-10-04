const express = require('express');
const path = require('path');
const crypto = require('crypto');
const session = require('express-session');
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;

const app = anExpressApp = express();
const PORT = process.env.PORT || 3000;

// إعدادات الجلسة (Session)
app.use(session({
    secret: process.env.SESSION_SECRET || 'GhostPay_Secure_Key_2026',
    resave: false,
    saveUninitialized: false
}));

app.use(passport.initialize());
app.use(passport.session());

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname)));

// قاعدة بيانات المستخدمين الوهمية (تستبدل لاحقاً بقاعدة بيانات حقيقية)
const usersDB = new Map();
const licensesDB = new Map();

// إعداد مصادقة جوجل (Google Strategy)
passport.use(new GoogleStrategy({
    clientID: process.env.GOOGLE_CLIENT_ID || 'ضع_هنا_Client_ID_الخاص_بـجوجل',
    clientSecret: process.env.GOOGLE_CLIENT_SECRET || 'ضع_هنا_Client_Secret_الخاص_بـجوجل',
    callbackURL: "https://ghostpay.work/auth/google/callback"
  },
  function(accessToken, refreshToken, profile, cb) {
    const email = profile.emails[0].value;
    const name = profile.displayName;
    
    // حفظ أو جلب المستخدم من قاعدة البيانات
    if (!usersDB.has(email)) {
        usersDB.set(email, {
            name: name,
            email: email,
            earnedBalance: 0.0000,
            purchaseBalance: 0.0000
        });
    }
    return cb(null, usersDB.get(email));
  }
));

passport.serializeUser((user, done) => { done(null, user.email); });
passport.deserializeUser((email, done) => { done(null, usersDB.get(email) || { email }); });

// --- المسارات (Routes) ---

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// بدء تسجيل الدخول بحساب جوجل
app.get('/auth/login', passport.authenticate('google', { scope: ['profile', 'email'] }));

// مسار العودة بعد نجاح المصادقة من جوجل
app.get('/auth/google/callback', 
    passport.authenticate('google', { failureRedirect: '/' }),
    (req, res) => {
        // نجح تسجيل الدخول، توجيه المستخدم للموقع مع حفظ جلسته
        res.redirect('/?loggedin=true');
    }
);

// مسار جلب بيانات المستخدم الحالي المعروضة في الواجهة
app.get('/api/v1/user/session', (req, res) => {
    if (req.isAuthenticated()) {
        res.json({ authenticated: true, user: req.user });
    } else {
        res.json({ authenticated: false });
    }
});

// مسار تسجيل الخروج
app.get('/auth/logout', (req, res) => {
    req.logout(() => {
        res.redirect('/');
    });
});

// مسار معالجة الشراء وإنشاء الترخيص
app.post('/api/v1/billing/checkout', (req, res) => {
    if (!req.isAuthenticated()) {
        return res.status(401).json({ status: "ERROR", message: "ACCESS DENIED: Please login via Google first." });
    }

    const { serviceType, price } = req.body;
    const userEmail = req.user.email;
    
    const validPrices = { 'WEB_SHIELD': 299, 'GAME_SHIELD': 499, 'HWID_GUARD': 399 };
    if (!validPrices[serviceType] || validPrices[serviceType] !== price) {
        return res.status(400).json({ status: "ERROR", message: "Invalid service tier or price mismatch." });
    }

    const licenseKey = 'GP_SHIELD_' + crypto.randomBytes(16).toString('hex').toUpperCase();
    licensesDB.set(licenseKey, { userEmail, serviceType, status: "ACTIVE", createdAt: new Date() });

    return res.json({
        status: "SUCCESS",
        message: `License generated successfully for ${userEmail}`,
        licenseKey: licenseKey,
        redirectUrl: `/?success=true&key=${licenseKey}`
    });
});

app.listen(PORT, () => {
    console.log(`GhostPay Secure Auth & Billing Server running on port ${PORT}`);
});
