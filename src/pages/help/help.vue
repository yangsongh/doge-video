<template>
    <div class="container">
        <div class="header">
            <text class="title">使用说明</text>
            <text class="back" @click="back">返回</text>
        </div>

        <scroller class="content" show-scrollbar="false" over-scroll="20px" over-fling="20px">
            <text class="line">1. 把转换好的 MP4 放到 /userdisk/Favorite/Video（支持子目录）。</text>
            <text class="line">2. 文件名建议只用英文、数字和下划线，避免中文和特殊符号。</text>
            <text class="line">3. 推荐规格：H.264 High、960×540、15fps、AAC 44.1kHz 立体声。</text>
            <text class="line">4. 在电脑上打开“Doge视频转码工具”，选择视频或文件夹，点“开始转换”。</text>
            <text class="line">5. 点击列表里的视频，会交给系统“视频播放器”播放；返回键回到本列表。</text>
            <text class="line">6. 如果播放器黑屏、卡死或重启，说明视频编码/分辨率不兼容；请用转换工具重新生成。</text>
            <text class="line">7. 本程序只做本地文件索引，不实现解码；播放器页面属于系统 App，系统 OTA 后可能变化。</text>
            <text class="line">8. 也可以在主界面点“选择文件”，手动浏览 /userdisk 下的目录和 MP4。</text>
            <text class="line">9. 主界面「设置」里可以修改视频播放器 AppID（默认 8001661999525016）。</text>
            <text class="line">10. 本程序自身不联网，也不上传视频；系统播放器在播放中断网会提示“网络未连接”。</text>
        </scroller>
    </div>
</template>

<script>
export default {
    name: 'help',
    methods: {
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

.title {
    color: #e3e3e3;
    font-size: 11vh;
    font-weight: bold;
}

.back {
    color: #c2e7ff;
    font-size: 7vh;
    padding: 1vh 2vh;
    border-radius: 1.2vh;
    background-color: #004a77;
}

.back:active {
    opacity: 0.6;
}

.content {
    flex: 1;
}

.line {
    color: #d6d6d6;
    font-size: 6.6vh;
    line-height: 9vh;
    margin-bottom: 1.2vh;
}
</style>
