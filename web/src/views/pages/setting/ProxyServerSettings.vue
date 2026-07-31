<script setup>
import { computed, onMounted, ref } from "vue";
import { getSystemConfig, revealProxyServer, saveSystemConfig, testProxyServer } from "@/api/system";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import { Eye, EyeOff, Gauge, LoaderCircle, Network, Save, Trash2, Undo2 } from "@lucide/vue";

const { t } = useI18n();
const formRef = ref();
const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const revealing = ref(false);
const credentialsVisible = ref(false);
const credentialsLoaded = ref(false);
const testResult = ref(null);
const initialUrl = ref("");

const proxy = ref({
  enabled: false,
  url: "",
  passwordSet: false,
  clearCredentials: false,
});

const urlChanged = computed(() => proxy.value.url.trim() !== initialUrl.value);

const applyConfig = (config = {}) => {
  const value = config.proxyServer || {};
  proxy.value = {
    enabled: Boolean(value.enabled),
    url: String(value.url || ""),
    passwordSet: Boolean(value.passwordSet),
    clearCredentials: false,
  };
  initialUrl.value = proxy.value.url;
  credentialsVisible.value = false;
  credentialsLoaded.value = false;
};

const proxyUrlPattern = /^(http|socks):\/\/(?:[^/?#@\s]*@)?(?:\[[^\]\s]+\]|[^:/?#@\s]+):(\d{1,5})\/?$/i;

const rules = computed(() => ({
  url: [
    {
      validator: (_rule, value, callback) => {
        const url = String(value || "").trim();
        if (!url) {
          if (proxy.value.enabled) {
            callback(new Error(t("setting.proxyUrlRequired")));
            return;
          }
          callback();
          return;
        }
        const match = url.match(proxyUrlPattern);
        const port = match ? Number(match[2]) : 0;
        if (!match || port < 1 || port > 65535) {
          callback(new Error(t("setting.proxyUrlInvalid")));
          return;
        }
        callback();
      },
      trigger: ["blur", "change"],
    },
  ],
}));

const loadConfig = () => {
  loading.value = true;
  getSystemConfig()
    .then((res) => applyConfig(res.data || {}))
    .finally(() => {
      loading.value = false;
    });
};

const onUrlInput = () => {
  proxy.value.clearCredentials = false;
  testResult.value = null;
};

const toggleClearCredentials = () => {
  proxy.value.clearCredentials = !proxy.value.clearCredentials;
  testResult.value = null;
};

const toggleCredentialsVisibility = () => {
  if (revealing.value) return;
  if (credentialsVisible.value) {
    credentialsVisible.value = false;
    return;
  }
  if (!proxy.value.passwordSet || urlChanged.value || credentialsLoaded.value) {
    credentialsVisible.value = true;
    return;
  }

  revealing.value = true;
  revealProxyServer()
    .then((res) => {
      const url = String(res.data?.url || "");
      if (!url) return;
      proxy.value.url = url;
      initialUrl.value = url;
      credentialsLoaded.value = true;
      credentialsVisible.value = true;
    })
    .catch(() => {})
    .finally(() => {
      revealing.value = false;
    });
};

const buildProxyTestPayload = () => {
  const payload = {};
  if (urlChanged.value) {
    payload.url = proxy.value.url.trim();
  }
  if (proxy.value.clearCredentials) {
    payload.clearCredentials = true;
  }
  return payload;
};

const runProxyTest = () => {
  formRef.value.validate((valid) => {
    if (!valid) return;
    if (!proxy.value.url.trim()) {
      ElMessage({ message: t("setting.proxyTestUrlRequired"), type: "warning" });
      return;
    }

    testing.value = true;
    testResult.value = null;
    testProxyServer(buildProxyTestPayload())
      .then((res) => {
        testResult.value = res.data || null;
      })
      .catch(() => {})
      .finally(() => {
        testing.value = false;
      });
  });
};

const saveConfig = () => {
  formRef.value.validate((valid) => {
    if (!valid) return;

    const proxyServer = { enabled: proxy.value.enabled };
    if (urlChanged.value) {
      proxyServer.url = proxy.value.url.trim();
    }
    if (proxy.value.clearCredentials) {
      proxyServer.clearCredentials = true;
    }

    saving.value = true;
    testResult.value = null;
    saveSystemConfig({ proxyServer })
      .then((res) => {
        applyConfig(res.data || {});
        ElMessage({ message: res.msg || t("common.success"), type: "success" });
      })
      .finally(() => {
        saving.value = false;
      });
  });
};

onMounted(loadConfig);
</script>

<template>
  <div class="proxy-server-page">
    <article class="proxy-card" v-loading="loading">
      <header class="card-heading">
        <div class="card-icon"><Network :size="20" aria-hidden="true" /></div>
        <div class="heading-copy">
          <h2>{{ $t("setting.proxyServerTitle") }}</h2>
          <p>{{ $t("setting.proxyServerDescription") }}</p>
        </div>
      </header>

      <div class="scope-note">{{ $t("setting.proxyServerScope") }}</div>

      <el-form ref="formRef" :model="proxy" :rules="rules" label-position="top">
        <el-form-item :label="$t('setting.proxyEnabled')">
          <div class="enable-row">
            <el-switch v-model="proxy.enabled" />
            <span class="status-label" :class="{ enabled: proxy.enabled }">
              {{ proxy.enabled ? $t("common.enabled") : $t("common.disabled") }}
            </span>
          </div>
        </el-form-item>

        <el-form-item prop="url" :label="$t('setting.proxyUrl')">
          <div class="url-row">
            <el-input
              v-model="proxy.url"
              :type="credentialsVisible ? 'text' : 'password'"
              autocomplete="new-password"
              autocapitalize="off"
              :disabled="revealing"
              :spellcheck="false"
              :placeholder="$t('setting.proxyUrlPlaceholder')"
              @input="onUrlInput"
              @keyup.enter="saveConfig"
            >
              <template #suffix>
                <button
                  type="button"
                  class="reveal-button"
                  :disabled="revealing"
                  :title="$t(credentialsVisible ? 'setting.proxyHideCredentials' : 'setting.proxyShowCredentials')"
                  :aria-label="$t(credentialsVisible ? 'setting.proxyHideCredentials' : 'setting.proxyShowCredentials')"
                  :aria-pressed="credentialsVisible"
                  @click="toggleCredentialsVisibility"
                >
                  <LoaderCircle v-if="revealing" class="reveal-spinner" :size="17" aria-hidden="true" />
                  <EyeOff v-else-if="credentialsVisible" :size="17" aria-hidden="true" />
                  <Eye v-else :size="17" aria-hidden="true" />
                </button>
              </template>
            </el-input>
            <el-tooltip
              v-if="proxy.passwordSet && !urlChanged"
              :content="proxy.clearCredentials ? $t('setting.proxyCancelClearCredentials') : $t('setting.proxyClearCredentials')"
              placement="top"
            >
              <el-button
                class="credential-button"
                :type="proxy.clearCredentials ? 'default' : 'danger'"
                :icon="proxy.clearCredentials ? Undo2 : Trash2"
                :disabled="revealing"
                :aria-label="proxy.clearCredentials ? $t('setting.proxyCancelClearCredentials') : $t('setting.proxyClearCredentials')"
                @click="toggleClearCredentials"
              />
            </el-tooltip>
          </div>
          <p class="field-tip">{{ $t("setting.proxyUrlExamples") }}</p>
          <p v-if="proxy.clearCredentials" class="credential-warning">{{ $t("setting.proxyCredentialsWillClear") }}</p>
          <p v-else-if="proxy.passwordSet && !urlChanged" class="credential-status">{{ $t("setting.proxyCredentialsStored") }}</p>
          <p v-else-if="proxy.passwordSet && urlChanged" class="credential-warning">{{ $t("setting.proxyCredentialsReplace") }}</p>
        </el-form-item>

        <div class="action-row">
          <div class="test-action">
            <el-button
              :icon="Gauge"
              :loading="testing"
              :disabled="saving || revealing"
              :title="$t('setting.proxyTestTarget')"
              @click="runProxyTest"
            >
              {{ $t("setting.proxyTest") }}
            </el-button>
            <span class="test-target">{{ $t("setting.proxyTestTarget") }}</span>
          </div>
          <el-button
            type="primary"
            :icon="Save"
            :loading="saving"
            :disabled="testing || revealing"
            @click="saveConfig"
          >
            {{ $t("setting.saveProxy") }}
          </el-button>
        </div>
        <div v-if="testResult" class="test-result" role="status">
          <Gauge :size="16" aria-hidden="true" />
          <span>
            {{ $t("setting.proxyTestResult", {
              latency: testResult.latencyMs,
              status: testResult.statusCode,
            }) }}
          </span>
        </div>
      </el-form>
    </article>
  </div>
</template>

<style lang="scss" scoped>
.proxy-server-page {
  width: 100%;
  padding: 0 0 24px;
  box-sizing: border-box;
}

.proxy-card {
  width: min(720px, 100%);
  padding: 24px;
  box-sizing: border-box;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-panel);
  box-shadow: var(--shadow-xs);
}

.card-heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;

  .heading-copy {
    min-width: 0;
  }

  h2 {
    margin: 0;
    color: var(--text-primary);
    font-size: 18px;
    font-weight: 750;
    letter-spacing: 0;
  }

  p {
    margin: 3px 0 0;
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.5;
  }
}

.card-icon {
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--active-color);
  border-radius: var(--radius-md);
  background: var(--brand-soft);
}

.scope-note {
  margin: 0 0 20px 52px;
  padding: 9px 11px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-inset);
  font-size: 12px;
  line-height: 1.5;
}

:deep(.el-form-item__label) {
  padding-bottom: 6px;
  color: var(--text-secondary);
  font-weight: 650;
}

:deep(.el-input__wrapper) {
  min-height: 42px;
}

.enable-row,
.url-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
}

.status-label {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 650;

  &.enabled {
    color: var(--success-color);
  }
}

.url-row {
  .el-input {
    min-width: 0;
    flex: 1;
  }
}

.credential-button {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  margin: 0;
  padding: 0;
}

.reveal-button {
  width: 28px;
  height: 28px;
  display: inline-grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;

  &:hover:not(:disabled) {
    color: var(--active-color);
    background: var(--brand-soft);
  }

  &:focus-visible {
    outline: 2px solid var(--active-color);
    outline-offset: 1px;
  }

  &:disabled {
    cursor: wait;
  }
}

.reveal-spinner {
  animation: reveal-spin 0.8s linear infinite;
}

@keyframes reveal-spin {
  to {
    transform: rotate(360deg);
  }
}

.field-tip,
.credential-status,
.credential-warning {
  width: 100%;
  margin: 6px 0 0;
  overflow-wrap: anywhere;
  font-size: 12px;
  line-height: 1.5;
}

.field-tip {
  color: var(--text-muted);
}

.credential-status {
  color: var(--success-color);
}

.credential-warning {
  color: var(--warning-color);
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  min-width: 0;
}

.test-action {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.test-target {
  min-width: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 12px;
  color: var(--success-color);
  font-size: 13px;
  font-weight: 650;
}

@media (max-width: 768px) {
  .proxy-server-page {
    padding-bottom: 16px;
  }

  .proxy-card {
    padding: 18px 14px;
  }

  .scope-note {
    margin-left: 0;
  }

  .action-row {
    align-items: stretch;
    flex-direction: column;
  }

  .test-action {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .action-row > .el-button {
    width: 100%;
  }
}

@media (max-width: 360px) {
  .field-tip,
  .test-target {
    display: none;
  }

  .test-result {
    margin-top: 6px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .reveal-spinner {
    animation: none;
  }
}
</style>
