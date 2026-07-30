import { createI18n } from "vue-i18n";
import { LANGS } from "./langs";

const messages = Object.fromEntries(Object.entries(LANGS).map(([key, val]) => [key, val.value]));
const sysLang = navigator.language;
const defaultLang = "zh-CN";
let autoLang = defaultLang;
// 语言主标签同时按 - 和 _ 回退，例如 en-US / en_US 都能回退到 en
const sysLangBase = sysLang.split(/[-_]/)[0];
if (Object.hasOwn(messages, sysLang)) {
  autoLang = sysLang;
} else if (Object.hasOwn(messages, sysLangBase)) {
  autoLang = sysLangBase;
}
let locale = localStorage.getItem("lang");
if (locale?.toLowerCase().startsWith("zh")) {
  locale = "zh-CN";
} else if (locale?.toLowerCase().startsWith("en")) {
  locale = "en";
}
if (!Object.hasOwn(messages, locale)) {
  locale = autoLang;
}
localStorage.setItem("lang", locale);
const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale,
  fallbackLocale: defaultLang,
  messages,
});

export default i18n;
