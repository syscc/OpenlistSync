<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { LoaderCircle, RefreshCw } from "@lucide/vue";
import { useI18n } from "vue-i18n";

const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  autoRefresh: {
    type: Boolean,
    default: true,
  },
  freshInterval: {
    type: Number,
    default: 3119,
  },
  needShow: {
    type: Number,
    default: 2,
  },
  refreshText: {
    type: String,
    default: "",
  },
});
const emit = defineEmits(["getData"]);
const { t } = useI18n();
const refreshStatus = ref(true);
let timer = null;

const destroy = () => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
};

const refreshData = () => {
  if (!props.loading) {
    emit("getData");
  }
};

const startRefresh = () => {
  destroy();
  emit("getData");
  timer = setInterval(() => {
    emit("getData");
  }, props.freshInterval);
};

const refreshChange = (val) => {
  refreshStatus.value = val;
  if (val) {
    startRefresh();
  } else {
    destroy();
  }
};

onMounted(() => {
  refreshStatus.value = props.autoRefresh;
  if (refreshStatus.value) {
    startRefresh();
  } else {
    emit("getData");
  }
});

onBeforeUnmount(() => {
  destroy();
});
</script>

<template>
  <div class="menu-refresh">
    <div class="refresh-label" v-show="needShow > 1">{{ refreshText || t("refresh.auto") }}</div>
    <el-switch v-model="refreshStatus" v-show="needShow > 1" :aria-label="refreshText || t('refresh.auto')" @change="refreshChange" />
    <el-tooltip :content="t('refresh.manual')" placement="bottom">
      <button
        v-show="needShow > 0"
        type="button"
        class="refresh-button"
        :class="{ spinning: loading }"
        :disabled="loading"
        :aria-label="t('refresh.manual')"
        @click="refreshData"
      >
        <LoaderCircle v-if="loading" :size="18" />
        <RefreshCw v-else :size="18" />
      </button>
    </el-tooltip>
  </div>
</template>

<style lang="scss" scoped>
.menu-refresh {
  display: flex;
  align-items: center;

  .refresh-label {
    font-size: 15px;
    margin-right: 8px;
    color: var(--text-secondary);
  }

  .refresh-button {
    width: 34px;
    height: 34px;
    margin-left: 18px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--active-color);
    background: color-mix(in srgb, var(--active-color) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--active-color) 20%, transparent);
    border-radius: var(--radius-sm, 10px);
    cursor: pointer;
    transition:
      color var(--motion-fast, 160ms) ease,
      background-color var(--motion-fast, 160ms) ease,
      transform var(--motion-fast, 160ms) ease;

    &:hover:not(:disabled) {
      background: color-mix(in srgb, var(--active-color) 14%, transparent);
      transform: translateY(-1px);
    }

    &:focus-visible {
      outline: 2px solid color-mix(in srgb, var(--active-color) 55%, transparent);
      outline-offset: 2px;
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.65;
    }
  }

  .spinning {
    cursor: not-allowed;
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .menu-refresh {
    .refresh-label {
      display: none;
    }

    .refresh-button {
      margin-left: 10px;
    }
  }
}
</style>
