<template>
    <div class="container">
        <div class="header">
            <div class="title-group">
                <text class="title">Doge 视频</text>
                <text class="subtitle">本地视频 · 系统播放器</text>
            </div>
            <div class="actions">
                <text class="action" @click="openFileManager">选择文件</text>
                <text class="action" @click="openSettings">设置</text>
                <text class="action" @click="openHelp">说明</text>
                <text class="action" @click="refresh">刷新</text>
                <text class="action" @click="back">返回</text>
            </div>
        </div>

        <scroller class="list" show-scrollbar="false" over-scroll="30px" over-fling="30px">
            <text v-if="loading" class="hint">少女祈祷中...</text>

            <text v-else-if="missing" class="hint">
                没有找到视频目录。请把转换后的 MP4 放到 /userdisk/Favorite/Video，或点“选择文件”手动浏览
            </text>

            <text v-else-if="error" class="hint">读取失败：{{ error }}</text>

            <text v-else-if="videos.length === 0" class="hint">
                视频目录是空的。用转换工具转好后拷入 /userdisk/Favorite/Video，或点“选择文件”手动浏览。
            </text>

            <div v-else class="list-inner">
                <div class="card" v-for="video in videos" :key="video.path" @click="play(video)">
                    <div class="card-main">
                        <text class="name">{{ video.name }}</text>
                        <text class="meta">{{ video.sizeText }} · {{ video.dir }}</text>
                    </div>
                    <text class="play">播放</text>
                </div>
                <text v-if="truncated" class="more">只显示前 200 个视频</text>
            </div>
        </scroller>

        <text v-if="message" class="message">{{ message }}</text>
    </div>
</template>

<script>
import VideoLibrary from '../../utils/VideoLibrary';
import { loadSettings, DEFAULT_PLAYER_APPID } from '../../utils/AppSettings';

export default {
    name: 'index',
    data() {
        return {
            videos: [],
            playerAppid: DEFAULT_PLAYER_APPID,
            loading: true,
            missing: false,
            error: '',
            message: '',
            truncated: false,
            refreshing: false
        };
    },
    created() {
        this.refresh();
    },
    methods: {
        onShow() {
            this.refresh();
        },

        async refresh() {
            if (this.refreshing) return;
            this.refreshing = true;
            this.loading = true;
            this.message = '';

            try {
                const settings = await loadSettings();
                this.playerAppid = settings.playerAppid;

                const library = new VideoLibrary();
                const videos = await library.load();
                this.videos = videos || [];
                this.missing = library.missing;
                this.error = library.error || '';
                this.truncated = library.truncated;
            } catch (e) {
                this.error = String(e);
                this.videos = [];
            } finally {
                this.loading = false;
                this.refreshing = false;
            }
        },

        play(video) {
            this.message = '';
            const url = 'file://' + video.path;

            try {
                $falcon.navTo('falcon://' + (this.playerAppid || DEFAULT_PLAYER_APPID) + '/index', {
                    url: url,
                    castUrl: url,
                    title: video.name,
                    from: 'math-book'
                });
            } catch (e) {
                this.message = '调起播放器失败：' + e;
            }
        },

        openFileManager() {
            $falcon.navTo('filemanager');
        },

        openSettings() {
            $falcon.navTo('settings');
        },

        openHelp() {
            $falcon.navTo('help');
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
    padding: 2vh 3vh 1.5vh 3vh;
}

.header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5vh;
}

.title-group {
    flex-direction: row;
    align-items: flex-end;
}

.title {
    color: #e3e3e3;
    font-size: 11vh;
    font-weight: bold;
}

.subtitle {
    color: #8e918f;
    font-size: 7vh;
    margin-left: 2vh;
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

.list {
    flex: 1;
}

.list-inner {
    padding-bottom: 2vh;
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
    font-size: 7vh;
    margin-top: 0.5vh;
}

.play {
    color: #00ff88;
    font-size: 7vh;
    background-color: #0f2a22;
    padding: 1vh 2vh;
    border-radius: 1.4vh;
    margin-left: 2vh;
}

.hint {
    color: #8e918f;
    font-size: 7.2vh;
    margin-top: 5vh;
    text-align: center;
}

.more {
    color: #5f6368;
    font-size: 5.4vh;
    text-align: center;
    margin-top: 1vh;
}

.message {
    color: #ffb4ab;
    font-size: 7vh;
    margin-top: 1vh;
}
</style>
