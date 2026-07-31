<script setup>
import { onMounted, ref, computed, watch } from "vue";
import { openlistDelete, openlistGet, openlistPost, openlistPut } from "@/api/job";
import { getMediaScrapingConfig, saveMediaScrapingConfig } from "@/api/mediaScraping";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { Pencil, Plus, Save, Trash2 } from "@lucide/vue";

const { t } = useI18n();
const route = useRoute();
const openlistList = ref([]);
const getLoading = ref(false);
const deleteLoading = ref(false);
const editLoading = ref(false);
const editData = ref(null);
const editFlag = ref(false);
const editShow = ref(false);
const formRef = ref();
const configMode = ref(route.query.type === "mediaScraping" ? "mediaScraping" : "openlist");
const saveMediaConfigLoading = ref(false);
const extensionsText = ref("");
const tmdbApiServerOptions = [
  { label: "api.themoviedb.org", value: "https://api.themoviedb.org" },
  { label: "api.tmdb.org", value: "https://api.tmdb.org" },
];

const defaultMediaConfig = () => ({
  defaultOpenlistId: null,
  openlistIds: [],
  tmdbApiKey: "",
  tmdbBearerToken: "",
  tmdbApiUrl: "https://api.themoviedb.org",
  tmdbLanguage: "zh-CN",
  tmdbIncludeAdult: false,
  tmdbRequired: true,
  tmdbTimeout: 30,
  openlistTimeout: 30,
  dryRun: true,
  overwrite: false,
  refresh: false,
  limit: 0,
  renameThreads: 2,
  renameLogLimit: 10,
  movieTemplate: "",
  tvTemplate: "",
  mediaExtensions: [],
  customWords: "",
  customReleaseGroups: "",
  customization: "",
  rules: [],
});

const mediaConfig = ref(defaultMediaConfig());

watch(
  () => route.query.type,
  (type) => {
    configMode.value = type === "mediaScraping" ? "mediaScraping" : "openlist";
  },
);

const editRule = computed(() => ({
  url: [
    {
      required: true,
      message: t("engine.addressRule"),
      trigger: "blur",
    },
  ],
}));

const addRule = computed(() => ({
  url: [
    {
      required: true,
      message: t("engine.addressRule"),
      trigger: "blur",
    },
  ],
  token: [
    {
      required: true,
      message: t("engine.tokenRule"),
      trigger: "blur",
    },
  ],
}));

const getOpenlistList = () => {
  getLoading.value = true;
  openlistGet()
    .then((res) => {
      openlistList.value = res.data;
    })
    .finally(() => {
      getLoading.value = false;
    });
};

const getMediaConfig = () => {
  getMediaScrapingConfig().then((res) => {
    mediaConfig.value = { ...defaultMediaConfig(), ...(res.data || {}) };
    extensionsText.value = (mediaConfig.value.mediaExtensions || []).join(",");
  });
};

const buildMediaConfig = () => {
  const defaultOpenlistId = mediaConfig.value.defaultOpenlistId || null;
  return {
    ...mediaConfig.value,
    defaultOpenlistId,
    openlistIds: defaultOpenlistId ? [defaultOpenlistId] : [],
    mediaExtensions: extensionsText.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
};

const saveMediaConfig = () => {
  saveMediaConfigLoading.value = true;
  saveMediaScrapingConfig(buildMediaConfig())
    .then((res) => {
      mediaConfig.value = { ...defaultMediaConfig(), ...(res.data || {}) };
      extensionsText.value = (mediaConfig.value.mediaExtensions || []).join(",");
      ElMessage({ message: res.msg, type: "success" });
    })
    .finally(() => {
      saveMediaConfigLoading.value = false;
    });
};

const addShow = () => {
  editFlag.value = false;
  editData.value = {
    remark: "",
    url: "",
    token: "",
  };
  editShow.value = true;
};

const editShowDialog = (row) => {
  editData.value = {
    ...row,
    token: "",
  };
  editFlag.value = true;
  editShow.value = true;
};

const closeShow = () => {
  formRef.value?.clearValidate();
  editShow.value = false;
};

const ensureHttpPrefix = (url) => {
  if (!/^https?:\/\//i.test(url)) {
    if (url.startsWith("//")) {
      return "http:" + url;
    }
    return "http://" + url;
  }
  return url;
};

const submit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return;
    editData.value.url = ensureHttpPrefix(editData.value.url);
    editLoading.value = true;
    const request = editFlag.value ? openlistPut(editData.value) : openlistPost(editData.value);
    request
      .then((res) => {
        ElMessage({
          message: res.msg,
          type: "success",
        });
        closeShow();
        getOpenlistList();
      })
      .finally(() => {
        editLoading.value = false;
      });
  });
};

const delOpenlist = (openlistId) => {
  ElMessageBox.confirm(t("engine.deleteConfirm"), t("common.tips"), {
    confirmButtonText: t("common.confirm"),
    cancelButtonText: t("common.cancel"),
    type: "warning",
  }).then(() => {
    deleteLoading.value = true;
    openlistDelete(openlistId)
      .then((res) => {
        ElMessage({
          message: res.msg,
          type: "success",
        });
        getOpenlistList();
      })
      .finally(() => {
        deleteLoading.value = false;
      });
  });
};

onMounted(() => {
  getOpenlistList();
  getMediaConfig();
});
</script>

<template>
  <div class="engine">
    <div class="engine-top">
      <el-select v-model="configMode" size="small" class="config-mode">
        <el-option :label="$t('engine.openlistMode')" value="openlist" />
        <el-option :label="$t('engine.scrapingMode')" value="mediaScraping" />
      </el-select>
      <el-button v-if="configMode === 'openlist'" type="primary" :icon="Plus" @click="addShow">
        {{ $t("engine.add") }}
      </el-button>
    </div>
    <div class="loading-box content-none-data" v-loading="true" v-if="getLoading && configMode === 'openlist'">{{ $t("engine.loading") }}</div>
    <div v-else-if="configMode === 'openlist'" class="card-box">
      <article class="card-item" v-for="item in openlistList" :key="item.id">
        <div class="card-item-top">
          <el-image src="/openlist.svg" fit="contain" class="engine-logo" />
          <div class="engine-info">
            <div class="card-item-user">
              {{ item.userName }}
              <div class="card-item-remark" v-if="item.remark != null">[{{ item.remark }}]</div>
            </div>
            <div class="card-item-url">{{ item.url }}</div>
          </div>
        </div>
        <div class="card-item-bottom">
          <el-button size="small" plain :icon="Pencil" @click="editShowDialog(item)">{{ $t("common.edit") }}</el-button>
          <el-button size="small" type="danger" text :icon="Trash2" :loading="deleteLoading" @click="delOpenlist(item.id)">{{ $t("common.delete") }}</el-button>
        </div>
      </article>
      <button v-if="openlistList.length === 0" type="button" class="empty-card" @click="addShow">
        <span class="empty-icon"><Plus :size="22" aria-hidden="true" /></span>
        <span>{{ $t("engine.empty") }}</span>
      </button>
    </div>
    <div v-else class="scraping-config">
      <el-form label-width="130px" size="small">
        <section class="config-block">
          <h2>{{ $t("engineScraping.defaultEngine") }}</h2>
          <el-form-item label="OpenList">
            <el-select
              v-model="mediaConfig.defaultOpenlistId"
              filterable
              :placeholder="$t('engineScraping.defaultEnginePlaceholder')"
              class="config-width"
            >
              <el-option v-for="item in openlistList" :key="item.id" :label="item.remark || item.url" :value="item.id">
                <span>{{ item.remark || item.url }}</span>
                <span class="option-url">{{ item.url }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </section>

        <section class="config-block">
          <h2>TMDb</h2>
          <el-form-item :label="$t('engineScraping.tmdbApiServer')">
            <div class="config-column config-width">
              <el-select
                v-model="mediaConfig.tmdbApiUrl"
                filterable
                allow-create
                default-first-option
                :reserve-keyword="false"
                :placeholder="$t('engineScraping.tmdbApiServerPlaceholder')"
              >
                <el-option v-for="item in tmdbApiServerOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <span class="field-tip">{{ $t("engineScraping.tmdbApiServerTip") }}</span>
            </div>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="mediaConfig.tmdbApiKey" class="config-width" show-password />
          </el-form-item>
          <el-form-item label="Bearer Token">
            <el-input v-model="mediaConfig.tmdbBearerToken" class="config-width" show-password />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.language')">
            <el-input v-model="mediaConfig.tmdbLanguage" class="short-width" />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.matchOptions')">
            <el-checkbox v-model="mediaConfig.tmdbRequired">{{ $t("engineScraping.tmdbRequired") }}</el-checkbox>
            <el-checkbox v-model="mediaConfig.tmdbIncludeAdult">{{ $t("engineScraping.includeAdult") }}</el-checkbox>
          </el-form-item>
        </section>

        <section class="config-block">
          <h2>{{ $t("engineScraping.namingOptions") }}</h2>
          <el-form-item :label="$t('engineScraping.runOptions')">
            <el-checkbox v-model="mediaConfig.refresh">{{ $t("engineScraping.refreshCache") }}</el-checkbox>
            <el-checkbox v-model="mediaConfig.overwrite">{{ $t("engineScraping.allowOverwrite") }}</el-checkbox>
          </el-form-item>
          <el-form-item :label="$t('engineScraping.limit')">
            <el-input-number v-model="mediaConfig.limit" :min="0" />
            <span class="tip-text">{{ $t("engineScraping.unlimitedTip") }}</span>
          </el-form-item>
          <el-form-item :label="$t('engineScraping.threads')">
            <el-input-number v-model="mediaConfig.renameThreads" :min="1" :max="16" />
            <span class="tip-text">{{ $t("engineScraping.threadsTip") }}</span>
          </el-form-item>
          <el-form-item :label="$t('engineScraping.logLimit')">
            <el-input-number v-model="mediaConfig.renameLogLimit" :min="0" :max="1000" />
            <span class="tip-text">{{ $t("engineScraping.logLimitTip") }}</span>
          </el-form-item>
          <el-form-item :label="$t('engineScraping.timeout')" class="timeout-row">
            <el-input-number v-model="mediaConfig.openlistTimeout" :min="1" :step="5" />
            <span class="tip-text">OpenList {{ $t("engineScraping.seconds") }}</span>
            <el-input-number v-model="mediaConfig.tmdbTimeout" :min="1" :step="5" />
            <span class="tip-text">TMDb {{ $t("engineScraping.seconds") }}</span>
          </el-form-item>
          <el-form-item :label="$t('engineScraping.extensions')">
            <el-input v-model="extensionsText" class="config-width" placeholder=".mkv,.mp4,.ts" />
          </el-form-item>
        </section>

        <section class="config-block">
          <h2>{{ $t("engineScraping.templates") }}</h2>
          <el-form-item :label="$t('engineScraping.movieTemplate')">
            <el-input v-model="mediaConfig.movieTemplate" type="textarea" :rows="3" class="config-width" />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.tvTemplate')">
            <el-input v-model="mediaConfig.tvTemplate" type="textarea" :rows="4" class="config-width" />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.customWords')">
            <el-input v-model="mediaConfig.customWords" type="textarea" :rows="3" class="config-width" placeholder="OldName => NewName" />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.releaseGroups')">
            <el-input v-model="mediaConfig.customReleaseGroups" type="textarea" :rows="3" class="config-width" />
          </el-form-item>
          <el-form-item :label="$t('engineScraping.customization')">
            <el-input v-model="mediaConfig.customization" type="textarea" :rows="3" class="config-width" />
          </el-form-item>
        </section>

        <el-button type="primary" :icon="Save" :loading="saveMediaConfigLoading" @click="saveMediaConfig">
          {{ $t("engineScraping.save") }}
        </el-button>
      </el-form>
    </div>

    <el-dialog :close-on-click-modal="false" v-model="editShow" :title="editFlag ? $t('engine.edit') : $t('engine.add')" width="600px" :append-to-body="true">
      <el-form :model="editData" :rules="editFlag ? editRule : addRule" ref="formRef" v-if="editShow" label-width="80px">
        <el-form-item prop="url" :label="$t('engine.address')">
          <el-input v-model="editData.url" :placeholder="$t('engine.addressPlaceholder')" />
        </el-form-item>
        <el-form-item prop="remark" :label="$t('engine.remark')">
          <el-input v-model="editData.remark" :placeholder="$t('engine.remarkPlaceholder')" />
        </el-form-item>
        <el-form-item prop="token" :label="$t('engine.token')">
          <el-input
            v-model="editData.token"
            show-password
            :placeholder="editFlag ? $t('engine.tokenPlaceholderEdit') : $t('engine.tokenPlaceholderAdd')"
            @keyup.enter="submit"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeShow">{{ $t("common.cancel") }}</el-button>
        <el-button type="primary" @click="submit" :loading="editLoading">{{ $t("common.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.engine {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow-y: auto;

  .loading-box {
    box-sizing: border-box;
    width: 100%;
    height: 100%;
  }

  .engine-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 18px 20px 6px;
  }

  .config-mode {
    width: 180px;
  }

  .scraping-config {
    box-sizing: border-box;
    max-width: 920px;
    padding: 16px 20px 24px;

    .config-block {
      margin: 0 0 14px;
      padding: 16px 16px 4px;
      background-color: var(--surface-panel, var(--home-item-background-color));
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md, 14px);
      box-shadow: var(--shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.05));
    }

    h2 {
      margin: 0 0 14px;
      font-size: 16px;
    }

    .config-width {
      width: min(620px, 100%);
    }

    .short-width {
      width: 180px;
    }

    .config-column {
      display: flex;
      flex-direction: column;
      gap: 6px;

      .el-select {
        width: 100%;
      }
    }

    .field-tip {
      color: var(--text-secondary);
      font-size: 12px;
      line-height: 1.5;
    }

    .option-url,
    .tip-text {
      margin-left: 10px;
      color: var(--text-secondary);
      font-size: 12px;
    }

    .option-url {
      float: right;
    }

    .timeout-row :deep(.el-form-item__content) {
      gap: 8px;
    }
  }

  .card-box {
    box-sizing: border-box;
    padding: 14px 20px 24px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
    width: 100%;
  }

  .card-item {
    background-color: var(--surface-panel, var(--home-item-background-color));
    border-radius: var(--radius-md, 14px);
    border: 1px solid var(--border-color);
    min-height: 148px;
    margin: 0;
    padding: 18px;
    box-sizing: border-box;
    box-shadow: var(--shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.05));
    transition:
      border-color var(--motion-base, 190ms) var(--ease-standard, ease),
      box-shadow var(--motion-base, 190ms) var(--ease-standard, ease),
      transform var(--motion-base, 190ms) var(--ease-standard, ease);

    &:hover {
      border-color: color-mix(in srgb, var(--active-color) 34%, var(--border-color));
      box-shadow: var(--shadow-md, 0 14px 34px rgba(15, 23, 42, 0.09));
      transform: translateY(-2px);
    }

    .card-item-top {
      display: flex;
      align-items: center;
      justify-content: flex-start;
    }

    .engine-logo {
      width: 46px;
      height: 46px;
      padding: 7px;
      border-radius: var(--radius-sm, 10px);
      background: color-mix(in srgb, #27d9d2 10%, transparent);
    }

    .engine-info {
      margin-left: 12px;
      min-width: 0;
    }

    .card-item-user {
      font-size: 17px;
      font-weight: 650;
      display: flex;
      color: var(--text-primary);
    }

    .card-item-remark {
      margin-left: 6px;
      color: var(--text-muted);
      max-width: 120px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .card-item-url {
      margin-top: 6px;
      font-size: 12px;
      color: var(--text-secondary);
      word-break: break-all;
    }

    .card-item-bottom {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      margin-top: 18px;
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
    }
  }

  .empty-card {
    min-height: 180px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--text-secondary);
    background: var(--surface-panel, var(--home-item-background-color));
    border: 1px dashed color-mix(in srgb, var(--active-color) 36%, var(--border-color));
    border-radius: var(--radius-md, 14px);
    font: inherit;
    cursor: pointer;

    .empty-icon {
      width: 44px;
      height: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--active-color);
      background: color-mix(in srgb, var(--active-color) 10%, transparent);
      border-radius: 50%;
    }

    &:hover {
      border-style: solid;
      background: color-mix(in srgb, var(--active-color) 3%, var(--home-item-background-color));
    }

    &:focus-visible {
      outline: 2px solid color-mix(in srgb, var(--active-color) 55%, transparent);
      outline-offset: 2px;
    }
  }
}

@media (max-width: 768px) {
  .engine {
    .engine-top {
      padding: 12px 12px 6px;
    }

    .scraping-config {
      max-width: 100%;
      padding: 10px 12px 20px;

      :deep(.el-form-item) {
        display: block;
      }

      :deep(.el-form-item__label) {
        display: block;
        width: auto !important;
        height: auto;
        margin-bottom: 6px;
        text-align: left;
      }

      :deep(.el-form-item__content) {
        margin-left: 0 !important;
      }

      .config-width,
      .short-width {
        width: 100%;
      }

      .timeout-row :deep(.el-form-item__content) {
        align-items: flex-start;
        flex-direction: column;
      }
    }

    .card-box {
      grid-template-columns: minmax(0, 1fr);
      padding: 10px 12px 20px;
    }

    .card-item {
      min-height: 0;
      margin: 0;
      padding: 16px;

      .card-item-top {
        justify-content: flex-start;
      }

      .engine-info {
        flex: 1;
      }

      .card-item-user {
        min-width: 0;
        flex-wrap: wrap;
      }

      .card-item-remark {
        max-width: min(120px, 40vw);
      }

      .card-item-bottom {
        justify-content: flex-end;
      }
    }

    .empty-card {
      min-height: 160px;
    }
  }
}
</style>
