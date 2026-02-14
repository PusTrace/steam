// === Импорт зависимостей ===
require('dotenv').config();          // ← важно
const SteamCommunity = require('steamcommunity');
const SteamTotp      = require('steam-totp');
const fs             = require('fs');

// === Пути к файлам ===
const COOKIES_FILE = './config/cookies.json';
const MA_FILE_PATH = './config/sda.json';

const community = new SteamCommunity();

function saveCookies(cookies) {
    try {
        fs.writeFileSync(COOKIES_FILE, JSON.stringify(cookies, null, 2), 'utf8');
    } catch (e) {
        console.error('⚠️ Ошибка сохранения куков:', e.message);
    }
}

async function loginAndSaveCookies() {
    const maFile = JSON.parse(fs.readFileSync(MA_FILE_PATH, 'utf8'));
    const twoFactorCode = SteamTotp.generateAuthCode(maFile.shared_secret);

    return new Promise((resolve, reject) => {
        community.login(
            {
                accountName: process.env.STEAM_ACCOUNT,
                password: process.env.STEAM_PASSWORD,
                twoFactorCode
            },
            (err, sessionID, cookies) => {
                if (err) return reject(err);
                const sessionIDClean = sessionID.split(';')[0];
                saveCookies(cookies);
                resolve({ cookies, sessionID: sessionIDClean });
            }
        );
    });
}

async function initializeSteam() {
    const cookiesData = await loginAndSaveCookies();
}

// === Запуск ===
initializeSteam().catch(err => {
    console.error('Fatal:', err);
});
