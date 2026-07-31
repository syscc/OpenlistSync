<script setup>
import { computed, onMounted, ref } from "vue";
import { delNotify, getNotifyList, postAddNotify, putEditNotify, putEnableNotify } from "@/api/notify";
import notifyMethod, { notifyMethodKeys } from "@/utils/notifyMethod";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { BellRing, FlaskConical, Pencil, Plus, Power, PowerOff, Trash2 } from "@lucide/vue";

const { t } = useI18n();
const notifyMethodLength = notifyMethodKeys.length;
const dataList = ref([]);
const loading = ref(false);
const deleteLoading = ref(false);
const editLoading = ref(false);
const tstLoading = ref(false);
const enableLoading = ref(false);
const editData = ref(null);
const editFlag = ref(false);
const editShow = ref(false);
const formRef = ref();

const editRule = computed(() => [
  {
    params: {
      url: [{ type: "string", required: true, message: t("notify.requestUrl"), trigger: "blur" }],
      titleName: [{ type: "string", required: true, message: t("notify.titleName"), trigger: "blur" }],
      contentName: [{ type: "string", required: true, message: t("notify.contentName"), trigger: "blur" }],
    },
  },
  {
    params: {
      sendKey: [{ type: "string", required: true, message: t("notify.sendKey"), trigger: "blur" }],
    },
  },
  {
    params: {
      url: [{ type: "string", required: true, message: t("notify.webhook"), trigger: "blur" }],
    },
  },
  {
    params: {
      corpid: [{ type: "string", required: true, message: t("notify.corpid"), trigger: "blur" }],
      agentid: [{ type: "string", required: true, message: t("notify.agentid"), trigger: "blur" }],
      corpsecret: [{ type: "string", required: true, message: t("notify.corpsecret"), trigger: "blur" }],
      touser: [{ type: "string", required: false, trigger: "blur" }],
    },
  },
  {
    params: {
      url: [{ type: "string", required: true, message: t("notify.webhook"), trigger: "blur" }],
    },
  },
]);

const getData = () => {
  loading.value = true;
  getNotifyList()
    .then((res) => {
      dataList.value = res.data;
    })
    .finally(() => {
      loading.value = false;
    });
};

const addShow = () => {
  editFlag.value = false;
  editData.value = {
    enable: 1,
    method: 1,
    params: {
      sendKey: "",
      notSendNull: false,
    },
  };
  editShow.value = true;
};

const editShowDialog = (row) => {
  const nextEditData = JSON.parse(JSON.stringify(row));
  nextEditData.params = JSON.parse(nextEditData.params);
  if (!Object.hasOwn(nextEditData.params, "notSendNull")) {
    nextEditData.params.notSendNull = false;
  }
  editData.value = nextEditData;
  editFlag.value = true;
  editShow.value = true;
};

const methodChange = (val) => {
  if (val === 0) {
    editData.value.params = {
      url: "",
      method: "POST",
      contentType: "application/json",
      needContent: true,
      titleName: "title",
      contentName: "content",
      notSendNull: false,
    };
  } else if (val === 1) {
    editData.value.params = {
      sendKey: "",
      notSendNull: false,
    };
  } else if (val === 2) {
    editData.value.params = {
      url: "",
      notSendNull: false,
    };
  } else if (val === 3) {
    editData.value.params = {
      corpid: "",
      agentid: "",
      corpsecret: "",
      touser: "@all",
      notSendNull: false,
    };
  } else if (val === 4) {
    editData.value.params = {
      url: "",
      notSendNull: false,
    };
  }
  setTimeout(() => {
    formRef.value?.clearValidate();
  });
};

const closeShow = () => {
  formRef.value?.clearValidate();
  editShow.value = false;
};

const enableNotify = (notifyId, enable) => {
  enableLoading.value = true;
  putEnableNotify(notifyId, enable)
    .then((res) => {
      ElMessage({
        message: res.msg,
        type: "success",
      });
      getData();
    })
    .finally(() => {
      enableLoading.value = false;
    });
};

const submit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return;
    const dt = JSON.parse(JSON.stringify(editData.value));
    dt.params = JSON.stringify(dt.params);
    editLoading.value = true;
    const request = editFlag.value ? putEditNotify(dt) : postAddNotify(dt);
    request
      .then((res) => {
        ElMessage({
          message: res.msg,
          type: "success",
        });
        closeShow();
        getData();
      })
      .finally(() => {
        editLoading.value = false;
      });
  });
};

const tstCuTrueDo = (item) => {
  tstLoading.value = true;
  const it = JSON.parse(JSON.stringify(item));
  if (typeof it.params === "object" && it.params !== null) {
    it.params = JSON.stringify(it.params);
  }
  delete it.enable;
  postAddNotify(it)
    .then(() => {
      ElMessage({
        message: t("notify.testSent"),
        type: "success",
      });
    })
    .finally(() => {
      tstLoading.value = false;
    });
};

const tstCu = (item = null) => {
  if (item == null) {
    formRef.value.validate((valid) => {
      if (valid) {
        tstCuTrueDo(editData.value);
      }
    });
  } else {
    tstCuTrueDo(item);
  }
};

const delCu = (id) => {
  ElMessageBox.confirm(t("notify.deleteConfirm"), t("common.tips"), {
    confirmButtonText: t("common.confirm"),
    cancelButtonText: t("common.cancel"),
    type: "warning",
  }).then(() => {
    deleteLoading.value = true;
    delNotify(id)
      .then((res) => {
        ElMessage({
          message: res.msg,
          type: "success",
        });
        getData();
      })
      .finally(() => {
        deleteLoading.value = false;
      });
  });
};

onMounted(() => {
  getData();
});
</script>

<template>
  <div class="notify">
    <div class="notify-toolbar">
      <div class="toolbar-title">
        <span class="toolbar-icon"><BellRing :size="18" aria-hidden="true" /></span>
        <span>{{ $t("notify.method") }}</span>
      </div>
      <el-button type="primary" :icon="Plus" @click="addShow">{{ $t("notify.add") }}</el-button>
    </div>
    <div class="loading-box content-none-data" v-loading="true" v-if="loading">{{ $t("notify.loading") }}</div>
    <div v-else class="card-box">
      <article class="card-item" v-for="item in dataList" :key="item.id">
        <div class="card-item-top">
          <el-image :src="`/notify/${item.method}.png`" fit="contain" class="notify-logo" />
          <div class="notify-info">
            <div class="card-item-user">{{ notifyMethod(item.method) }}</div>
            <div :class="`card-item-enable enable-${item.enable == 1 ? 'enable' : 'disable'}`">
              {{ item.enable == 1 ? $t("notify.enabled") : $t("notify.disabled") }}
            </div>
          </div>
        </div>
        <div class="card-item-bottom">
          <el-button size="small" plain :icon="Pencil" @click="editShowDialog(item)">{{ $t("common.edit") }}</el-button>
          <el-button size="small" text :icon="Power" v-if="item.enable == 0" :loading="enableLoading" @click="enableNotify(item.id, 1)">
            {{ $t("common.enable") }}
          </el-button>
          <el-button size="small" text :icon="PowerOff" v-else :loading="enableLoading" @click="enableNotify(item.id, 0)">
            {{ $t("common.disable") }}
          </el-button>
          <el-button size="small" text :icon="FlaskConical" :loading="tstLoading" @click="tstCu(item)">{{ $t("common.test") }}</el-button>
          <el-button size="small" type="danger" text :icon="Trash2" :loading="deleteLoading" @click="delCu(item.id)">{{ $t("common.delete") }}</el-button>
        </div>
      </article>
      <button v-if="dataList.length === 0" type="button" class="empty-card" @click="addShow">
        <span class="empty-icon"><Plus :size="22" aria-hidden="true" /></span>
        <span>{{ $t("notify.empty") }}</span>
      </button>
    </div>

    <el-dialog :close-on-click-modal="false" top="6vh" v-model="editShow" :title="editFlag ? $t('notify.edit') : $t('notify.add')" width="700px" :append-to-body="true">
      <el-form :model="editData" :rules="editRule[editData.method]" ref="formRef" v-if="editShow" label-width="110px">
        <el-form-item prop="enable" :label="$t('common.enabled')">
          <el-switch v-model="editData.enable" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item prop="method" :label="$t('notify.method')" class="notify-method-form-item">
          <el-select v-model="editData.method" @change="methodChange" style="width: 100%">
            <el-option :key="meItem - 1" :value="meItem - 1" :label="notifyMethod(meItem - 1)" v-for="meItem in notifyMethodLength" />
          </el-select>
          <i18n-t v-if="editData.method == 1" keypath="notify.serverChanTip" tag="div" class="tip-box" scope="global">
            <template #serverChanT>
              <a href="https://sct.ftqq.com/r/15503" target="_blank" rel="noopener noreferrer">{{ $t("notify.serverChanT") }}</a>
            </template>
            <template #serverChan3>
              <a href="https://sc3.ft07.com/" target="_blank" rel="noopener noreferrer">{{ $t("notify.serverChan3") }}</a>
            </template>
          </i18n-t>
          <i18n-t v-else-if="editData.method == 2" keypath="notify.dingTalkTip" tag="div" class="tip-box" scope="global">
            <template #configGuide>
              <a href="https://open.dingtalk.com/document/orgapp/custom-bot-creation-and-installation" target="_blank" rel="noopener noreferrer">
                {{ $t("notify.configGuide") }}
              </a>
            </template>
          </i18n-t>
          <i18n-t v-else-if="editData.method == 3" keypath="notify.weComTip" tag="div" class="tip-box" scope="global">
            <template #configGuide>
              <a href="https://sct.ftqq.com/forward" target="_blank" rel="noopener noreferrer">{{ $t("notify.configGuide") }}</a>
            </template>
          </i18n-t>
          <i18n-t v-else-if="editData.method == 4" keypath="notify.larkTip" tag="div" class="tip-box" scope="global">
            <template #configGuide>
              <a href="https://open.larksuite.com/document/client-docs/bot-v3/add-custom-bot" target="_blank" rel="noopener noreferrer">
                {{ $t("notify.configGuide") }}
              </a>
            </template>
          </i18n-t>
        </el-form-item>
        <template v-if="editData.method == 0">
          <el-form-item prop="params.url" :label="$t('notify.requestUrl')">
            <el-input v-model="editData.params.url" :placeholder="$t('notify.requestUrl')" />
          </el-form-item>
          <el-form-item prop="params.method" :label="$t('notify.requestMethod')">
            <el-select v-model="editData.params.method" style="width: 100%">
              <el-option key="POST" value="POST" label="POST" />
              <el-option key="PUT" value="PUT" label="PUT" />
              <el-option key="GET" value="GET" label="GET" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="editData.params.method != 'GET'" prop="params.contentType" :label="$t('notify.contentType')">
            <el-select v-model="editData.params.contentType" style="width: 100%">
              <el-option key="application/json" value="application/json" label="application/json" />
              <el-option key="application/x-www-form-urlencoded" value="application/x-www-form-urlencoded" label="application/x-www-form-urlencoded" />
            </el-select>
          </el-form-item>
          <el-form-item prop="params.titleName" :label="$t('notify.titleName')">
            <el-input v-model="editData.params.titleName" :placeholder="$t('notify.titleName')" />
          </el-form-item>
          <el-form-item prop="params.needContent" :label="$t('notify.needContent')">
            <el-select v-model="editData.params.needContent" style="width: 100%">
              <el-option :key="true" :value="true" :label="$t('notify.need')" />
              <el-option :key="false" :value="false" :label="$t('notify.notNeed')" />
            </el-select>
          </el-form-item>
          <el-form-item prop="params.contentName" v-if="editData.params.needContent" :label="$t('notify.contentName')">
            <el-input v-model="editData.params.contentName" :placeholder="$t('notify.contentName')" />
          </el-form-item>
        </template>
        <template v-else-if="editData.method == 1">
          <el-form-item prop="params.sendKey" :label="$t('notify.sendKey')">
            <el-input v-model="editData.params.sendKey" :placeholder="$t('notify.sendKey')" />
          </el-form-item>
        </template>
        <template v-else-if="editData.method == 2">
          <el-form-item prop="params.url" :label="$t('notify.webhook')">
            <el-input v-model="editData.params.url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxxx" />
          </el-form-item>
        </template>
        <template v-else-if="editData.method == 3">
          <el-form-item prop="params.corpid" :label="$t('notify.corpid')">
            <el-input v-model="editData.params.corpid" :placeholder="$t('notify.corpid')" />
          </el-form-item>
          <el-form-item prop="params.agentid" :label="$t('notify.agentid')">
            <el-input v-model="editData.params.agentid" :placeholder="$t('notify.agentid')" />
          </el-form-item>
          <el-form-item prop="params.corpsecret" :label="$t('notify.corpsecret')">
            <el-input v-model="editData.params.corpsecret" :placeholder="$t('notify.corpsecret')" type="password" />
          </el-form-item>
          <el-form-item prop="params.touser" :label="$t('notify.touser')">
            <el-input v-model="editData.params.touser" :placeholder="$t('notify.touserPlaceholder')" />
          </el-form-item>
        </template>
        <template v-else-if="editData.method == 4">
          <el-form-item prop="params.url" :label="$t('notify.webhook')">
            <el-input v-model="editData.params.url" placeholder="https://open.larksuite.com/open-apis/bot/v2/hook/xxxxxxxxxx" />
          </el-form-item>
        </template>
        <el-form-item prop="params.notSendNull" :label="$t('notify.notSendNull')">
          <el-switch v-model="editData.params.notSendNull" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeShow">{{ $t("common.cancel") }}</el-button>
        <el-button :icon="FlaskConical" :loading="tstLoading" @click="tstCu()">{{ $t("common.test") }}</el-button>
        <el-button type="primary" @click="submit" :loading="editLoading">{{ $t("common.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.notify {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow-y: auto;

  .notify-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 18px 20px 6px;
  }

  .toolbar-title {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 650;
  }

  .toolbar-icon {
    width: 34px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--active-color);
    background: color-mix(in srgb, var(--active-color) 9%, transparent);
    border-radius: var(--radius-sm, 10px);
  }

  .loading-box {
    box-sizing: border-box;
    width: 100%;
    height: 100%;
  }

  .card-box {
    box-sizing: border-box;
    padding: 14px 20px 24px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr));
    gap: 12px;
    width: 100%;
  }

  .card-item {
    background-color: var(--surface-panel, var(--home-item-background-color));
    border-radius: var(--radius-md, 14px);
    border: 1px solid var(--border-color);
    min-height: 152px;
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

    .notify-logo {
      width: 48px;
      height: 48px;
      padding: 5px;
      border-radius: var(--radius-sm, 10px);
      background: color-mix(in srgb, var(--active-color) 7%, transparent);
    }

    .notify-info {
      margin-left: 12px;
      min-width: 0;
    }

    .card-item-user {
      font-size: 17px;
      font-weight: 650;
      color: var(--text-primary);
    }

    .card-item-enable {
      position: relative;
      width: fit-content;
      margin-top: 7px;
      padding: 3px 8px 3px 20px;
      border-radius: var(--radius-pill, 999px);
      font-size: 12px;
      font-weight: 650;

      &::before {
        position: absolute;
        top: 50%;
        left: 8px;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
        transform: translateY(-50%);
        content: "";
      }
    }

    .enable-enable {
      color: var(--success-color);
      background: color-mix(in srgb, var(--success-color) 11%, transparent);
    }

    .enable-disable {
      color: var(--text-muted);
      background: color-mix(in srgb, var(--text-muted) 12%, transparent);
    }

    .card-item-bottom {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      margin-top: 18px;
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
      flex-wrap: wrap;
      gap: 6px;
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

.notify-method-form-item {
  :deep(.el-form-item__content) {
    display: block;
  }
}

.tip-box {
  margin-top: 6px;
  line-height: 1.5;
  color: var(--text-muted);

  a {
    color: var(--active-color);

    &:hover {
      opacity: 0.8;
    }
  }
}

@media (max-width: 768px) {
  .notify {
    .notify-toolbar {
      padding: 12px 12px 6px;
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
        justify-content: flex-end;
      }

      .notify-info {
        min-width: 0;
      }

      .card-item-bottom {
        justify-content: flex-start;
      }
    }

    .empty-card {
      min-height: 160px;
    }
  }

  .tip-box {
    font-size: 13px;
  }
}
</style>
