<script setup>
import { onMounted, ref, computed, watch } from "vue";
import { openlistDelete, openlistGet, openlistPost, openlistPut } from "@/api/job";
import { getMediaScrapingConfig, saveMediaScrapingConfig } from "@/api/mediaScraping";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";

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

const defaultMediaConfig = () => ({
  defaultOpenlistId: null,
  openlistIds: [],
  tmdbApiKey: "",
  tmdbBearerToken: "",
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
    </div>
    <div class="loading-box content-none-data" v-loading="true" v-if="getLoading && configMode === 'openlist'">{{ $t("engine.loading") }}</div>
    <div v-else-if="configMode === 'openlist'" class="card-box">
      <div class="card-item" v-for="item in openlistList" :key="item.id">
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
          <el-button size="small" type="primary" @click="editShowDialog(item)">{{ $t("common.edit") }}</el-button>
          <el-button size="small" type="danger" :loading="deleteLoading" @click="delOpenlist(item.id)">{{ $t("common.delete") }}</el-button>
        </div>
      </div>
      <div class="card-item card-add" @click="addShow" v-if="!getLoading">
        <template v-if="openlistList.length == 0">{{ $t("engine.empty") }}</template>
        <span v-else>{{ $t("common.add") }}</span>
      </div>
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

        <el-button type="primary" :loading="saveMediaConfigLoading" @click="saveMediaConfig">
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

  .loading-box {
    box-sizing: border-box;
    width: 100%;
    height: 100%;
  }

  .engine-top {
    padding: 16px 16px 0;
  }

  .config-mode {
    width: 180px;
  }

  .scraping-config {
    box-sizing: border-box;
    max-width: 920px;
    padding: 16px;

    .config-block {
      margin: 0 0 14px;
      padding: 16px 16px 4px;
      background-color: var(--home-item-background-color);
      border: 1px solid var(--border-color);
      border-radius: 6px;
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
    padding: 8px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    width: 100%;
  }

  .card-item {
    background-color: var(--home-item-background-color);
    border-radius: 6px;
    border: 1px solid transparent;
    min-height: 118px;
    margin: 8px;
    padding: 10px;
    box-sizing: border-box;
    transition: border-color 0.2s, transform 0.2s;

    &:hover {
      border-color: var(--active-color);
      transform: translateY(-1px);
    }

    .card-item-top {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .engine-logo {
      width: 60px;
      height: 60px;
    }

    .engine-info {
      margin-left: 12px;
      min-width: 0;
    }

    .card-item-user {
      font-size: 18px;
      display: flex;
      color: var(--text-primary);
    }

    .card-item-remark {
      margin-left: 6px;
      color: var(--warning-color);
      max-width: 120px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .card-item-url {
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      word-break: break-all;
    }

    .card-item-bottom {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 12px;
    }
  }

  .card-add {
    font-size: 26px;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--active-color);
    font-weight: 700;
  }
}

@media (max-width: 768px) {
  .engine {
    .engine-top {
      padding: 10px 8px 4px;
    }

    .scraping-config {
      max-width: 100%;
      padding: 8px;

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
      padding: 4px;
    }

    .card-item {
      min-height: 0;
      margin: 4px;
      padding: 12px;

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

    .card-add {
      min-height: 96px;
      justify-content: center;
    }
  }
}
</style>
