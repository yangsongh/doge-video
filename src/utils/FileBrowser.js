import fs from 'fs';
import isVideo from './tools/isVideo';

export const BROWSE_ROOT = '/userdisk';
const MAX_ITEMS = 300;

function formatSize(size) {
    if (!size) return '未知大小';
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    if (size < 1024 * 1024 * 1024) return (size / (1024 * 1024)).toFixed(1) + ' MB';
    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function compare(a, b) {
    if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
    const an = a.name.match(/(\d+)/);
    const bn = b.name.match(/(\d+)/);
    const av = an ? parseInt(an[1], 10) : 0;
    const bv = bn ? parseInt(bn[1], 10) : 0;
    if (av !== bv) return av - bv;
    return a.name.localeCompare(b.name);
}

export default class FileBrowser {
    constructor(root = BROWSE_ROOT, start = null) {
        this.root = root;
        this.cwd = start && start.indexOf(root) === 0 ? start : root;
        this.items = [];
        this.loading = true;
        this.error = '';
        this.truncated = false;
    }

    get canGoUp() {
        return this.cwd !== this.root;
    }

    get parent() {
        if (!this.canGoUp) return null;
        const index = this.cwd.lastIndexOf('/');
        if (index <= this.root.length - 1) return this.root;
        return this.cwd.slice(0, index);
    }

    async load() {
        this.loading = true;
        this.error = '';
        this.truncated = false;
        this.items = [];

        let entries;
        try {
            entries = await fs.readdir(this.cwd, { withFileTypes: true });
        } catch (e) {
            this.error = String(e);
            this.loading = false;
            return this.items;
        }

        const result = [];
        for (let i = 0; i < entries.length; i++) {
            if (result.length >= MAX_ITEMS) {
                this.truncated = true;
                break;
            }

            const entry = entries[i];
            if (!entry || !entry.name || entry.name.charAt(0) === '.') continue;

            const full = this.cwd + '/' + entry.name;

            if (entry.isDirectory()) {
                result.push({
                    type: 'dir',
                    name: entry.name,
                    path: full,
                    meta: '目录'
                });
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
                type: 'file',
                name: entry.name,
                path: full,
                size,
                meta: formatSize(size)
            });
        }

        this.items = result.sort(compare);
        this.loading = false;
        return this.items;
    }

    async enter(path) {
        this.cwd = path;
        return this.load();
    }

    async up() {
        if (!this.canGoUp) return false;
        this.cwd = this.parent || this.root;
        await this.load();
        return true;
    }
}
