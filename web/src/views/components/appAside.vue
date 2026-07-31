<script setup>
import { computed, markRaw } from 'vue'
import { ChartNoAxesCombined, Film, FolderOpen, PanelLeftClose, PanelLeftOpen, Settings } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const props = defineProps(['isCollapse', 'isMobile'])
const emit = defineEmits(['changeCollapse'])
const { t } = useI18n()
const route = useRoute()

const changeCollapse = function changeCollapse() {
    emit('changeCollapse', !props.isCollapse);
}

const menuList = [{
    index: '/home',
    icon: markRaw(ChartNoAxesCombined),
    title: computed(() => t('menu.home'))
}, {
    index: '/mediaScraping',
    icon: markRaw(Film),
    title: computed(() => t('menu.mediaScraping'))
}, {
    index: '/engine',
    icon: markRaw(FolderOpen),
    title: computed(() => t('menu.engine'))
}, {
    index: '/setting',
    icon: markRaw(Settings),
    title: computed(() => t('menu.setting'))
}]

const leftIndex = computed(() => route.meta?.leftIndex)
</script>

<template>
    <div class="aside-box">
        <div class="aside-main">
            <el-menu :default-active="leftIndex" :router="true" :collapse="isMobile ? false : isCollapse">
                <template v-for="menuItem in menuList" :key="menuItem.index">
                    <el-menu-item :index="menuItem.index" v-if="!menuItem.children">
                        <component :is="menuItem.icon" class="menu-icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
                        <template #title><span class="menu-title">{{ menuItem.title }}</span></template>
                    </el-menu-item>
                    <el-sub-menu :index="menuItem.index" v-else>
                        <template #title>
                            <component :is="menuItem.icon" class="menu-icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
                            <span>{{ menuItem.title }}</span>
                        </template>
                        <el-menu-item :index="subItem.index" :key="subItem.index" v-for="subItem in menuItem.children">
                            {{ subItem.title }}
                        </el-menu-item>
                    </el-sub-menu>
                </template>
            </el-menu>
        </div>
        <div class="aside-bottom">
            <button class="collapse-button" type="button" :aria-label="isCollapse ? t('menu.expand') : t('menu.collapse')"
                :title="isCollapse ? t('menu.expand') : t('menu.collapse')" @click="changeCollapse">
                <PanelLeftOpen v-if="isCollapse" :size="20" :stroke-width="1.75" aria-hidden="true" />
                <PanelLeftClose v-else :size="20" :stroke-width="1.75" aria-hidden="true" />
            </button>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.aside-box {
    border-right: 1px solid var(--border-color);
    background: var(--app-left-background-color);

    .aside-main {
        height: calc(100% - 56px);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 12px 10px;
        box-sizing: border-box;

        .el-menu {
            background-color: var(--app-left-background-color);
            border-right: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .el-menu--vertical {
            height: 100%;
        }

        :deep(.el-menu-item) {
            height: 46px;
            margin: 0;
            padding: 0 14px !important;
            border-radius: 12px;
            color: var(--text-secondary);
            gap: 12px;
            transition: background-color 160ms ease, color 160ms ease, box-shadow 160ms ease;
        }

        :deep(.el-menu-item:hover) {
            color: var(--text-primary);
            background-color: var(--surface-hover);
        }

        :deep(.el-menu-item.is-active) {
            color: var(--active-color);
            background-color: var(--brand-soft);
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--active-color) 18%, transparent);
        }

        :deep(.el-menu-item .menu-icon) {
            flex: 0 0 auto;
        }

        :deep(.el-menu--collapse .el-menu-item) {
            justify-content: center;
            padding: 0 !important;
        }
    }

    .aside-bottom {
        height: 56px;
        border-top: 1px solid var(--border-color);
        box-sizing: border-box;
        display: flex;
        align-items: center;
        padding: 0 12px;
    }

    .collapse-button {
        width: 36px;
        height: 36px;
        padding: 0;
        border: 0;
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--text-secondary);
        background: transparent;
        cursor: pointer;
        transition: background-color 160ms ease, color 160ms ease, transform 160ms ease;
    }

    .collapse-button:hover {
        color: var(--active-color);
        background-color: var(--brand-soft);
    }

    .collapse-button:active {
        transform: scale(0.94);
    }

    .collapse-button:focus-visible {
        outline: 2px solid var(--active-color);
        outline-offset: 2px;
    }
}

@media (max-width: 768px) {
    .aside-box {
        border-top: 1px solid var(--border-color);
        border-right: 0;
        box-shadow: 0 -12px 32px var(--app-header-shadow-color);

        .aside-main {
            height: 100%;
            overflow: hidden;
            padding: 0 6px;

            .el-menu {
                height: 100%;
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0;
            }

            :deep(.el-menu-item) {
                height: 63px;
                min-width: 0;
                padding: 6px 4px !important;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 3px;
                line-height: 1.15;
                border-radius: 10px;
            }

            :deep(.el-menu-item.is-active) {
                background-color: var(--brand-soft);
                box-shadow: inset 0 2px 0 var(--active-color);
            }

            :deep(.el-menu-item .menu-icon) {
                width: 20px;
                height: 20px;
            }

            :deep(.el-menu-item .menu-title) {
                width: 100%;
                min-height: 24px;
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                line-height: 12px;
                text-align: center;
                white-space: normal;
                overflow-wrap: anywhere;
            }
        }

        .aside-bottom {
            display: none;
        }
    }
}

@media (prefers-reduced-motion: reduce) {
    .aside-box {
        .aside-main :deep(.el-menu-item),
        .collapse-button {
            transition: none;
        }

        .collapse-button:active {
            transform: none;
        }
    }
}
</style>
