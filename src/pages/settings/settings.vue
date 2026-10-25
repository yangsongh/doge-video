<template>
    <div class="container">
        <div class="header">
            <text class="title">设置</text>
            <text class="back" @click="back">返回</text>
        </div>

        <div class="body">
            <div class="left">
                <text class="label">视频播放器 AppID</text>
                <text class="display">{{ appid || '—' }}</text>
                <text class="hint">点右侧数字键输入，8–20 位数字；默认 {{ defaultAppid }}。</text>

                <div class="actions">
                    <text class="save" @click="save">保存</text>
                    <text class="reset" @click="reset">默认</text>
                </div>
                <text class="status">{{ status }}</text>
            </div>

            <div class="keypad">
                <div class="key-row" v-for="(row, ri) in rows" :key="ri">
                    <text class="key" v-for="key in row" :key="key.label" @click="press(key)">{{ key.label }}</text>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { DEFAULT_PLAYER_APPID, loadSettings, saveSettings } from '../../utils/AppSettings';

export default {
    name: 'settings',
    data() {
        return {
            defaultAppid: DEFAULT_PLAYER_APPID,
            appid: DEFAULT_PLAYER_APPID,
            status: '',
            rows: [
                [
                    { label: '1', value: '1' }, { label: '2', value: '2' },
                    { label: '3', value: '3' }, { label: '4', value: '4' }
                ],
                [
                    { label: '5', value: '5' }, { label: '6', value: '6' },
                    { label: '7', value: '7' }, { label: '8', value: '8' }
                ],
                [
                    { label: '9', value: '9' }, { label: '0', value: '0' },
                    { label: '清空', action: 'clear' }, { label: '退格', action: 'back' }
                ]
            ]
        };
    },
    async created() {
        const settings = await loadSettings();
        this.appid = settings.playerAppid;
    },
    methods: {
        press(key) {
            if (key.action === 'clear') {
                this.appid = '';
                this.status = '';
                return;
            }
            if (key.action === 'back') {
                this.appid = String(this.appid || '').slice(0, -1);
                this.status = '';
                return;
            }
            if (String(this.appid || '').length >= 20) return;
            this.appid = String(this.appid || '') + key.value;
            this.status = '';
        },

        async save() {
            const value = String(this.appid || '').trim();
            if (!/^\d{8,20}$/.test(value)) {
                this.status = '请输入 8–20 位数字';
                return;
            }

            try {
                await saveSettings({ playerAppid: value });
                this.appid = value;
                this.status = '已保存：' + value;
            } catch (e) {
                this.status = '保存失败：' + e;
            }
        },

        reset() {
            this.appid = DEFAULT_PLAYER_APPID;
            this.status = '已填入默认值，点“保存”生效';
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
    padding: 1.5vh 2.5vh;
}

.header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1vh;
}

.title {
    color: #e3e3e3;
    font-size: 9vh;
    font-weight: bold;
}

.back {
    color: #c2e7ff;
    font-size: 5.5vh;
    padding: 0.8vh 1.8vh;
    border-radius: 1.2vh;
    background-color: #004a77;
}

.back:active {
    opacity: 0.6;
}

.body {
    flex: 1;
    flex-direction: row;
}

.left {
    flex: 1;
    flex-direction: column;
    padding-right: 2vh;
}

.label {
    color: #c2e7ff;
    font-size: 5vh;
}

.display {
    height: 10vh;
    line-height: 10vh;
    padding: 0 1.6vh;
    margin-top: 1vh;
    border-radius: 1.4vh;
    background-color: #242529;
    color: #00ff88;
    font-size: 5.2vh;
}

.hint {
    color: #8e918f;
    font-size: 3.6vh;
    line-height: 4.8vh;
    margin-top: 1vh;
}

.actions {
    flex-direction: row;
    align-items: center;
    margin-top: 1.6vh;
}

.save {
    color: #002111;
    font-size: 5.4vh;
    background-color: #00ff88;
    padding: 1vh 2.4vh;
    border-radius: 1.4vh;
    margin-right: 1.6vh;
}

.reset {
    color: #c2e7ff;
    font-size: 5.4vh;
    background-color: #004a77;
    padding: 1vh 2.4vh;
    border-radius: 1.4vh;
}

.save:active,
.reset:active {
    opacity: 0.6;
}

.status {
    color: #ffd6db;
    font-size: 4vh;
    margin-top: 1vh;
}

.keypad {
    flex: 1;
    flex-direction: column;
    justify-content: center;
}

.key-row {
    flex-direction: row;
    margin-bottom: 1.2vh;
}

.key {
    flex: 1;
    height: 11vh;
    line-height: 11vh;
    margin: 0 0.5vh;
    text-align: center;
    color: #ffffff;
    font-size: 5.6vh;
    background-color: #242529;
    border-radius: 1.4vh;
}

.key:active {
    background-color: #004a77;
}
</style>
