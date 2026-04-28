import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { V as VAceEditor } from './theme-monokai-CF_yROe-.js';
import { f as isValidUrl, v as validateIPs, _ as _export_sfc } from './_plugin-vue_export-helper-D32QZFxh.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createVNode:_createVNode,unref:_unref,mergeProps:_mergeProps,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock,createElementVNode:_createElementVNode,withModifiers:_withModifiers} = await importShared('vue');

const _hoisted_1 = { class: "plugin-config" };
const _hoisted_2 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_3 = { class: "d-flex align-center" };
const _hoisted_4 = { class: "font-weight-medium" };
const _hoisted_5 = { class: "text-body-2" };
const {ref,reactive,onMounted,computed} = await importShared('vue');
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    initialConfig: {
      type: Object,
      default: () => ({})
    },
    api: {
      type: Object,
      default: () => {
      }
    }
  },
  emits: ["save", "close", "switch"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const activeTab = ref("subscription");
    const editorOptions = {
      enableBasicAutocompletion: true,
      enableSnippets: true,
      enableLiveAutocompletion: true,
      showLineNumbers: true,
      tabSize: 2
    };
    const configPlaceholder = ref(
      `profile:
  store-selected: true
mode: rule
log-level: silent`
    );
    const clashTemplateDialog = ref(false);
    const clashTemplateType = ref("YAML");
    const clashTemplateContent = ref("");
    const form = ref(null);
    const isFormValid = ref(true);
    const error = ref("");
    const saving = ref(false);
    const testing = ref(false);
    const dashboardComponents = ["Clash Info", "Traffic Stats"];
    const showSecrets = ref({ 0: false });
    const testResult = reactive({
      show: false,
      success: false,
      title: "",
      message: ""
    });
    const defaultConfig = {
      enabled: false,
      subscriptions_config: [],
      filter_keywords: ["公益性", "高延迟", "域名", "官网", "重启", "过期时间", "系统代理"],
      clash_dashboards: [{ url: "", secret: "" }],
      movie_pilot_url: "",
      cron_string: "0 */6 * * *",
      timeout: 10,
      retry_times: 3,
      proxy: false,
      notify: false,
      auto_update_subscriptions: true,
      ruleset_prefix: "📂<=",
      acl4ssr_prefix: "🗂️=>",
      group_by_region: false,
      group_by_country: false,
      refresh_delay: 5,
      enable_acl4ssr: false,
      dashboard_components: [],
      clash_template: "",
      hint_geo_dat: false,
      best_cf_ip: [],
      active_dashboard: 0,
      apikey: null,
      identifiers: [],
      cache_ttl: 3600
    };
    const config = reactive({ ...defaultConfig });
    onMounted(() => {
      if (props.initialConfig) {
        Object.keys(props.initialConfig).forEach((key) => {
          if (key in config) {
            config[key] = props.initialConfig[key];
          }
        });
      }
    });
    const sub_links = computed(() => {
      if (!config.subscriptions_config) {
        return [];
      }
      return config.subscriptions_config.map((item) => item.url);
    });
    const generateApiKey = () => {
      const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
      let key = "";
      for (let i = 0; i < 32; i++) {
        key += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      config.apikey = key;
    };
    function showError(title, msg) {
      testResult.title = title;
      testResult.success = false;
      testResult.message = msg;
      testResult.show = true;
    }
    async function testConnection() {
      testing.value = true;
      error.value = "";
      testResult.show = false;
      try {
        if (sub_links.value.length === 0) {
          showError("连接测试失败", "请先配置至少一个订阅链接");
        }
        const testParams = {
          clash_apis: config.clash_dashboards,
          sub_links: sub_links.value
        };
        const result = await props.api.post("/plugin/MubeyClashRP/connectivity", testParams);
        if (result.success) {
          testResult.success = true;
          testResult.title = "连接测试成功！";
          testResult.message = "Clash面板和订阅链接连接正常，配置验证通过";
          testResult.show = true;
          setTimeout(() => {
            testResult.show = false;
          }, 5e3);
        } else {
          showError("连接测试失败", result.message || "连接测试失败，请检查配置");
        }
      } catch (err) {
        if (err instanceof Error) showError("连接测试失败", err.message);
      } finally {
        testing.value = false;
      }
    }
    async function saveConfig() {
      for (let i = 0; i < config.subscriptions_config.length; i++) {
        const sub = config.subscriptions_config[i];
        if (!sub.url || !isValidUrl(sub.url)) {
          error.value = `订阅配置 ${i + 1} 中的URL无效或为空`;
          return;
        }
      }
      if (!isFormValid.value) {
        error.value = "请修正表单中的错误";
        return;
      }
      saving.value = true;
      error.value = "";
      try {
        await new Promise((resolve) => setTimeout(resolve, 1e3));
        emit("save", { ...config });
      } catch (err) {
        if (err instanceof Error) error.value = err.message || "保存配置失败";
      } finally {
        saving.value = false;
      }
    }
    const toggleSecret = (index) => {
      showSecrets.value[index] = !showSecrets.value[index];
    };
    const addClashConfig = () => {
      const newIndex = config.clash_dashboards.length;
      config.clash_dashboards.push({ url: "", secret: "" });
      showSecrets.value[newIndex] = false;
    };
    const removeClashConfig = (index) => {
      config.clash_dashboards.splice(index, 1);
      delete showSecrets.value[index];
      if (config.active_dashboard === index) {
        config.active_dashboard = config.clash_dashboards.length > 0 ? 0 : null;
      }
    };
    const addSubscriptionConfig = () => {
      config.subscriptions_config.push({
        url: "",
        rules: false,
        proxies: true,
        "proxy-groups": false,
        "rule-providers": false,
        "proxy-providers": false
      });
    };
    const removeSubscriptionConfig = (index) => {
      config.subscriptions_config.splice(index, 1);
    };
    function openClashTemplateDialog() {
      clashTemplateContent.value = config.clash_template;
      clashTemplateDialog.value = true;
    }
    function saveClashTemplate() {
      config.clash_template = clashTemplateContent.value;
      clashTemplateDialog.value = false;
    }
    function resetForm() {
      Object.assign(config, JSON.parse(JSON.stringify(defaultConfig)));
      if (form.value) {
        form.value.resetValidation();
      }
    }
    return (_ctx, _cache) => {
      const _component_v_alert = _resolveComponent("v-alert");
      const _component_v_card_title = _resolveComponent("v-card-title");
      const _component_v_icon = _resolveComponent("v-icon");
      const _component_v_btn = _resolveComponent("v-btn");
      const _component_v_card_item = _resolveComponent("v-card-item");
      const _component_v_switch = _resolveComponent("v-switch");
      const _component_v_col = _resolveComponent("v-col");
      const _component_v_row = _resolveComponent("v-row");
      const _component_v_text_field = _resolveComponent("v-text-field");
      const _component_v_select = _resolveComponent("v-select");
      const _component_v_tab = _resolveComponent("v-tab");
      const _component_v_tabs = _resolveComponent("v-tabs");
      const _component_v_divider = _resolveComponent("v-divider");
      const _component_v_chip = _resolveComponent("v-chip");
      const _component_v_combobox = _resolveComponent("v-combobox");
      const _component_v_spacer = _resolveComponent("v-spacer");
      const _component_v_expansion_panel_title = _resolveComponent("v-expansion-panel-title");
      const _component_v_expansion_panel_text = _resolveComponent("v-expansion-panel-text");
      const _component_v_expansion_panel = _resolveComponent("v-expansion-panel");
      const _component_v_expansion_panels = _resolveComponent("v-expansion-panels");
      const _component_v_window_item = _resolveComponent("v-window-item");
      const _component_v_radio = _resolveComponent("v-radio");
      const _component_v_radio_group = _resolveComponent("v-radio-group");
      const _component_v_cron_field = _resolveComponent("v-cron-field");
      const _component_v_window = _resolveComponent("v-window");
      const _component_v_form = _resolveComponent("v-form");
      const _component_v_card_text = _resolveComponent("v-card-text");
      const _component_v_card_actions = _resolveComponent("v-card-actions");
      const _component_v_card = _resolveComponent("v-card");
      const _component_v_dialog = _resolveComponent("v-dialog");
      return _openBlock(), _createElementBlock(_Fragment, null, [
        _createElementVNode("div", _hoisted_1, [
          error.value ? (_openBlock(), _createBlock(_component_v_alert, {
            key: 0,
            type: "error",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createTextVNode(_toDisplayString(error.value), 1)
            ]),
            _: 1
          })) : _createCommentVNode("", true),
          _createVNode(_component_v_card, null, {
            default: _withCtx(() => [
              _createVNode(_component_v_card_item, null, {
                append: _withCtx(() => [
                  _createVNode(_component_v_btn, {
                    icon: "",
                    color: "primary",
                    variant: "text",
                    onClick: _cache[0] || (_cache[0] = ($event) => emit("close"))
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { left: "" }, {
                        default: _withCtx(() => _cache[33] || (_cache[33] = [
                          _createTextVNode("mdi-close")
                        ])),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                default: _withCtx(() => [
                  _createVNode(_component_v_card_title, null, {
                    default: _withCtx(() => _cache[32] || (_cache[32] = [
                      _createTextVNode("Clash Rule Provider 插件配置")
                    ])),
                    _: 1
                  })
                ]),
                _: 1
              }),
              _createVNode(_component_v_card_text, { class: "overflow-y-auto" }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_form, {
                    ref_key: "form",
                    ref: form,
                    modelValue: isFormValid.value,
                    "onUpdate:modelValue": _cache[25] || (_cache[25] = ($event) => isFormValid.value = $event),
                    onSubmit: _withModifiers(saveConfig, ["prevent"])
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_row, null, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_col, {
                            cols: "6",
                            md: "3"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_switch, {
                                modelValue: config.enabled,
                                "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => config.enabled = $event),
                                label: "启用插件",
                                color: "primary",
                                inset: "",
                                density: "compact",
                                hint: "启用插件"
                              }, null, 8, ["modelValue"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_col, {
                            cols: "6",
                            md: "3"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_switch, {
                                modelValue: config.proxy,
                                "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => config.proxy = $event),
                                label: "启用代理",
                                color: "primary",
                                inset: "",
                                density: "compact",
                                hint: "是否使用系统代理进行网络请求"
                              }, null, 8, ["modelValue"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_col, {
                            cols: "6",
                            md: "3"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_switch, {
                                modelValue: config.notify,
                                "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => config.notify = $event),
                                label: "启用通知",
                                color: "primary",
                                inset: "",
                                density: "compact",
                                hint: "执行完成后发送通知消息"
                              }, null, 8, ["modelValue"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_col, {
                            cols: "6",
                            md: "3"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_switch, {
                                modelValue: config.auto_update_subscriptions,
                                "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => config.auto_update_subscriptions = $event),
                                label: "自动更新订阅",
                                color: "primary",
                                inset: "",
                                density: "compact",
                                hint: "定期自动更新 Clash 订阅配置"
                              }, null, 8, ["modelValue"])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_row, null, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_col, {
                            cols: "12",
                            md: "4"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_text_field, {
                                modelValue: config.movie_pilot_url,
                                "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => config.movie_pilot_url = $event),
                                label: "MoviePilot URL",
                                variant: "outlined",
                                placeholder: "http://localhost:3001",
                                hint: "MoviePilot 服务的访问地址",
                                rules: [
                                  (v) => !!v || "MoviePilot URL不能为空",
                                  (v) => _unref(isValidUrl)(v) || "请输入有效的URL地址"
                                ]
                              }, {
                                "prepend-inner": _withCtx(() => [
                                  _createVNode(_component_v_icon, { color: "success" }, {
                                    default: _withCtx(() => _cache[34] || (_cache[34] = [
                                      _createTextVNode("mdi-movie")
                                    ])),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }, 8, ["modelValue", "rules"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_col, {
                            cols: "12",
                            md: "4"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_text_field, {
                                modelValue: config.apikey,
                                "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => config.apikey = $event),
                                label: "API Key",
                                variant: "outlined",
                                placeholder: "留空使用系统 API Key",
                                hint: "用于服务认证的 API Key"
                              }, {
                                "prepend-inner": _withCtx(() => [
                                  _createVNode(_component_v_icon, { color: "warning" }, {
                                    default: _withCtx(() => _cache[35] || (_cache[35] = [
                                      _createTextVNode("mdi-key")
                                    ])),
                                    _: 1
                                  })
                                ]),
                                "append-inner": _withCtx(() => [
                                  _createVNode(_component_v_icon, {
                                    color: "primary",
                                    class: "cursor-pointer",
                                    onClick: generateApiKey
                                  }, {
                                    default: _withCtx(() => _cache[36] || (_cache[36] = [
                                      _createTextVNode(" mdi-autorenew ")
                                    ])),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }, 8, ["modelValue"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_col, {
                            cols: "12",
                            md: "4"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_select, {
                                modelValue: config.dashboard_components,
                                "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => config.dashboard_components = $event),
                                items: dashboardComponents,
                                label: "仪表盘组件",
                                "hide-details": "",
                                variant: "outlined",
                                multiple: "",
                                chips: "",
                                class: "mb-4",
                                hint: "添加仪表盘组件"
                              }, {
                                "prepend-inner": _withCtx(() => [
                                  _createVNode(_component_v_icon, { color: "info" }, {
                                    default: _withCtx(() => _cache[37] || (_cache[37] = [
                                      _createTextVNode("mdi-view-dashboard")
                                    ])),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }, 8, ["modelValue"])
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_tabs, {
                        modelValue: activeTab.value,
                        "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => activeTab.value = $event),
                        class: "mt-4",
                        grow: ""
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_tab, { value: "subscription" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, { start: "" }, {
                                default: _withCtx(() => _cache[38] || (_cache[38] = [
                                  _createTextVNode("mdi-link-variant")
                                ])),
                                _: 1
                              }),
                              _cache[39] || (_cache[39] = _createTextVNode(" 订阅配置 "))
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_tab, { value: "clash" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, { start: "" }, {
                                default: _withCtx(() => _cache[40] || (_cache[40] = [
                                  _createTextVNode("mdi-application-brackets")
                                ])),
                                _: 1
                              }),
                              _cache[41] || (_cache[41] = _createTextVNode(" Clash API 配置 "))
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_tab, { value: "execution" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, { start: "" }, {
                                default: _withCtx(() => _cache[42] || (_cache[42] = [
                                  _createTextVNode("mdi-play-circle")
                                ])),
                                _: 1
                              }),
                              _cache[43] || (_cache[43] = _createTextVNode(" 执行设置 "))
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_tab, { value: "settings" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, { start: "" }, {
                                default: _withCtx(() => _cache[44] || (_cache[44] = [
                                  _createTextVNode("mdi-cog")
                                ])),
                                _: 1
                              }),
                              _cache[45] || (_cache[45] = _createTextVNode(" 高级选项 "))
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }, 8, ["modelValue"]),
                      _createVNode(_component_v_divider),
                      _createVNode(_component_v_window, {
                        modelValue: activeTab.value,
                        "onUpdate:modelValue": _cache[24] || (_cache[24] = ($event) => activeTab.value = $event),
                        class: "pa-4"
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_v_window_item, { value: "subscription" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_switch, {
                                        modelValue: config.group_by_country,
                                        "onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => config.group_by_country = $event),
                                        label: "按国家分组节点",
                                        color: "primary",
                                        inset: "",
                                        hint: "启用后，根据名称将节点添加到代理组"
                                      }, null, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_switch, {
                                        modelValue: config.group_by_region,
                                        "onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => config.group_by_region = $event),
                                        label: "按大洲分组节点",
                                        color: "primary",
                                        inset: "",
                                        hint: "启用后，根据名称将节点添加到代理组"
                                      }, null, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }),
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, { cols: "12" }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_combobox, {
                                        modelValue: config.filter_keywords,
                                        "onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => config.filter_keywords = $event),
                                        label: "节点过滤关键词",
                                        variant: "outlined",
                                        multiple: "",
                                        chips: "",
                                        "closable-chips": "",
                                        clearable: "",
                                        hint: "添加用于过滤节点的关键词"
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "info" }, {
                                            default: _withCtx(() => _cache[46] || (_cache[46] = [
                                              _createTextVNode("mdi-filter")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        chip: _withCtx(({ props: props2, item }) => [
                                          _createVNode(_component_v_chip, _mergeProps(props2, {
                                            closable: "",
                                            size: "small",
                                            color: "info"
                                          }), {
                                            default: _withCtx(() => [
                                              _createTextVNode(_toDisplayString(item.value), 1)
                                            ]),
                                            _: 2
                                          }, 1040)
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_divider),
                                  _createVNode(_component_v_col, { cols: "12" }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_expansion_panels, { multiple: "" }, {
                                        default: _withCtx(() => [
                                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(config.subscriptions_config, (item, index) => {
                                            return _openBlock(), _createBlock(_component_v_expansion_panel, { key: index }, {
                                              default: _withCtx(() => [
                                                _createVNode(_component_v_expansion_panel_title, null, {
                                                  default: _withCtx(() => [
                                                    _createElementVNode("span", _hoisted_2, " 订阅配置 " + _toDisplayString(index + 1), 1),
                                                    _createVNode(_component_v_spacer),
                                                    _createVNode(_component_v_btn, {
                                                      icon: "",
                                                      size: "small",
                                                      color: "error",
                                                      variant: "text",
                                                      onClick: _withModifiers(($event) => removeSubscriptionConfig(index), ["stop"])
                                                    }, {
                                                      default: _withCtx(() => [
                                                        _createVNode(_component_v_icon, null, {
                                                          default: _withCtx(() => _cache[47] || (_cache[47] = [
                                                            _createTextVNode("mdi-delete")
                                                          ])),
                                                          _: 1
                                                        })
                                                      ]),
                                                      _: 2
                                                    }, 1032, ["onClick"])
                                                  ]),
                                                  _: 2
                                                }, 1024),
                                                _createVNode(_component_v_expansion_panel_text, null, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_row, { dense: "" }, {
                                                      default: _withCtx(() => [
                                                        _createVNode(_component_v_col, { cols: "12" }, {
                                                          default: _withCtx(() => [
                                                            _createVNode(_component_v_text_field, {
                                                              modelValue: item.url,
                                                              "onUpdate:modelValue": ($event) => item.url = $event,
                                                              label: "订阅链接",
                                                              variant: "underlined",
                                                              placeholder: "https://xxx.com/clash/config.yaml",
                                                              density: "compact",
                                                              rules: [
                                                                (v) => !!v || "订阅链接不能为空",
                                                                (v) => _unref(isValidUrl)(v) || "请输入有效的 URL 地址"
                                                              ]
                                                            }, {
                                                              "prepend-inner": _withCtx(() => [
                                                                _createVNode(_component_v_icon, { color: "primary" }, {
                                                                  default: _withCtx(() => _cache[48] || (_cache[48] = [
                                                                    _createTextVNode("mdi-link")
                                                                  ])),
                                                                  _: 1
                                                                })
                                                              ]),
                                                              _: 2
                                                            }, 1032, ["modelValue", "onUpdate:modelValue", "rules"])
                                                          ]),
                                                          _: 2
                                                        }, 1024),
                                                        _createVNode(_component_v_col, {
                                                          cols: "12",
                                                          md: "3"
                                                        }, {
                                                          default: _withCtx(() => [
                                                            _createVNode(_component_v_switch, {
                                                              modelValue: item.rules,
                                                              "onUpdate:modelValue": ($event) => item.rules = $event,
                                                              label: "保留规则",
                                                              color: "primary",
                                                              density: "compact"
                                                            }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                                          ]),
                                                          _: 2
                                                        }, 1024),
                                                        _createVNode(_component_v_col, {
                                                          cols: "12",
                                                          md: "3"
                                                        }, {
                                                          default: _withCtx(() => [
                                                            _createVNode(_component_v_switch, {
                                                              modelValue: item["rule-providers"],
                                                              "onUpdate:modelValue": ($event) => item["rule-providers"] = $event,
                                                              label: "保留规则集合",
                                                              color: "primary",
                                                              density: "compact"
                                                            }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                                          ]),
                                                          _: 2
                                                        }, 1024),
                                                        _createVNode(_component_v_col, {
                                                          cols: "12",
                                                          md: "3"
                                                        }, {
                                                          default: _withCtx(() => [
                                                            _createVNode(_component_v_switch, {
                                                              modelValue: item["proxy-groups"],
                                                              "onUpdate:modelValue": ($event) => item["proxy-groups"] = $event,
                                                              label: "保留代理组",
                                                              color: "primary",
                                                              density: "compact"
                                                            }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                                          ]),
                                                          _: 2
                                                        }, 1024),
                                                        _createVNode(_component_v_col, {
                                                          cols: "12",
                                                          md: "3"
                                                        }, {
                                                          default: _withCtx(() => [
                                                            _createVNode(_component_v_switch, {
                                                              modelValue: item["proxy-providers"],
                                                              "onUpdate:modelValue": ($event) => item["proxy-providers"] = $event,
                                                              label: "保留代理集合",
                                                              color: "primary",
                                                              density: "compact"
                                                            }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                                          ]),
                                                          _: 2
                                                        }, 1024)
                                                      ]),
                                                      _: 2
                                                    }, 1024)
                                                  ]),
                                                  _: 2
                                                }, 1024)
                                              ]),
                                              _: 2
                                            }, 1024);
                                          }), 128))
                                        ]),
                                        _: 1
                                      }),
                                      _createVNode(_component_v_row, {
                                        dense: "",
                                        justify: "space-between"
                                      }, {
                                        default: _withCtx(() => [
                                          _createVNode(_component_v_btn, {
                                            size: "small",
                                            color: "primary",
                                            variant: "tonal",
                                            class: "mt-2",
                                            onClick: addSubscriptionConfig
                                          }, {
                                            default: _withCtx(() => [
                                              _createVNode(_component_v_icon, { start: "" }, {
                                                default: _withCtx(() => _cache[49] || (_cache[49] = [
                                                  _createTextVNode("mdi-plus")
                                                ])),
                                                _: 1
                                              }),
                                              _cache[50] || (_cache[50] = _createTextVNode(" 添加 "))
                                            ]),
                                            _: 1
                                          }),
                                          _createVNode(_component_v_btn, {
                                            size: "small",
                                            color: "primary",
                                            variant: "tonal",
                                            class: "mt-2",
                                            onClick: openClashTemplateDialog
                                          }, {
                                            default: _withCtx(() => [
                                              _createVNode(_component_v_icon, { left: "" }, {
                                                default: _withCtx(() => _cache[51] || (_cache[51] = [
                                                  _createTextVNode("mdi-import")
                                                ])),
                                                _: 1
                                              }),
                                              _cache[52] || (_cache[52] = _createTextVNode(" 配置模板 "))
                                            ]),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      })
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              })
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_window_item, { value: "clash" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_alert, {
                                "border-color": "info",
                                variant: "tonal",
                                border: "start",
                                text: "Clash 访问地址用于通知 Clash 更新规则集; 选中的面板用于小组件显示",
                                class: "mb-3"
                              }),
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, { cols: "12" }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_radio_group, {
                                        modelValue: config.active_dashboard,
                                        "onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => config.active_dashboard = $event)
                                      }, {
                                        default: _withCtx(() => [
                                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(config.clash_dashboards, (item, index) => {
                                            return _openBlock(), _createBlock(_component_v_row, { key: index }, {
                                              default: _withCtx(() => [
                                                _createVNode(_component_v_col, {
                                                  cols: "2",
                                                  md: "1",
                                                  class: "d-flex align-center"
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_radio, {
                                                      value: index,
                                                      color: "primary",
                                                      label: ""
                                                    }, null, 8, ["value"])
                                                  ]),
                                                  _: 2
                                                }, 1024),
                                                _createVNode(_component_v_col, {
                                                  cols: "10",
                                                  md: "5"
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_text_field, {
                                                      modelValue: item.url,
                                                      "onUpdate:modelValue": ($event) => item.url = $event,
                                                      label: "API URL",
                                                      variant: "outlined",
                                                      placeholder: "http://localhost:9090",
                                                      density: "compact",
                                                      rules: [(v) => !v || _unref(isValidUrl)(v) || "请输入有效的URL地址"]
                                                    }, {
                                                      "prepend-inner": _withCtx(() => [
                                                        _createVNode(_component_v_icon, { color: "primary" }, {
                                                          default: _withCtx(() => _cache[53] || (_cache[53] = [
                                                            _createTextVNode("mdi-web")
                                                          ])),
                                                          _: 1
                                                        })
                                                      ]),
                                                      _: 2
                                                    }, 1032, ["modelValue", "onUpdate:modelValue", "rules"])
                                                  ]),
                                                  _: 2
                                                }, 1024),
                                                _createVNode(_component_v_col, {
                                                  cols: "10",
                                                  md: "5"
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_text_field, {
                                                      modelValue: item.secret,
                                                      "onUpdate:modelValue": ($event) => item.secret = $event,
                                                      label: "API 密钥",
                                                      variant: "outlined",
                                                      placeholder: "your-clash-secret",
                                                      density: "compact",
                                                      "append-inner-icon": showSecrets.value[index] ? "mdi-eye-off" : "mdi-eye",
                                                      type: showSecrets.value[index] ? "text" : "password",
                                                      "onClick:appendInner": ($event) => toggleSecret(index)
                                                    }, {
                                                      "prepend-inner": _withCtx(() => [
                                                        _createVNode(_component_v_icon, { color: "warning" }, {
                                                          default: _withCtx(() => _cache[54] || (_cache[54] = [
                                                            _createTextVNode("mdi-key")
                                                          ])),
                                                          _: 1
                                                        })
                                                      ]),
                                                      _: 2
                                                    }, 1032, ["modelValue", "onUpdate:modelValue", "append-inner-icon", "type", "onClick:appendInner"])
                                                  ]),
                                                  _: 2
                                                }, 1024),
                                                _createVNode(_component_v_col, {
                                                  cols: "2",
                                                  md: "1",
                                                  class: "d-flex align-center"
                                                }, {
                                                  default: _withCtx(() => [
                                                    _createVNode(_component_v_btn, {
                                                      icon: "",
                                                      color: "error",
                                                      variant: "text",
                                                      onClick: ($event) => removeClashConfig(index)
                                                    }, {
                                                      default: _withCtx(() => [
                                                        _createVNode(_component_v_icon, null, {
                                                          default: _withCtx(() => _cache[55] || (_cache[55] = [
                                                            _createTextVNode("mdi-delete")
                                                          ])),
                                                          _: 1
                                                        })
                                                      ]),
                                                      _: 2
                                                    }, 1032, ["onClick"])
                                                  ]),
                                                  _: 2
                                                }, 1024)
                                              ]),
                                              _: 2
                                            }, 1024);
                                          }), 128))
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"]),
                                      _createVNode(_component_v_btn, {
                                        size: "small",
                                        color: "primary",
                                        variant: "tonal",
                                        class: "mt-2",
                                        onClick: addClashConfig
                                      }, {
                                        default: _withCtx(() => [
                                          _createVNode(_component_v_icon, { start: "" }, {
                                            default: _withCtx(() => _cache[56] || (_cache[56] = [
                                              _createTextVNode("mdi-plus")
                                            ])),
                                            _: 1
                                          }),
                                          _cache[57] || (_cache[57] = _createTextVNode(" 添加 "))
                                        ]),
                                        _: 1
                                      })
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              })
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_window_item, { value: "execution" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_cron_field, {
                                        modelValue: config.cron_string,
                                        "onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => config.cron_string = $event),
                                        label: "执行周期",
                                        placeholder: "0 4 * * *",
                                        hint: "使用标准Cron表达式格式 (分 时 日 月 周)"
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "info" }, {
                                            default: _withCtx(() => _cache[58] || (_cache[58] = [
                                              _createTextVNode("mdi-clock-time-four-outline")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.timeout,
                                        "onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => config.timeout = $event),
                                        modelModifiers: { number: true },
                                        label: "超时时间",
                                        variant: "outlined",
                                        type: "number",
                                        min: "1",
                                        max: "300",
                                        suffix: "秒",
                                        hint: "请求的超时时间",
                                        rules: [(v) => v > 0 || "超时时间必须大于0"]
                                      }, null, 8, ["modelValue", "rules"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.retry_times,
                                        "onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => config.retry_times = $event),
                                        modelModifiers: { number: true },
                                        label: "重试次数",
                                        variant: "outlined",
                                        type: "number",
                                        min: "0",
                                        max: "10",
                                        hint: "失败时的重试次数",
                                        rules: [(v) => v >= 0 || "重试次数不能为负数"]
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "info" }, {
                                            default: _withCtx(() => _cache[59] || (_cache[59] = [
                                              _createTextVNode("mdi-refresh")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue", "rules"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.refresh_delay,
                                        "onUpdate:modelValue": _cache[16] || (_cache[16] = ($event) => config.refresh_delay = $event),
                                        modelModifiers: { number: true },
                                        label: "刷新延迟",
                                        variant: "outlined",
                                        type: "number",
                                        min: "1",
                                        max: "30",
                                        suffix: "秒",
                                        hint: "通知Clash刷新规则集的延迟时间",
                                        rules: [(v) => v >= 0 || "刷新延迟不能为负数"]
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "info" }, {
                                            default: _withCtx(() => _cache[60] || (_cache[60] = [
                                              _createTextVNode("mdi-clock-outline")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue", "rules"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              })
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_window_item, { value: "settings" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_switch, {
                                        modelValue: config.hint_geo_dat,
                                        "onUpdate:modelValue": _cache[17] || (_cache[17] = ($event) => config.hint_geo_dat = $event),
                                        label: "Geo规则补全",
                                        color: "primary",
                                        inset: "",
                                        hint: "获取官方Geo数据库, 并在输入时补全"
                                      }, null, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "6"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_switch, {
                                        modelValue: config.enable_acl4ssr,
                                        "onUpdate:modelValue": _cache[18] || (_cache[18] = ($event) => config.enable_acl4ssr = $event),
                                        label: "ACL4SSR规则集",
                                        color: "primary",
                                        inset: "",
                                        hint: "启用ACL4SSR规则集"
                                      }, null, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }),
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "4"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.ruleset_prefix,
                                        "onUpdate:modelValue": _cache[19] || (_cache[19] = ($event) => config.ruleset_prefix = $event),
                                        label: "规则集前缀",
                                        variant: "outlined",
                                        placeholder: "📂<=",
                                        hint: "为生成的规则集添加前缀"
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "info" }, {
                                            default: _withCtx(() => _cache[61] || (_cache[61] = [
                                              _createTextVNode("mdi-palette")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "4"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.acl4ssr_prefix,
                                        "onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => config.acl4ssr_prefix = $event),
                                        label: "ACL4SSR 规则集前缀",
                                        variant: "outlined",
                                        placeholder: "🗂️=>",
                                        hint: "ACL4SSR 规则集前缀"
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "primary" }, {
                                            default: _withCtx(() => _cache[62] || (_cache[62] = [
                                              _createTextVNode("mdi-palette")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  }),
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "4"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_text_field, {
                                        modelValue: config.cache_ttl,
                                        "onUpdate:modelValue": _cache[21] || (_cache[21] = ($event) => config.cache_ttl = $event),
                                        label: "缓存 TTL",
                                        variant: "outlined",
                                        placeholder: "3600",
                                        type: "number",
                                        min: "600",
                                        suffix: "秒"
                                      }, {
                                        "prepend-inner": _withCtx(() => [
                                          _createVNode(_component_v_icon, { color: "warning" }, {
                                            default: _withCtx(() => _cache[63] || (_cache[63] = [
                                              _createTextVNode("mdi-alarm")
                                            ])),
                                            _: 1
                                          })
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }),
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "12"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_combobox, {
                                        modelValue: config.best_cf_ip,
                                        "onUpdate:modelValue": _cache[22] || (_cache[22] = ($event) => config.best_cf_ip = $event),
                                        label: "Cloudflare CDN 优选 IPs",
                                        variant: "outlined",
                                        multiple: "",
                                        chips: "",
                                        "closable-chips": "",
                                        clearable: "",
                                        hint: "用于设置 Hosts 中的 Cloudflare 域名",
                                        rules: [_unref(validateIPs)]
                                      }, {
                                        chip: _withCtx(({ props: props2, item }) => [
                                          _createVNode(_component_v_chip, _mergeProps(props2, {
                                            closable: "",
                                            size: "small"
                                          }), {
                                            default: _withCtx(() => [
                                              _createTextVNode(_toDisplayString(item.value), 1)
                                            ]),
                                            _: 2
                                          }, 1040)
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue", "rules"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }),
                              _createVNode(_component_v_row, null, {
                                default: _withCtx(() => [
                                  _createVNode(_component_v_col, {
                                    cols: "12",
                                    md: "12"
                                  }, {
                                    default: _withCtx(() => [
                                      _createVNode(_component_v_combobox, {
                                        modelValue: config.identifiers,
                                        "onUpdate:modelValue": _cache[23] || (_cache[23] = ($event) => config.identifiers = $event),
                                        label: "预设设备标识",
                                        variant: "outlined",
                                        multiple: "",
                                        chips: "",
                                        "closable-chips": "",
                                        clearable: "",
                                        hint: "获取配置时的额外查询参数 「identifier」"
                                      }, {
                                        chip: _withCtx(({ props: props2, item }) => [
                                          _createVNode(_component_v_chip, _mergeProps(props2, {
                                            closable: "",
                                            size: "small"
                                          }), {
                                            default: _withCtx(() => [
                                              _createTextVNode(_toDisplayString(item.value), 1)
                                            ]),
                                            _: 2
                                          }, 1040)
                                        ]),
                                        _: 1
                                      }, 8, ["modelValue"])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              })
                            ]),
                            _: 1
                          })
                        ]),
                        _: 1
                      }, 8, ["modelValue"])
                    ]),
                    _: 1
                  }, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_v_alert, {
                type: "info",
                variant: "tonal"
              }, {
                default: _withCtx(() => _cache[64] || (_cache[64] = [
                  _createTextVNode(" 配置说明参考: "),
                  _createElementVNode("a", {
                    href: "https://github.com/wumode/MoviePilot-Plugins/tree/main/plugins.v2/clashruleprovider/README.md",
                    target: "_blank",
                    style: { "text-decoration": "underline" }
                  }, "README", -1)
                ])),
                _: 1
              }),
              _createVNode(_component_v_card_actions, null, {
                default: _withCtx(() => [
                  _createVNode(_component_v_btn, {
                    color: "primary",
                    onClick: _cache[26] || (_cache[26] = ($event) => emit("switch"))
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { left: "" }, {
                        default: _withCtx(() => _cache[65] || (_cache[65] = [
                          _createTextVNode("mdi-view-dashboard-edit")
                        ])),
                        _: 1
                      }),
                      _cache[66] || (_cache[66] = _createTextVNode(" 规则 "))
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_btn, {
                    color: "secondary",
                    onClick: resetForm
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { left: "" }, {
                        default: _withCtx(() => _cache[67] || (_cache[67] = [
                          _createTextVNode("mdi-autorenew")
                        ])),
                        _: 1
                      }),
                      _cache[68] || (_cache[68] = _createTextVNode(" 重置 "))
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_btn, {
                    color: "info",
                    loading: testing.value,
                    onClick: testConnection
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { left: "" }, {
                        default: _withCtx(() => _cache[69] || (_cache[69] = [
                          _createTextVNode("mdi-connection")
                        ])),
                        _: 1
                      }),
                      _cache[70] || (_cache[70] = _createTextVNode(" 测试连接 "))
                    ]),
                    _: 1
                  }, 8, ["loading"]),
                  _createVNode(_component_v_spacer),
                  _createVNode(_component_v_btn, {
                    color: "primary",
                    disabled: !isFormValid.value,
                    loading: saving.value,
                    onClick: saveConfig
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { left: "" }, {
                        default: _withCtx(() => _cache[71] || (_cache[71] = [
                          _createTextVNode("mdi-content-save")
                        ])),
                        _: 1
                      }),
                      _cache[72] || (_cache[72] = _createTextVNode(" 保存配置 "))
                    ]),
                    _: 1
                  }, 8, ["disabled", "loading"])
                ]),
                _: 1
              }),
              testResult.show ? (_openBlock(), _createBlock(_component_v_alert, {
                key: 0,
                type: testResult.success ? "success" : "error",
                variant: "tonal",
                closable: "",
                class: "ma-4 mt-0",
                "onClick:close": _cache[27] || (_cache[27] = ($event) => testResult.show = false)
              }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_3, [
                    _createVNode(_component_v_icon, { class: "mr-2" }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(testResult.success ? "mdi-check-circle" : "mdi-alert-circle"), 1)
                      ]),
                      _: 1
                    }),
                    _createElementVNode("div", null, [
                      _createElementVNode("div", _hoisted_4, _toDisplayString(testResult.title), 1),
                      _createElementVNode("div", _hoisted_5, _toDisplayString(testResult.message), 1)
                    ])
                  ])
                ]),
                _: 1
              }, 8, ["type"])) : _createCommentVNode("", true)
            ]),
            _: 1
          })
        ]),
        _createVNode(_component_v_dialog, {
          modelValue: clashTemplateDialog.value,
          "onUpdate:modelValue": _cache[31] || (_cache[31] = ($event) => clashTemplateDialog.value = $event),
          "max-width": "600"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_title, null, {
                  default: _withCtx(() => _cache[73] || (_cache[73] = [
                    _createTextVNode("Clash 配置模板")
                  ])),
                  _: 1
                }),
                _createVNode(_component_v_card_text, { style: { "max-height": "900px", "overflow-y": "auto" } }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_select, {
                      modelValue: clashTemplateType.value,
                      "onUpdate:modelValue": _cache[28] || (_cache[28] = ($event) => clashTemplateType.value = $event),
                      items: ["YAML"],
                      label: "配置类型",
                      class: "mb-4"
                    }, null, 8, ["modelValue"]),
                    _createVNode(_unref(VAceEditor), {
                      value: clashTemplateContent.value,
                      "onUpdate:value": _cache[29] || (_cache[29] = ($event) => clashTemplateContent.value = $event),
                      lang: "yaml",
                      theme: "monokai",
                      hint: "",
                      options: editorOptions,
                      placeholder: configPlaceholder.value,
                      style: { "height": "30rem", "width": "100%", "margin-bottom": "16px" }
                    }, null, 8, ["value", "placeholder"]),
                    _createVNode(_component_v_alert, {
                      type: "info",
                      dense: "",
                      class: "mb-4",
                      variant: "tonal"
                    }, {
                      default: _withCtx(() => _cache[74] || (_cache[74] = [
                        _createTextVNode("规则和出站代理会被添加在配置模板上 ")
                      ])),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_card_actions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_btn, {
                      onClick: _cache[30] || (_cache[30] = ($event) => clashTemplateDialog.value = false)
                    }, {
                      default: _withCtx(() => _cache[75] || (_cache[75] = [
                        _createTextVNode("取消")
                      ])),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      color: "primary",
                      onClick: saveClashTemplate
                    }, {
                      default: _withCtx(() => _cache[76] || (_cache[76] = [
                        _createTextVNode("确定")
                      ])),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"])
      ], 64);
    };
  }
});

const ConfigComponent = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-3fef8398"]]);

export { ConfigComponent as default };
