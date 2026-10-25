import fs from 'fs';

export const VIDEO_ROOT = '/userdisk/Favorite/Video';
export const SETTINGS_PATH = VIDEO_ROOT + '/settings.json';
export const DEFAULT_PLAYER_APPID = '8001661999525016';

export const DEFAULT_SETTINGS = {
    playerAppid: DEFAULT_PLAYER_APPID
};

export async function ensureVideoRoot() {
    try {
        await fs.readdir(VIDEO_ROOT);
        return true;
    } catch (e) {
        try {
            await fs.mkdir(VIDEO_ROOT);
            return true;
        } catch (e2) {
            return false;
        }
    }
}

export function normalizeAppid(value) {
    const appid = String(value === undefined || value === null ? '' : value).trim();
    if (/^\d{8,20}$/.test(appid)) return appid;
    return DEFAULT_PLAYER_APPID;
}

export async function loadSettings() {
    await ensureVideoRoot();
    try {
        const raw = await fs.readFile(SETTINGS_PATH);
        const parsed = JSON.parse(raw);
        return {
            playerAppid: normalizeAppid(parsed && parsed.playerAppid)
        };
    } catch (e) {
        return { playerAppid: DEFAULT_PLAYER_APPID };
    }
}

export async function saveSettings(settings) {
    const ok = await ensureVideoRoot();
    if (!ok) throw new Error('无法创建视频目录');

    const data = {
        playerAppid: normalizeAppid(settings && settings.playerAppid)
    };
    await fs.writeFile(SETTINGS_PATH, JSON.stringify(data, null, 2));
    return data;
}
