<script setup>
import { Moon, Sun } from '@lucide/vue';
import { useDark } from '@vueuse/core';

const isDark = useDark();
</script>

<template>
    <el-switch v-model="isDark" class="theme-switch" :aria-label="$t('theme.toggle')">
        <template #active-action>
            <Moon class="dark-icon" :size="15" :stroke-width="1.75" aria-hidden="true" />
        </template>
        <template #inactive-action>
            <Sun class="light-icon" :size="15" :stroke-width="1.75" aria-hidden="true" />
        </template>
    </el-switch>
</template>

<style lang="scss" scoped>
.light-icon {
    color: #9a6700;
}

.dark-icon {
    color: #d7e2f3;
}

.theme-switch {
    --el-switch-off-color: rgba(245, 158, 11, 0.14);
    --el-switch-on-color: #273449;
}

:deep(.el-switch__core) {
    min-width: 44px;
    height: 26px;
    border-color: var(--border-color);
}

:deep(.el-switch__action) {
    width: 20px;
    height: 20px;
    color: var(--text-primary);
    background-color: var(--home-item-background-color);
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
}

:deep(.el-switch__input:focus-visible + .el-switch__core) {
    outline: 2px solid var(--active-color);
    outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
    :deep(.el-switch__core),
    :deep(.el-switch__action) {
        transition: none;
    }
}
</style>
