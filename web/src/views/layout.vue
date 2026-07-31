<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';
import Cookies from 'js-cookie';
import { useMediaQuery } from '@vueuse/core';
import { useRoute } from 'vue-router';
import appHeader from '@/views/components/appHeader.vue';
import appLeft from './components/appAside.vue';
import { saveLanguage } from '@/api/system';
import { useAppStore } from '@/store/useAppStore';
let isCollapse = ref(false);
const isMobile = useMediaQuery('(max-width: 768px)');
const appStore = useAppStore();
const route = useRoute();
const appMainRef = ref();
const changeCollapse = function changeCollapse(val) {
    isCollapse.value = val;
}
watch(() => route.fullPath, async () => {
    await nextTick();
    if (appMainRef.value) {
        appMainRef.value.scrollTop = 0;
        appMainRef.value.scrollLeft = 0;
    }
});
onMounted(() => {
    if (Cookies.get(appStore.cookieName)) {
        saveLanguage(localStorage.getItem('lang') || 'zh-CN').catch(() => {})
    }
})
</script>

<template>
    <div ref="appMainRef" class="app-main">
        <appHeader class="app-header" />
        <appLeft :isCollapse="isMobile ? false : isCollapse" :isMobile="isMobile" @changeCollapse="changeCollapse"
            :class="`app-left${isCollapse ? ' left-collapse' : ''}`" />
        <div v-loading="appStore.loading" :class="`app-content${isCollapse ? ' content-collapse' : ''}`">
            <router-view />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.app-main {
    width: 100%;
    height: 100vh;
    height: 100dvh;
    box-sizing: border-box;
    position: relative;
    overflow-y: auto;

    .app-header {
        position: fixed;
        z-index: 2;
        top: 0;
        left: 0;
        right: 0;
        height: 58px;
        width: 100%;
        box-sizing: border-box;
        border-bottom: 1px solid var(--border-color);
        box-shadow: 0 10px 30px var(--app-header-shadow-color);

        background: var(--app-header-background-color);
        backdrop-filter: blur(18px) saturate(150%);
        -webkit-backdrop-filter: blur(18px) saturate(150%);
    }

    .app-left {
        position: fixed;
        left: 0;
        top: 58px;
        bottom: 0;
        transition: width 220ms cubic-bezier(.2, .8, .2, 1);
        width: 212px;
        box-sizing: border-box;
        background: var(--app-left-background-color);
    }

    .left-collapse {
        width: 68px;
    }

    .app-content {
        width: 100%;
        height: 100%;
        padding-left: 212px;
        padding-top: 58px;
        transition: padding-left 220ms cubic-bezier(.2, .8, .2, 1);
        box-sizing: border-box;
    }

    .content-collapse {
        padding-left: 68px;
    }


}

@media (prefers-reduced-motion: reduce) {
    .app-main {
        .app-left,
        .app-content {
            transition: none;
        }
    }
}

@media (max-width: 768px) {
    .app-main {
        overflow-x: hidden;
        overflow-y: auto;
        overscroll-behavior-y: contain;
        -webkit-overflow-scrolling: touch;

        .app-header {
            z-index: 20;
            height: 54px;
        }

        .app-left,
        .left-collapse {
            z-index: 20;
            top: auto;
            right: 0;
            bottom: 0;
            width: 100%;
            height: calc(64px + env(safe-area-inset-bottom));
            padding-bottom: env(safe-area-inset-bottom);
        }

        .app-content,
        .content-collapse {
            height: auto;
            min-height: 100vh;
            min-height: 100dvh;
            padding-left: 0;
            padding-top: 54px;
            padding-bottom: calc(64px + env(safe-area-inset-bottom));
        }
    }
}
</style>
