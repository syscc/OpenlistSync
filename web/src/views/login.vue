<script setup>
import { ref, computed, onMounted } from "vue";
import logo from "@/views/components/logo.vue";
import lightDark from "./components/lightDark.vue";
import locale from "./components/locale.vue";
import { login, resetPwd } from "@/api/user";
import { useI18n } from "vue-i18n";
import {
  ArrowRight,
  Clapperboard,
  FolderSync,
  KeyRound,
  LockKeyhole,
  Network,
  UserRound,
} from "@lucide/vue";
import Motion from "@/utils/motion";
import { useAppStore } from "@/store/useAppStore";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import Cookies from "js-cookie";

const { t } = useI18n();
const appStore = useAppStore();
const router = useRouter();

const params = ref({
  userName: "",
  passwd: "",
});
const loginFormRef = ref();
const loading = ref(false);

const rules = computed(() => ({
  userName: [
    {
      required: true,
      message: t("login.userNameRule"),
      trigger: ["blur", "change"],
    },
  ],
  passwd: [
    {
      required: true,
      message: t("login.passwdRule"),
      trigger: ["blur", "change"],
    },
  ],
}));

const doLogin = () => {
  loginFormRef.value.validate((valid) => {
    if (!valid) return;
    Cookies.remove(appStore.cookieName);
    loading.value = true;
    login(params.value)
      .then((res) => {
        appStore.set("user", res.data);
        router.replace("/home");
      })
      .finally(() => {
        loading.value = false;
      });
  });
};

const resetShow = ref(false);
const resetFormRef = ref();
const resetForm = ref({
  userName: "",
  key: "",
  passwd: "",
  passwd2: "",
});

const validatePass2 = (rule, value, callback) => {
  if (value == "" || value == null) {
    callback(new Error(t("login.newPasswd2Rule")));
  } else if (value !== resetForm.value.passwd) {
    callback(new Error(t("login.newPasswd2Error")));
  } else {
    callback();
  }
};

const resetRules = computed(() => ({
  userName: [
    {
      required: true,
      message: t("login.userNameRule"),
      trigger: ["blur", "change"],
    },
  ],
  key: [
    {
      required: true,
      message: t("login.keyRule"),
      trigger: ["blur", "change"],
    },
  ],
  passwd: [
    {
      required: true,
      message: t("login.newPasswd"),
      trigger: ["blur", "change"],
    },
  ],
  passwd2: [
    {
      validator: validatePass2,
      trigger: ["blur", "change"],
    },
  ],
}));

const showReset = () => {
  resetShow.value = true;
};

const closeReset = () => {
  resetFormRef.value?.clearValidate();
  resetForm.value = {
    userName: "",
    key: "",
    passwd: "",
    passwd2: "",
  };
  resetShow.value = false;
};

const submitReset = () => {
  resetFormRef.value.validate((valid) => {
    if (!valid) return;
    loading.value = true;
    resetPwd(resetForm.value)
      .then(() => {
        closeReset();
        ElMessage({
          message: t("login.resetSuccess"),
          type: "success",
        });
      })
      .finally(() => {
        loading.value = false;
      });
  });
};

onMounted(() => {
  appStore.set("user", null);
});
</script>

<template>
  <div class="login">
    <div class="ambient ambient-one" aria-hidden="true"></div>
    <div class="ambient ambient-two" aria-hidden="true"></div>
    <div class="path-field" aria-hidden="true">
      <span class="path-line path-line-one"></span>
      <span class="path-line path-line-two"></span>
      <span class="path-node path-node-one"></span>
      <span class="path-node path-node-two"></span>
      <span class="path-node path-node-three"></span>
    </div>
    <header class="login-topbar">
      <logo class="topbar-logo" />
      <div class="login-tools">
        <locale />
        <lightDark />
      </div>
    </header>

    <main class="login-stage">
      <section class="story-panel" aria-labelledby="login-story-title">
        <Motion :delay="60">
          <div class="story-eyebrow">{{ $t("login.eyebrow") }}</div>
        </Motion>
        <Motion :delay="90">
          <h1 id="login-story-title">{{ $t("login.headline") }}</h1>
        </Motion>
        <Motion :delay="120">
          <p>{{ $t("login.description") }}</p>
        </Motion>
        <Motion :delay="150">
          <div class="story-features">
            <div class="feature-item"><FolderSync :size="18" aria-hidden="true" /><span>{{ $t("login.featureSync") }}</span></div>
            <div class="feature-item"><Clapperboard :size="18" aria-hidden="true" /><span>{{ $t("login.featureRename") }}</span></div>
            <div class="feature-item"><Network :size="18" aria-hidden="true" /><span>{{ $t("login.featureObserve") }}</span></div>
          </div>
        </Motion>
      </section>

      <Motion :delay="110">
        <section class="login-box" aria-labelledby="login-form-title">
          <div class="card-mark"><img src="/logo.svg" alt="" /></div>
          <div class="login-kicker">OpenListSync</div>
          <h2 id="login-form-title" class="login-title">{{ $t("login.welcome") }}</h2>
          <p class="login-subtitle">{{ $t("login.subtitle") }}</p>
          <el-form ref="loginFormRef" :model="params" :rules="rules" label-position="top">
          <el-form-item prop="userName">
            <template #label>{{ $t("login.userNameLabel") }}</template>
            <el-input :prefix-icon="UserRound" v-model="params.userName" :placeholder="$t('login.userName')" autocomplete="username" />
          </el-form-item>
          <el-form-item prop="passwd">
            <template #label>{{ $t("login.passwdLabel") }}</template>
            <el-input
              :prefix-icon="LockKeyhole"
              type="password"
              show-password
              v-model="params.passwd"
              :placeholder="$t('login.passwd')"
              autocomplete="current-password"
              @keyup.enter="doLogin"
            />
          </el-form-item>
          <button type="button" class="forgot" @click="showReset">{{ $t("login.forgot") }}</button>
          <el-form-item class="submit-item">
            <el-button :loading="loading" @click="doLogin" type="primary" size="large">
              {{ $t("login.loginBtn") }}
              <ArrowRight :size="17" aria-hidden="true" />
            </el-button>
          </el-form-item>
          </el-form>
        </section>
      </Motion>
    </main>

    <el-dialog width="560px" :append-to-body="true" v-model="resetShow" :title="$t('login.resetTitle')">
      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="110px">
        <el-form-item prop="userName" :label="$t('login.userNameLabel')">
          <el-input :prefix-icon="UserRound" v-model="resetForm.userName" :placeholder="$t('login.userName')" autocomplete="username" />
        </el-form-item>
        <el-form-item prop="key" :label="$t('login.key')">
          <el-input :prefix-icon="KeyRound" v-model="resetForm.key" :placeholder="$t('login.keyPlaceholder')" autocomplete="off" />
        </el-form-item>
        <el-form-item prop="passwd" :label="$t('user.newPasswdLabel')">
          <el-input type="password" show-password v-model="resetForm.passwd" :placeholder="$t('login.newPasswd')" />
        </el-form-item>
        <el-form-item prop="passwd2" :label="$t('user.newPasswd2Label')">
          <el-input type="password" show-password v-model="resetForm.passwd2" :placeholder="$t('login.newPasswd2')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeReset">{{ $t("common.cancel") }}</el-button>
        <el-button type="primary" @click="submitReset" :loading="loading">{{ $t("common.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.login {
  position: fixed;
  inset: 0;
  overflow: hidden auto;
  min-height: 100vh;
  min-height: 100dvh;
  box-sizing: border-box;
  color: #eefaf8;
  background: #0b2020;

  &::before {
    content: "";
    position: absolute;
    inset: 0;
    opacity: 0;
    pointer-events: none;
    background: transparent;
  }

  .ambient {
    position: absolute;
    border-radius: 50%;
    filter: blur(1px);
    pointer-events: none;
  }

  .ambient-one {
    width: min(42vw, 660px);
    aspect-ratio: 1;
    left: -12vw;
    top: 18%;
    border: 1px solid rgba(91, 220, 204, 0.13);
    box-shadow: inset 0 0 120px rgba(44, 181, 165, 0.05);
  }

  .ambient-two {
    width: min(30vw, 480px);
    aspect-ratio: 1;
    right: -8vw;
    bottom: -20%;
    border: 1px solid rgba(240, 185, 76, 0.12);
  }

  .login-topbar {
    position: fixed;
    z-index: 5;
    top: 0;
    left: 0;
    right: 0;
    height: 76px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 clamp(20px, 4vw, 64px);
    box-sizing: border-box;
    border-bottom: 1px solid rgba(200, 235, 230, 0.1);
    background: rgba(7, 17, 19, 0.46);
    backdrop-filter: blur(18px);

    :deep(.logo-title) {
      color: #f1faf8;
      background: none;
      -webkit-text-fill-color: currentColor;
    }
  }

  .login-tools {
    --text-secondary: #c9dcda;
    --surface-hover: rgba(255, 255, 255, 0.08);
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 5px 8px;
    border: 1px solid rgba(216, 242, 238, 0.14);
    border-radius: var(--radius-pill);
    background: rgba(255, 255, 255, 0.05);
  }

  .login-stage {
    position: relative;
    z-index: 2;
    width: min(1180px, calc(100% - 64px));
    min-height: 100vh;
    min-height: 100dvh;
    margin: 0 auto;
    padding: 112px 0 54px;
    box-sizing: border-box;
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(390px, 0.75fr);
    gap: clamp(48px, 8vw, 120px);
    align-items: center;
  }

  .story-panel {
    max-width: 660px;

    .story-eyebrow {
      margin-bottom: 22px;
      color: #72d8cc;
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0;
    }

    h1 {
      max-width: 620px;
      margin: 0;
      color: #f4fbfa;
      font-size: 72px;
      font-weight: 780;
      line-height: 0.98;
      letter-spacing: 0;
      text-wrap: balance;
    }

    p {
      max-width: 560px;
      margin: 30px 0 0;
      color: #a8bdbb;
      font-size: 17px;
      line-height: 1.8;
    }
  }

  .story-features {
    margin-top: 42px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .feature-item {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 9px 13px;
    color: #c9d8d6;
    border: 1px solid rgba(196, 233, 228, 0.15);
    border-radius: var(--radius-pill);
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(8px);

    svg {
      color: #66d2c5;
      stroke-width: 1.75;
    }
  }

  .path-field {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
  }

  .path-line {
    position: absolute;
    height: 1px;
    transform-origin: left center;
    background: rgba(96, 211, 198, 0.35);
  }

  .path-line-one {
    top: 34%;
    left: 7%;
    width: 46%;
    transform: rotate(-17deg);
  }

  .path-line-two {
    right: 2%;
    bottom: 28%;
    width: 38%;
    transform: rotate(14deg);
  }

  .path-node {
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #66d2c5;
    box-shadow: 0 0 0 7px rgba(102, 210, 197, 0.08), 0 0 24px rgba(102, 210, 197, 0.5);
    animation: nodePulse 3.8s ease-in-out infinite;
  }

  .path-node-one { left: 28%; top: 29%; }
  .path-node-two { left: 46%; top: 39%; animation-delay: -1.4s; }
  .path-node-three { right: 18%; bottom: 23%; animation-delay: -2.2s; }

  .login-box {
    position: relative;
    width: 100%;
    padding: clamp(30px, 4vw, 48px);
    box-sizing: border-box;
    color: var(--text-primary);
    border: 1px solid rgba(214, 234, 231, 0.18);
    border-radius: var(--radius-lg);
    background: var(--app-login-background-color);
    box-shadow: 0 40px 100px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(24px) saturate(120%);

    .card-mark {
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      margin-bottom: 22px;
      border-radius: var(--radius-lg);
      background: var(--brand-soft);

      img {
        width: 34px;
        height: 34px;
      }
    }

    .login-kicker {
      margin-bottom: 6px;
      color: var(--active-color);
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    .login-title {
      margin: 0;
      font-size: 36px;
      font-weight: 780;
      line-height: 1.1;
      letter-spacing: 0;
      color: var(--text-primary);
    }

    .login-subtitle {
      margin: 10px 0 30px;
      color: var(--text-muted);
      line-height: 1.65;
    }

    :deep(.el-form-item__label) {
      height: auto;
      padding-bottom: 7px;
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 650;
      line-height: 1.4;
    }

    .forgot {
      display: block;
      margin: -6px 0 10px auto;
      padding: 3px 0;
      border: 0;
      color: var(--active-color);
      background: transparent;
      color: var(--active-color);
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }

    :deep(.el-input) {
      font-size: 15px;

      .el-input__wrapper {
        min-height: 46px;
        padding: 1px 14px;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        background: color-mix(in srgb, var(--surface-panel) 80%, transparent);
        box-shadow: none;
      }

      .el-input__prefix-inner svg {
        width: 18px;
        height: 18px;
        color: var(--text-muted);
        stroke-width: 1.75;
      }
    }

    :deep(.el-form-item) {
      margin: 0 0 20px;

      .el-form-item__error {
        padding-top: 4px;
        font-size: 12px;
      }
    }

    :deep(.submit-item) {
      margin: 22px 0 0;
    }

    :deep(.submit-item .el-button) {
      width: 100%;
      min-height: 48px;
      gap: 7px;
      border: 0;
      border-radius: var(--radius-md);
      font-size: 15px;
      box-shadow: 0 12px 28px color-mix(in srgb, var(--brand-primary) 25%, transparent);
    }
  }
}

@keyframes nodePulse {
  0%, 100% { transform: scale(0.86); opacity: 0.5; }
  50% { transform: scale(1.18); opacity: 1; }
}

@media (max-width: 980px) {
  .login {
    .login-stage {
      width: min(620px, calc(100% - 40px));
      grid-template-columns: 1fr;
      gap: 36px;
      padding-top: 110px;
    }

    .story-panel {
      text-align: center;

      h1,
      p {
        margin-left: auto;
        margin-right: auto;
      }

      h1 {
        font-size: 56px;
      }
    }

    .story-features {
      justify-content: center;
      margin-top: 28px;
    }
  }
}

@media (max-width: 768px) {
  .login {
    .login-topbar {
      height: 62px;
      padding: 0 12px;

      :deep(.logo-title) {
        font-size: 19px;
      }
    }

    .login-tools {
      gap: 8px;
      padding: 4px 6px;
    }

    .login-stage {
      width: min(100% - 24px, 520px);
      padding: 92px 0 24px;
      gap: 26px;
    }

    .story-panel {
      .story-eyebrow {
        margin-bottom: 14px;
        font-size: 10px;
      }

      h1 {
        font-size: 44px;
      }

      p {
        margin-top: 18px;
        font-size: 14px;
        line-height: 1.65;
      }
    }

    .story-features {
      margin-top: 20px;
      gap: 7px;
    }

    .feature-item {
      padding: 7px 10px;
      font-size: 12px;
    }

    .login-box {
      width: 100%;
      padding: 28px 22px 24px;
      border-radius: var(--radius-lg);

      .login-title {
        font-size: 30px;
      }

      .login-subtitle {
        margin-bottom: 24px;
      }

      :deep(.el-form) {
        width: 100%;
      }

      :deep(.el-form-item) {
        margin-bottom: 18px;
      }
    }
  }
}

@media (max-width: 420px) {
  .login {
    .topbar-logo :deep(.logo-title) {
      display: none;
    }

    .story-features {
      display: none;
    }

    .login-stage {
      padding-top: 82px;
    }
  }
}

@media (max-width: 420px) and (max-height: 650px) {
  .login {
    .login-stage {
      padding-top: 74px;
      padding-bottom: 14px;
    }

    .story-panel {
      display: none;
    }

    .login-box {
      padding-top: 22px;

      .card-mark {
        width: 44px;
        height: 44px;
        margin-bottom: 14px;

        img {
          width: 30px;
          height: 30px;
        }
      }

      .login-subtitle {
        margin: 7px 0 18px;
      }
    }
  }
}
</style>
