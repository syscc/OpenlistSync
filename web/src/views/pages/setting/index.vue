<script setup>
import { computed, markRaw, ref, watch } from "vue";
import { editPwd } from "@/api/user";
import { parseTime } from "@/utils/utils";
import { useAppStore } from "@/store/useAppStore";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import GlobalExcludeSettings from "@/views/pages/globalExclude/index.vue";
import NotificationSettings from "@/views/pages/notify/index.vue";
import ProxyServerSettings from "@/views/pages/setting/ProxyServerSettings.vue";
import {
  BellRing,
  Bug,
  CalendarDays,
  CircleUserRound,
  Code2,
  ExternalLink,
  Info,
  KeyRound,
  Network,
  Save,
  ShieldBan,
  ShieldCheck,
} from "@lucide/vue";

const appStore = useAppStore();
const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const settingsTabs = new Set(["account", "proxyServer", "globalExclude", "notifications", "about"]);
const normalizeSettingsTab = (tab) => (tab === "tmdbProxy" ? "proxyServer" : tab);
const settingNavItems = computed(() => [
  { name: "account", label: t("setting.accountSecurity"), icon: markRaw(CircleUserRound) },
  { name: "proxyServer", label: t("setting.proxyServer"), icon: markRaw(Network) },
  { name: "globalExclude", label: t("setting.globalExclude"), icon: markRaw(ShieldBan) },
  { name: "notifications", label: t("setting.notifications"), icon: markRaw(BellRing) },
  { name: "about", label: t("setting.about"), icon: markRaw(Info) },
]);
const activeTab = computed({
  get() {
    const tab = normalizeSettingsTab(route.query.tab);
    return settingsTabs.has(tab) ? tab : "account";
  },
  set(tab) {
    router.replace({
      path: "/setting",
      query: tab === "account" ? {} : { tab },
    });
  },
});
watch(
  () => route.query.tab,
  (tab) => {
    if (tab === "tmdbProxy") {
      router.replace({ path: "/setting", query: { tab: "proxyServer" } });
    } else if (tab === "account" || (tab !== undefined && !settingsTabs.has(tab))) {
      router.replace({ path: "/setting" });
    }
  },
  { immediate: true },
);
const versionText = computed(() =>
  t("setting.version").replace("__version_placeholder__", import.meta.env.VITE_APP_VERSION),
);
const resetFormRef = ref();
const resetForm = ref({
  oldPasswd: "",
  passwd: "",
  passwd2: "",
});
const loading = ref(false);

const validatePass2 = (rule, value, callback) => {
  if (value == "" || value == null) {
    callback(new Error(t("user.newPasswd2Rule")));
  } else if (value !== resetForm.value.passwd) {
    callback(new Error(t("user.newPasswd2Error")));
  } else {
    callback();
  }
};

const rules = computed(() => ({
  oldPasswd: [
    {
      required: true,
      message: t("user.oldPasswdRule"),
      trigger: "blur",
    },
  ],
  passwd: [
    {
      required: true,
      message: t("user.newPasswdRule"),
      trigger: "blur",
    },
  ],
  passwd2: [
    {
      validator: validatePass2,
      trigger: "blur",
    },
  ],
}));

const resetPasswd = () => {
  resetFormRef.value.validate((valid) => {
    if (!valid) return;
    loading.value = true;
    editPwd(resetForm.value)
      .then((res) => {
        ElMessage({
          message: res.msg || t("user.success"),
          type: "success",
        });
        resetFormRef.value.resetFields();
      })
      .finally(() => {
        loading.value = false;
      });
  });
};
</script>

<template>
  <div class="setting">
    <header class="setting-heading">
      <div>
        <div class="heading-kicker">CONTROL CENTER</div>
        <h1>{{ $t("setting.title") }}</h1>
        <p>{{ $t("setting.subtitle") }}</p>
      </div>
      <div class="heading-mark" aria-hidden="true"><ShieldCheck :size="26" /></div>
    </header>
    <el-select v-model="activeTab" class="setting-tab-select" :aria-label="$t('setting.title')">
      <el-option v-for="item in settingNavItems" :key="item.name" :label="item.label" :value="item.name" />
    </el-select>
    <div class="setting-workspace">
      <nav class="setting-nav" :aria-label="$t('setting.title')">
        <button
          v-for="item in settingNavItems"
          :key="item.name"
          type="button"
          class="setting-nav-item"
          :class="{ active: activeTab === item.name }"
          :aria-current="activeTab === item.name ? 'page' : undefined"
          @click="activeTab = item.name"
        >
          <component :is="item.icon" :size="18" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <main class="setting-content">
        <section v-if="activeTab === 'account'" class="account-layout">
          <article class="profile-card" v-if="appStore.user">
            <div class="profile-avatar"><CircleUserRound :size="30" aria-hidden="true" /></div>
            <div class="profile-copy">
              <span>{{ $t("setting.accountSecurity") }}</span>
              <strong>{{ appStore.user.userName }}</strong>
              <p>{{ $t("setting.accountDescription") }}</p>
            </div>
            <dl>
              <div>
                <dt><CircleUserRound :size="15" aria-hidden="true" />{{ $t("setting.username") }}</dt>
                <dd>{{ appStore.user.userName }}</dd>
              </div>
              <div>
                <dt><CalendarDays :size="15" aria-hidden="true" />{{ $t("common.createdAt") }}</dt>
                <dd>{{ parseTime(appStore.user.createTime) }}</dd>
              </div>
            </dl>
          </article>

          <article class="security-card" v-if="appStore.user">
            <div class="section-heading">
              <div class="section-icon"><KeyRound :size="19" aria-hidden="true" /></div>
              <div>
                <h2>{{ $t("setting.securityTitle") }}</h2>
                <p>{{ $t("setting.securityDescription") }}</p>
              </div>
            </div>
            <el-form :model="resetForm" :rules="rules" ref="resetFormRef" label-position="top">
              <el-form-item prop="oldPasswd" :label="$t('user.oldPasswdLabel')">
                <el-input :placeholder="$t('user.oldPasswd')" show-password v-model="resetForm.oldPasswd" autocomplete="current-password" />
              </el-form-item>
              <el-form-item prop="passwd" :label="$t('user.newPasswdLabel')">
                <el-input :placeholder="$t('user.newPasswd')" show-password v-model="resetForm.passwd" autocomplete="new-password" />
              </el-form-item>
              <el-form-item prop="passwd2" :label="$t('user.newPasswd2Label')">
                <el-input :placeholder="$t('user.newPasswd2')" show-password v-model="resetForm.passwd2" autocomplete="new-password" @keyup.enter="resetPasswd" />
              </el-form-item>
            </el-form>
            <el-button :icon="Save" type="primary" :loading="loading" @click="resetPasswd">{{ $t("header.setPwd") }}</el-button>
          </article>
        </section>

        <ProxyServerSettings v-else-if="activeTab === 'proxyServer'" />
        <GlobalExcludeSettings v-else-if="activeTab === 'globalExclude'" />
        <NotificationSettings v-else-if="activeTab === 'notifications'" />

        <section v-else class="about-card">
          <div class="about-orbit" aria-hidden="true">
            <img src="/logo.svg" alt="" />
          </div>
          <div class="about-copy">
            <div class="heading-kicker">OPEN SOURCE MEDIA OPERATIONS</div>
            <h2>OpenListSync</h2>
            <p>{{ $t("setting.aboutDescription") }}</p>
            <div class="about-version">{{ versionText }}</div>
            <div class="about-links">
              <a href="https://github.com/syscc/OpenlistSync" target="_blank" rel="noopener noreferrer">
                <Code2 :size="18" /><span>{{ $t("setting.projectSource") }}</span><ExternalLink :size="15" />
              </a>
              <a href="https://github.com/syscc/OpenlistSync/issues" target="_blank" rel="noopener noreferrer">
                <Bug :size="18" /><span>{{ $t("setting.issueTracker") }}</span><ExternalLink :size="15" />
              </a>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.setting {
  padding: clamp(20px, 3vw, 36px);
  width: 100%;
  min-height: 100%;
  box-sizing: border-box;

  .setting-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 28px;

    h1 {
      margin: 3px 0 5px;
      color: var(--text-primary);
      font-size: 36px;
      font-weight: 780;
      line-height: 1.1;
      letter-spacing: 0;
    }

    p {
      margin: 0;
      color: var(--text-muted);
    }
  }

  .heading-kicker {
    color: var(--active-color);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .heading-mark {
    width: 48px;
    height: 48px;
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    color: var(--active-color);
    border: 1px solid color-mix(in srgb, var(--active-color) 25%, var(--border-color));
    border-radius: var(--radius-lg);
    background: var(--brand-soft);
  }

  .setting-tab-select {
    display: none;
  }

  .setting-workspace {
    display: block;
  }

  .setting-nav {
    position: sticky;
    z-index: 4;
    top: 70px;
    display: flex;
    align-items: center;
    gap: 28px;
    margin-bottom: 24px;
    padding: 0 2px;
    overflow-x: auto;
    border-bottom: 1px solid var(--border-color);
    background: color-mix(in srgb, var(--background-color) 94%, transparent);
    backdrop-filter: blur(14px);
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .setting-nav-item {
    position: relative;
    width: auto;
    min-height: 48px;
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 4px;
    border: 0;
    border-radius: 0;
    color: var(--text-secondary);
    background: transparent;
    cursor: pointer;
    transition: color var(--motion-fast) var(--ease-standard),
      transform var(--motion-fast) var(--ease-standard);

    &::after {
      content: "";
      position: absolute;
      right: 0;
      bottom: -1px;
      left: 0;
      height: 2px;
      background: var(--active-color);
      transform: scaleX(0);
      transform-origin: center;
      transition: transform var(--motion-fast) var(--ease-standard);
    }

    svg {
      flex: 0 0 auto;
      stroke-width: 1.75;
    }

    &:hover {
      color: var(--text-primary);
    }

    &.active {
      color: var(--active-color);
      font-weight: 700;

      &::after {
        transform: scaleX(1);
      }
    }
  }

  .setting-content {
    min-width: 0;
  }

  .account-layout {
    display: grid;
    grid-template-columns: minmax(260px, 0.7fr) minmax(360px, 1.3fr);
    gap: 18px;
  }

  .profile-card,
  .security-card,
  .about-card {
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    background: var(--surface-panel);
    box-shadow: var(--shadow-xs);
  }

  .profile-card {
    padding: 24px;

    .profile-avatar {
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      margin-bottom: 24px;
      color: var(--active-color);
      border-radius: var(--radius-lg);
      background: var(--brand-soft);
    }

    .profile-copy {
      span {
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      strong {
        display: block;
        margin-top: 4px;
        font-size: 24px;
        letter-spacing: 0;
      }

      p {
        margin: 8px 0 22px;
        color: var(--text-muted);
        line-height: 1.65;
      }
    }

    dl {
      margin: 0;
      padding-top: 10px;
      border-top: 1px solid var(--border-color);

      > div {
        padding: 12px 0;
      }

      dt {
        display: flex;
        align-items: center;
        gap: 7px;
        color: var(--text-muted);
        font-size: 12px;
      }

      dd {
        margin: 5px 0 0 22px;
        color: var(--text-primary);
        font-weight: 650;
        overflow-wrap: anywhere;
      }
    }
  }

  .security-card {
    padding: 24px;

    .section-heading {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 24px;

      .section-icon {
        width: 38px;
        height: 38px;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        color: var(--active-color);
        border-radius: var(--radius-md);
        background: var(--brand-soft);
      }

      h2 {
        margin: 0;
        font-size: 18px;
      }

      p {
        margin: 4px 0 0;
        color: var(--text-muted);
        font-size: 13px;
      }
    }

    :deep(.el-form-item__label) {
      padding-bottom: 6px;
      color: var(--text-secondary);
      font-weight: 650;
    }

    :deep(.el-input__wrapper) {
      min-height: 42px;
    }

    .el-button {
      min-width: 150px;
    }
  }

  .about-card {
    min-height: 360px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: clamp(36px, 7vw, 84px);
    padding: clamp(32px, 6vw, 70px);
    overflow: hidden;

    .about-orbit {
      position: relative;
      width: 180px;
      height: 180px;
      flex: 0 0 auto;
      display: grid;
      place-items: center;
      border: 1px solid color-mix(in srgb, var(--active-color) 22%, transparent);
      border-radius: 50%;
      background: var(--brand-soft);

      &::before,
      &::after {
        content: "";
        position: absolute;
        border: 1px solid color-mix(in srgb, var(--active-color) 16%, transparent);
        border-radius: 50%;
      }

      &::before { inset: 22px -22px; }
      &::after { inset: -22px 22px; }

      img {
        width: 72px;
        height: 72px;
      }
    }

    .about-copy {
      max-width: 500px;

      h2 {
        margin: 7px 0 12px;
        font-size: 48px;
        line-height: 1;
        letter-spacing: 0;
      }

      > p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 16px;
        line-height: 1.7;
      }
    }

    .about-version {
      display: inline-flex;
      margin-top: 22px;
      padding: 6px 10px;
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-pill);
      background: var(--surface-inset);
      font-family: var(--font-mono);
      font-size: 12px;
    }

    .about-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 24px;

      a {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 12px;
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        background: var(--surface-panel);
        text-decoration: none;
        transition: border-color var(--motion-fast), transform var(--motion-fast), box-shadow var(--motion-fast);

        &:hover {
          border-color: var(--active-color);
          transform: translateY(-1px);
          box-shadow: var(--shadow-sm);
        }
      }
    }
  }
}

@media (max-width: 1100px) {
  .setting {
    .account-layout {
      grid-template-columns: 1fr;
    }

    .about-card {
      flex-direction: column;
      align-items: flex-start;
      gap: 32px;

      .about-copy {
        max-width: 100%;
      }
    }
  }
}

@media (max-width: 1000px) {
  .setting {
    .setting-tab-select {
      display: block;
      width: 100%;
      margin-bottom: 14px;
    }

    .setting-workspace {
      display: block;
    }

    .setting-nav {
      display: none;
    }
  }
}

@media (max-width: 768px) {
  .setting {
    min-height: 100%;
    padding: 18px 12px 28px;

    .setting-heading {
      margin-bottom: 18px;

      h1 {
        font-size: 28px;
      }

      .heading-mark {
        width: 42px;
        height: 42px;
      }
    }

    .setting-tab-select {
      display: block;
      width: 100%;
      margin-bottom: 14px;
    }

    .setting-workspace {
      display: block;
    }

    .setting-nav {
      display: none;
    }

    .profile-card,
    .security-card {
      padding: 20px 16px;
    }

    .about-card {
      min-height: 0;
      flex-direction: column;
      align-items: flex-start;
      padding: 36px 20px;

      .about-orbit {
        width: 116px;
        height: 116px;

        img {
          width: 52px;
          height: 52px;
        }
      }
    }
  }
}
</style>
