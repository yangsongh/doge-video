import fs from 'fs';
import isVideo from './tools/isVideo';
import { VIDEO_ROOT } from './AppSettings';

export { VIDEO_ROOT };
const MAX_FILES = 200;
const MAX_DEPTH = 2;

function formatSize(size) {
    if (!size) return '未知大小';
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    if (size < 1024 * 1024 * 1024) return (size / (1024 * 1024)).toFixed(1) + ' MB';
    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function compareName(a, b) {
    const an = a.name.match(/(\d+)/);
    const bn = b.name.match(/(\d+)/);
    const av = an ? parseInt(an[1], 10) : 0;
    const bv = bn ? parseInt(bn[1], 10) : 0;
    if (av !== bv) return av - bv;
    return a.name.localeCompare(b.name);
}

export default class VideoLibrary {
    constructor(root = VIDEO_ROOT) {
        this.root = root;
        this.videos = [];
        this.loading = true;
        this.missing = false;
        this.error = null;
        this.truncated = false;
    }

    async ensureRoot() {
        try {
            await fs.readdir(this.root);
            return true;
        } catch (e) {
            try {
                await fs.mkdir(this.root);
                return true;
            } catch (e2) {
                return false;
            }
        }
    }

    async load() {
        this.loading = true;
        this.missing = false;
        this.error = null;
        this.truncated = false;
        this.videos = [];

        const ok = await this.ensureRoot();
        if (!ok) {
            this.missing = true;
            this.loading = false;
            return this.videos;
        }

        const result = [];
        try {
            await this.scan(this.root, 0, result);
            this.videos = result.sort(compareName);
            this.truncated = result.length >= MAX_FILES;
        } catch (e) {
            this.error = String(e);
        }

        this.loading = false;
        return this.videos;
    }

    async scan(dir, depth, result) {
        if (result.length >= MAX_FILES) return;

        let entries;
        try {
            entries = await fs.readdir(dir, { withFileTypes: true });
        } catch (e) {
            if (depth === 0) throw e;
            return;
        }

        for (let i = 0; i < entries.length; i++) {
            if (result.length >= MAX_FILES) return;

            const entry = entries[i];
            if (!entry || !entry.name || entry.name.charAt(0) === '.') continue;

            const full = dir + '/' + entry.name;

            if (entry.isDirectory()) {
                if (depth < MAX_DEPTH) {
                    await this.scan(full, depth + 1, result);
                }
                continue;
            }

            if (!isVideo(entry.name)) continue;

            let size = 0;
            try {
                const stat = await fs.stat(full);
                size = stat.size || 0;
            } catch (e) {
                size = 0;
            }

            result.push({
                name: entry.name,
                path: full,
                dir: dir === this.root ? '根目录' : dir.slice(this.root.length + 1),
                size,
                sizeText: formatSize(size)
            });
        }
    }
}
