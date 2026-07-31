<template>
    <div class="logo">
        <img class="logo-mark" src="/logo.svg" alt="" width="34" height="34" />
        <div class="logo-title">{{ $t('title') }}</div>
    </div>
</template>

<style lang="scss" scoped>
.logo {
    display: flex;
    align-items: center;
    min-width: 0;

    .logo-mark {
        width: 34px;
        height: 34px;
        display: block;
    }

    .logo-title {
        margin-left: 10px;
        color: var(--text-primary);
        font-size: 21px;
        font-weight: 760;
        line-height: 1;
        letter-spacing: 0;
        white-space: nowrap;
    }
}
</style>
