<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
import { Languages } from '@lucide/vue';
import { saveLanguage } from '@/api/system';
import { useAppStore } from '@/store/useAppStore';
const { locale, t } = useI18n();
import { LANGS } from '@/utils/langs';
const appStore = useAppStore();
const lang = ref(locale.value);
const changeTitle = () => {
    document.title = t('title')
}
const changeLang = (val) => {
    locale.value = val
    localStorage.setItem('lang', val)
    changeTitle()
    if (Cookies.get(appStore.cookieName)) {
        saveLanguage(val).catch(() => {})
    }
}
const langList = ref(Object.entries(LANGS).map(([key, val]) => ({
    label: val.label,
    value: key
})))
onMounted(() => {
    changeTitle()
})
</script>

<template>
    <div class="locale">
        <el-select ref="lang-select" v-model="lang" :options="langList" :aria-label="$t('engineScraping.language')"
            :suffix-icon="null" placeholder="Select" @change="changeLang">
            <template #label="{ label }">
                <div class="label-box">
                    <Languages :size="18" :stroke-width="1.75" aria-hidden="true" />
                    <span>{{ label }}</span>
                </div>
            </template>
        </el-select>
    </div>
</template>

<style lang="scss" scoped>
.locale {
    width: 90px;
    display: flex;
    align-items: center;

    :deep(.el-select__wrapper.is-focused) {
        box-shadow: 0 0 0 2px var(--active-color) inset;
    }

    :deep(.el-select__wrapper) {
        min-height: 36px;
        padding: 4px 8px;
        border-radius: 10px;
        box-shadow: none;
        background-color: transparent;
        transition: background-color 160ms ease, box-shadow 160ms ease;

        &:hover {
            background-color: var(--surface-hover);
        }

        .el-select__placeholder {
            width: 100%;

            .label-box {
                display: flex;
                align-items: center;
                justify-content: flex-start;
                color: var(--text-secondary);
                font-size: 13px;

                svg {
                    margin-right: 6px;
                    flex: 0 0 auto;
                }
            }
        }

        .el-select__suffix {
            display: none;
        }
    }
}

@media (max-width: 768px) {
    .locale {
        width: 38px;

        :deep(.el-select) {
            width: 38px !important;
        }

        :deep(.el-select__wrapper) {
            min-height: 36px;
            padding: 4px 9px;

            .el-select__placeholder {
                width: 20px;

                .label-box span {
                    display: none;
                }
            }
        }
    }
}

@media (prefers-reduced-motion: reduce) {
    .locale :deep(.el-select__wrapper) {
        transition: none;
    }
}
</style>
