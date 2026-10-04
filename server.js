const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// السماح بقراءة الملفات الثابتة مثل التصاميم والملفات الملحقة
app.use(express.static(path.join(__dirname)));

// مسار عرض الواجهة الرئيسية
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
    console.log(`GhostPay Shield Server is running on port ${PORT}`);
});
