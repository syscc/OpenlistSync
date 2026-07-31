<script setup>
import { useRouter } from 'vue-router';
import lightDark from './lightDark.vue';
import locale from './locale.vue';
import logo from './logo.vue';
import user from './user.vue';

const router = useRouter();
</script>

<template>
    <header class="header-box">
        <button class="brand-button" type="button" :aria-label="$t('title')" @click="router.push('/')">
            <logo />
        </button>
        <div class="header-right">
            <locale class="header-item" />
            <lightDark class="header-item" />
            <user class="header-item" />
        </div>
    </header>
</template>

<style lang="scss" scoped>
.header-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px;

    .brand-button {
        min-width: 0;
        padding: 4px 6px;
        border: 0;
        border-radius: 12px;
        color: inherit;
        background: transparent;
        cursor: pointer;
        transition: background-color 160ms ease, transform 160ms ease;
    }

    .brand-button:hover {
        background-color: var(--surface-hover);
    }

    .brand-button:active {
        transform: scale(0.98);
    }

    .brand-button:focus-visible {
        outline: 2px solid var(--active-color);
        outline-offset: 2px;
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .header-item {
        flex: 0 0 auto;
    }
}

@media (max-width: 768px) {
    .header-box {
        padding: 0 8px 0 10px;

        .header-right {
            min-width: 0;
            gap: 4px;
        }
    }
}

@media (max-width: 420px) {
    .header-box {
        :deep(.logo-title) {
            margin-left: 8px;
            font-size: 20px;
        }
    }
}

@media (prefers-reduced-motion: reduce) {
    .header-box .brand-button {
        transition: none;
    }

    .header-box .brand-button:active {
        transform: none;
    }
}
</style>
