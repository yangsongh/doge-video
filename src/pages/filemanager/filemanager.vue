<template>
    <div class="container">
        <div class="header">
            <text class="title">选择视频</text>
            <div class="actions">
                <text class="action" @click="up">上级</text>
                <text class="action" @click="refresh">刷新</text>
                <text class="action" @click="back">返回</text>
            </div>
        </div>

        <scroller class="path-scroller" scroll-direction="horizontal" show-scrollbar="false">
            <text class="path">{{ cwd }}</text>
        </scroller>

        <scroller class="list" show-scrollbar="false" over-scroll="30px" over-fling="30px">
            <text v-if="loading" class="hint">正在读取目录...</text>
            <text v-else-if="error" class="hint">读取失败：{{ error }}</text>
            <text v-else-if="items.length === 0" class="hint">这个目录里没有子目录或 MP4</text>

            <div v-else class="list-inner">
                <div v-if="canGoUp" class="card parent" @click="up">
                    <text class="name">..  返回上级</text>
                    <text class="badge">目录</text>
                </div>

                <div class="card" v-for="item in items" :key="item.path" @click="open(item)">
                    <div class="card-main">
                        <text class="name">{{ item.name }}</text>
                        <text class="meta">{{ item.meta }}</text>
                    </div>
                    <text class="badge" :class="item.type === 'file' ? 'badge-play' : ''">
                        {{ item.type === 'dir' ? '进入' : '播放' }}
                    </text>
                </div>
            </div>
        </scroller>

        <text class="footer">只建议选择已转换的 MP4；高分辨率原片可能黑屏或让播放器崩溃。</text>
    </div>
</template>

<script>
import FileBrowser from '../../utils/FileBrowser';
import { loadSettings, DEFAULT_PLAYER_APPID } from '../../utils/AppSettings';

export default {
    name: 'filemanager',
    data() {
        return {
            browser: null,
            cwd: '/userdisk',
            items: [],
            playerAppid: DEFAULT_PLAYER_APPID,
            canGoUp: false,
            loading: true,
            error: '',
            refreshing: false
        };
    },
    created() {
        const options = (this.$page && this.$page.options) || {};
        const start = options.path || '/userdisk';
        this.browser = new FileBrowser('/userdisk', start);
        this.cwd = this.browser.cwd;
        this.refresh();
    },
    methods: {
        onShow() {
            this.refresh();
        },

        async refresh() {
            if (!this.browser || this.refreshing) return;
            this.refreshing = true;
            this.loading = true;
            this.error = '';

            try {
                const settings = await loadSettings();
                this.playerAppid = settings.playerAppid;

                await this.browser.load();
                this.cwd = this.browser.cwd;
                this.items = this.browser.items;
                this.canGoUp = this.browser.canGoUp;
            } catch (e) {
                this.error = String(e);
                this.items = [];
            } finally {
                this.loading = false;
                this.refreshing = false;
            }
        },

        async open(item) {
            if (item.type === 'dir') {
                await this.browser.enter(item.path);
                this.cwd = this.browser.cwd;
                this.items = this.browser.items;
                this.canGoUp = this.browser.canGoUp;
                return;
            }

            const url = 'file://' + item.path;
            try {
                $falcon.navTo('falcon://' + (this.playerAppid || DEFAULT_PLAYER_APPID) + '/index', {
                    url: url,
                    castUrl: url,
                    title: item.name,
                    from: 'math-book'
                });
            } catch (e) {
                this.error = '调起播放器失败：' + e;
            }
        },

        async up() {
            if (!this.browser || !this.browser.canGoUp) {
                this.$page.finish();
                return;
            }
            await this.browser.up();
            this.cwd = this.browser.cwd;
            this.items = this.browser.items;
            this.canGoUp = this.browser.canGoUp;
        },

        back() {
            this.$page.finish();
        }
    }
};
</script>

<style lang="less" scoped>
.container {
    width: 100vw;
    height: 100vh;
    flex-direction: column;
    background-color: #1a1b1f;
    padding: 2vh 3vh 1vh 3vh;
}

.header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.8vh;
}

.title {
    color: #e3e3e3;
    font-size: 11vh;
    font-weight: bold;
}

.actions {
    flex-direction: row;
    align-items: center;
}

.action {
    color: #c2e7ff;
    font-size: 7vh;
    margin-left: 2vh;
    padding: 1vh 1.6vh;
    border-radius: 1.2vh;
    background-color: #004a77;
}

.action:active {
    opacity: 0.6;
}

.path-scroller {
    height: 8vh;
    margin-bottom: 0.6vh;
}

.path {
    color: #8e918f;
    font-size: 6vh;
}

.list {
    flex: 1;
}

.list-inner {
    padding-bottom: 1.5vh;
}

.card {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    background-color: #242529;
    border-radius: 2vh;
    padding: 1.8vh 2.4vh;
    margin-bottom: 1.4vh;
}

.card:active {
    opacity: 0.7;
}

.parent {
    background-color: #202226;
}

.card-main {
    flex: 1;
    flex-direction: column;
}

.name {
    color: #ffffff;
    font-size: 7.2vh;
}

.meta {
    color: #8e918f;
    font-size: 6.4vh;
    margin-top: 0.4vh;
}

.badge {
    color: #c2e7ff;
    font-size: 7vh;
    background-color: #0d2a3a;
    padding: 1vh 1.8vh;
    border-radius: 1.4vh;
    margin-left: 2vh;
}

.badge-play {
    color: #00ff88;
    background-color: #0f2a22;
}

.hint {
    color: #8e918f;
    font-size: 7.2vh;
    margin-top: 5vh;
    text-align: center;
}

.footer {
    color: #5f6368;
    font-size: 5.4vh;
    margin-top: 0.6vh;
}
</style>
