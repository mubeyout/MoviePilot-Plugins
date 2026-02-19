<script setup lang="ts">
import { ref, PropType, toRaw } from 'vue'
import { Proxy, ProxyData } from '@/components/types'

const props = defineProps({
  proxyData: {
    type: Object as PropType<ProxyData>,
    required: true
  },
  api: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'refresh', 'show-snackbar', 'show-error'])

const proxyForm = ref<any>(null)
const loading = ref(false)

const tab = ref('general')
const proxy = ref<Proxy>(structuredClone(toRaw(props.proxyData.data)))
const wsHeaderString = ref('')
const httpHeaderString = ref('')

const jsonValidator = (value: string) => {
  if (!value) return true
  try {
    JSON.parse(value)
    return true
  } catch (e) {
    return '无效的JSON格式'
  }
}

const proxyTypes = [
  'ss',
  'ssr',
  'vmess',
  'vless',
  'trojan',
  'http',
  'snell',
  'tuic',
  'hysteria',
  'hysteria2'
]

// Initialize optional nested objects if they don't exist
const initNestedObjects = () => {
  if (!proxy.value.smux) {
    proxy.value.smux = { enabled: false, protocol: 'h2mux' }
  }
  if (!proxy.value.smux['brutal-opts']) {
    proxy.value.smux['brutal-opts'] = { enabled: false }
  }
  if (!proxy.value['ws-opts']) {
    proxy.value['ws-opts'] = {
      path: '/',
      'v2ray-http-upgrade': false,
      'v2ray-http-upgrade-fast-open': false
    }
  }
  if (!proxy.value['http-opts']) {
    proxy.value['http-opts'] = { path: ['/'], method: 'GET' }
  }
  if (!proxy.value['h2-opts']) {
    proxy.value['h2-opts'] = { path: '/', host: [] }
  }
  if (!proxy.value['grpc-opts']) {
    proxy.value['grpc-opts'] = { 'grpc-service-name': '' }
  }

  if (!proxy.value.alpn) {
    proxy.value.alpn = []
  }

  // Initialize header strings from existing data
  if (proxy.value['ws-opts']?.headers) {
    wsHeaderString.value = JSON.stringify(proxy.value['ws-opts'].headers, null, 2)
  }
  if (proxy.value['http-opts']?.headers) {
    httpHeaderString.value = JSON.stringify(proxy.value['http-opts'].headers, null, 2)
  }
}

initNestedObjects()

// Parse header strings back to objects before saving
const parseHeaders = () => {
  if (proxy.value.network === 'ws') {
    try {
      if (proxy.value['ws-opts']) {
        proxy.value['ws-opts'].headers = JSON.parse(wsHeaderString.value || '{}')
      }
    } catch (e) {
      console.error('Invalid JSON format for ws headers:', e)
      if (proxy.value['ws-opts']) {
        proxy.value['ws-opts'].headers = {}
      }
    }
  }
  if (proxy.value.network === 'http') {
    try {
      if (proxy.value['http-opts']) {
        proxy.value['http-opts'].headers = JSON.parse(httpHeaderString.value || '{}')
      }
    } catch (e) {
      console.error('Invalid JSON format for http headers:', e)
      if (proxy.value['http-opts']) {
        proxy.value['http-opts'].headers = {}
      }
    }
  }
}

const handleSave = async () => {
  const { valid } = await proxyForm.value.validate()
  if (valid) {
    parseHeaders()

    // Create a clean proxy object to emit
    const finalProxy: Proxy = { ...proxy.value }

    // Clean up unused transport options
    if (finalProxy.network !== 'ws') delete finalProxy['ws-opts']
    if (finalProxy.network !== 'http') delete finalProxy['http-opts']
    if (finalProxy.network !== 'h2') delete finalProxy['h2-opts']
    if (finalProxy.network !== 'grpc') delete finalProxy['grpc-opts']

    // Clean up smux if disabled
    if (!finalProxy.smux?.enabled) {
      delete finalProxy.smux
    } else if (!finalProxy.smux['brutal-opts']?.enabled) {
      delete finalProxy.smux['brutal-opts']
    }

    // Clean up unused TLS options
    if (!finalProxy.tls) {
      delete finalProxy.servername
      delete finalProxy.fingerprint
      delete finalProxy.alpn
      delete finalProxy['skip-cert-verify']
      delete finalProxy['client-fingerprint']
      delete finalProxy.sni
    } else {
      // If TLS is enabled, clean up the one that is not used
      if (['vmess', 'vless'].includes(finalProxy.type)) {
        delete finalProxy.sni
      } else {
        delete finalProxy.servername
      }
      if (!['vmess', 'vless', 'trojan'].includes(finalProxy.type)) {
        delete finalProxy['client-fingerprint']
      }
    }
    await saveProxy(finalProxy)
  }
}

const saveProxy = async (proxy: Proxy) => {
  loading.value = true
  try {
    const requestData = {
      source: props.proxyData?.meta.source,
      proxy: proxy
    }
    const name = encodeURIComponent(props.proxyData.data.name)
    const result = await props.api.patch(`/plugin/ClashRuleProvider/proxies/${name}`, requestData)
    if (!result.success) {
      emit('show-error', '保存出站代理失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '保存出站代理失败',
        color: 'error'
      })
      return
    }
    emit('refresh')
    emit('show-snackbar', {
      show: true,
      message: '出站代理更新成功',
      color: 'success'
    })
    emit('close')
  } catch (err: unknown) {
    if (err instanceof Error) emit('show-error', '保存 Proxy 失败: ' + (err.message || '未知错误'))
    emit('show-snackbar', {
      show: true,
      message: '保存代理失败',
      color: 'error'
    })
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <v-dialog max-width="50rem" persistent>
    <v-card>
      <v-card-title>编辑代理</v-card-title>
      <v-card-text class="pa-2">
        <v-form ref="proxyForm" @submit.prevent="handleSave">
          <v-tabs v-model="tab" background-color="primary" dark grow>
            <v-tab value="general">通用</v-tab>
            <v-tab value="tls">TLS</v-tab>
            <v-tab value="transport">传输层</v-tab>
          </v-tabs>
          <v-window v-model="tab" class="pt-4">
            <!-- General Tab -->
            <v-window-item value="general">
              <v-container fluid>
                <v-row dense>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="proxy.name"
                      disabled
                      label="名称 (name)"
                      :rules="[(v) => !!v || '名称不能为空']"
                      hint="代理名称"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="proxy.type"
                      label="类型 (type)"
                      :items="proxyTypes"
                      :rules="[(v) => !!v || '类型不能为空']"
                      hint="代理协议类型"
                      variant="outlined"
                    ></v-select>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="proxy.server"
                      label="服务器 (server)"
                      :rules="[(v) => !!v || '服务器地址不能为空']"
                      hint="代理服务器地址 (域名/IP)"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="proxy.port"
                      label="端口 (port)"
                      type="number"
                      :rules="[(v) => !!v || '端口不能为空']"
                      hint="代理服务器端口"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="proxy['ip-version']"
                      label="IP版本 (ip-version)"
                      :items="['dual', 'ipv4', 'ipv6', 'ipv4-prefer', 'ipv6-prefer']"
                      hint="出站使用的IP版本"
                      clearable
                      variant="outlined"
                    ></v-select>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="proxy['interface-name']"
                      label="网络接口 (interface-name)"
                      hint="指定出站网络接口"
                      clearable
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="proxy['routing-mark']"
                      label="路由标记 (routing-mark)"
                      type="number"
                      hint="为出站连接设置路由标记"
                      clearable
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="proxy['dialer-proxy']"
                      label="拨号代理 (dialer-proxy)"
                      hint="指定当前代理通过哪个代理建立连接"
                      clearable
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4" sm="4">
                    <v-switch
                      v-model="proxy.udp"
                      label="UDP"
                      hint="是否允许UDP"
                      inset
                      color="primary"
                    ></v-switch>
                  </v-col>
                  <v-col cols="4" sm="4">
                    <v-switch
                      v-model="proxy.tfo"
                      label="TFO"
                      hint="启用 TCP Fast Open"
                      inset
                      color="primary"
                    ></v-switch>
                  </v-col>
                  <v-col cols="4" sm="4">
                    <v-switch
                      v-model="proxy.mptcp"
                      label="MPTCP"
                      hint="启用 Multi-Path TCP"
                      inset
                      color="primary"
                    ></v-switch>
                  </v-col>
                </v-row>
              </v-container>
            </v-window-item>

            <!-- TLS Tab -->
            <v-window-item value="tls">
              <v-container fluid>
                <v-row dense>
                  <v-col cols="12">
                    <v-switch v-model="proxy.tls" label="启用 TLS" inset color="primary"></v-switch>
                  </v-col>
                </v-row>
                <v-expand-transition>
                  <div v-if="proxy.tls">
                    <v-row dense>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-if="['vmess', 'vless'].includes(proxy.type)"
                          v-model="proxy.servername"
                          label="服务器名称 (servername)"
                          hint="TLS服务器名称(SNI)"
                          clearable
                          persistent-hint
                          variant="outlined"
                        ></v-text-field>
                        <v-text-field
                          v-else
                          v-model="proxy.sni"
                          label="SNI"
                          hint="TLS服务器名称(SNI)"
                          clearable
                          persistent-hint
                          variant="outlined"
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="proxy.fingerprint"
                          label="指纹 (fingerprint)"
                          hint="证书指纹"
                          clearable
                          persistent-hint
                          variant="outlined"
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12">
                        <v-combobox
                          v-model="proxy.alpn"
                          label="ALPN"
                          hint="应用层协议协商"
                          multiple
                          chips
                          clearable
                          deletable-chips
                          persistent-hint
                          variant="outlined"
                        ></v-combobox>
                      </v-col>
                      <v-col
                        v-if="['vmess', 'vless', 'trojan'].includes(proxy.type)"
                        cols="12"
                        md="6"
                      >
                        <v-select
                          v-model="proxy['client-fingerprint']"
                          label="客户端指纹 (client-fingerprint)"
                          :items="[
                            'chrome',
                            'firefox',
                            'safari',
                            'ios',
                            'android',
                            'edge',
                            '360',
                            'qq',
                            'random'
                          ]"
                          hint="uTLS客户端指紋"
                          clearable
                          persistent-hint
                          variant="outlined"
                        ></v-select>
                      </v-col>
                      <v-col cols="12" md="6" class="d-flex align-center">
                        <v-switch
                          v-model="proxy['skip-cert-verify']"
                          label="跳过证书验证"
                          inset
                          persistent-hint
                          color="primary"
                        ></v-switch>
                      </v-col>
                    </v-row>
                  </div>
                </v-expand-transition>
              </v-container>
            </v-window-item>

            <!-- Transport Tab -->
            <v-window-item value="transport">
              <v-container fluid>
                <v-row>
                  <v-col cols="12">
                    <v-select
                      v-model="proxy.network"
                      label="网络 (network)"
                      :items="['http', 'h2', 'grpc', 'ws']"
                      hint="传输层协议"
                      clearable
                      persistent-hint
                      variant="outlined"
                    ></v-select>
                  </v-col>
                </v-row>
                <!-- ws-opts -->
                <v-expand-transition>
                  <div v-if="proxy.network === 'ws' && proxy['ws-opts']" class="mt-2">
                    <v-card variant="tonal">
                      <v-card-title class="text-subtitle-1 py-2">WebSocket 选项</v-card-title>
                      <v-card-text>
                        <v-row>
                          <v-col cols="12" md="6">
                            <v-switch
                              v-model="proxy['ws-opts']['v2ray-http-upgrade']"
                              label="v2ray-http-upgrade"
                              hint="启用 http upgrade"
                              inset
                              color="primary"
                            ></v-switch>
                          </v-col>
                          <v-col cols="12" md="6">
                            <v-switch
                              v-model="proxy['ws-opts']['v2ray-http-upgrade-fast-open']"
                              label="v2ray-http-upgrade-fast-open"
                              hint="启用 http upgrade 的 fast open"
                              inset
                              color="primary"
                            ></v-switch>
                          </v-col>
                        </v-row>
                        <v-text-field
                          v-model="proxy['ws-opts'].path"
                          label="路径 (path)"
                          hint="WebSocket请求路径"
                          variant="outlined"
                          class="mb-2"
                        ></v-text-field>
                        <v-text-field
                          v-model.number="proxy['ws-opts']['max-early-data']"
                          label="max-early-data"
                          type="number"
                          hint="Early Data 首包长度阈值"
                          variant="outlined"
                          class="mb-2"
                          clearable
                        ></v-text-field>
                        <v-text-field
                          v-model="proxy['ws-opts']['early-data-header-name']"
                          label="early-data-header-name"
                          variant="outlined"
                          class="mb-2"
                          clearable
                        ></v-text-field>
                        <v-textarea
                          v-model="wsHeaderString"
                          label="请求头 (headers)"
                          hint='请输入JSON格式字符串, 例如: {"Host":"example.com"}'
                          variant="outlined"
                          rows="3"
                          :rules="[jsonValidator]"
                        ></v-textarea>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
                <!-- http-opts -->
                <v-expand-transition>
                  <div v-if="proxy.network === 'http' && proxy['http-opts']" class="mt-2">
                    <v-card variant="tonal">
                      <v-card-title class="text-subtitle-1 py-2">HTTP 选项</v-card-title>
                      <v-card-text>
                        <v-text-field
                          v-model="proxy['http-opts'].method"
                          label="方法 (method)"
                          hint="HTTP请求方法"
                          variant="outlined"
                          class="mb-2"
                        ></v-text-field>
                        <v-combobox
                          v-model="proxy['http-opts'].path"
                          label="路径 (path)"
                          hint="HTTP请求路径"
                          multiple
                          chips
                          clearable
                          deletable-chips
                          variant="outlined"
                          class="mb-2"
                        ></v-combobox>
                        <v-textarea
                          v-model="httpHeaderString"
                          label="请求头 (headers)"
                          hint='请输入JSON格式字符串, 例如: {"Host":"example.com"}'
                          variant="outlined"
                          rows="3"
                          :rules="[jsonValidator]"
                        ></v-textarea>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
                <!-- h2-opts -->
                <v-expand-transition>
                  <div v-if="proxy.network === 'h2' && proxy['h2-opts']" class="mt-2">
                    <v-card variant="tonal">
                      <v-card-title class="text-subtitle-1 py-2">H2 选项</v-card-title>
                      <v-card-text>
                        <v-text-field
                          v-model="proxy['h2-opts'].path"
                          label="路径 (path)"
                          hint="H2请求路径"
                          variant="outlined"
                          class="mb-2"
                        ></v-text-field>
                        <v-combobox
                          v-model="proxy['h2-opts'].host"
                          label="主机 (host)"
                          hint="主机域名列表"
                          multiple
                          chips
                          clearable
                          deletable-chips
                          variant="outlined"
                        ></v-combobox>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
                <!-- grpc-opts -->
                <v-expand-transition>
                  <div v-if="proxy.network === 'grpc' && proxy['grpc-opts']" class="mt-2">
                    <v-card variant="tonal">
                      <v-card-title class="text-subtitle-1 py-2">gRPC 选项</v-card-title>
                      <v-card-text>
                        <v-text-field
                          v-model="proxy['grpc-opts']['grpc-service-name']"
                          label="服务名称 (grpc-service-name)"
                          hint="gRPC服务名称"
                          variant="outlined"
                        ></v-text-field>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
                <!-- smux-opts -->
                <v-expand-transition>
                  <div
                    v-if="(!proxy.network || proxy.network === 'tcp') && proxy.smux"
                    class="mt-2"
                  >
                    <v-card variant="tonal">
                      <v-card-title class="text-subtitle-1 py-2">Smux 选项</v-card-title>
                      <v-card-text>
                        <v-row dense>
                          <v-col cols="12">
                            <v-switch
                              v-model="proxy.smux.enabled"
                              label="启用 Smux"
                              inset
                              color="primary"
                            ></v-switch>
                          </v-col>
                        </v-row>
                        <v-expand-transition>
                          <div v-if="proxy.smux.enabled && proxy.smux['brutal-opts']">
                            <v-row dense>
                              <v-col cols="12" md="6">
                                <v-select
                                  v-model="proxy.smux.protocol"
                                  label="协议 (protocol)"
                                  :items="['smux', 'yamux', 'h2mux']"
                                  hint="Smux协议类型"
                                  variant="outlined"
                                ></v-select>
                              </v-col>
                              <v-col cols="12" md="6">
                                <v-text-field
                                  v-model.number="proxy.smux['max-connections']"
                                  label="最大连接数 (max-connections)"
                                  type="number"
                                  hint="最大复用连接数"
                                  clearable
                                  variant="outlined"
                                ></v-text-field>
                              </v-col>
                              <v-col cols="12" md="6">
                                <v-text-field
                                  v-model.number="proxy.smux['min-streams']"
                                  label="最小流数 (min-streams)"
                                  type="number"
                                  hint="每个连接的最小流数"
                                  clearable
                                  variant="outlined"
                                ></v-text-field>
                              </v-col>
                              <v-col cols="12" md="6">
                                <v-text-field
                                  v-model.number="proxy.smux['max-streams']"
                                  label="最大流数 (max-streams)"
                                  type="number"
                                  hint="每个连接的最大流数"
                                  clearable
                                  variant="outlined"
                                ></v-text-field>
                              </v-col>
                              <v-col cols="4" sm="4">
                                <v-switch
                                  v-model="proxy.smux.padding"
                                  label="Padding"
                                  hint="启用Padding"
                                  inset
                                  color="primary"
                                ></v-switch>
                              </v-col>
                              <v-col cols="4" sm="4">
                                <v-switch
                                  v-model="proxy.smux.statistic"
                                  label="Statistic"
                                  hint="启用统计"
                                  inset
                                  color="primary"
                                ></v-switch>
                              </v-col>
                              <v-col cols="4" sm="4">
                                <v-switch
                                  v-model="proxy.smux['only-tcp']"
                                  label="Only TCP"
                                  hint="仅用于TCP"
                                  inset
                                  color="primary"
                                ></v-switch>
                              </v-col>
                              <v-col cols="12">
                                <v-switch
                                  v-model="proxy.smux['brutal-opts'].enabled"
                                  label="启用 Brutal 优化"
                                  inset
                                  color="primary"
                                ></v-switch>
                              </v-col>
                            </v-row>
                            <v-expand-transition>
                              <v-row v-if="proxy.smux['brutal-opts'].enabled" dense>
                                <v-col cols="12" md="6">
                                  <v-text-field
                                    v-model.number="proxy.smux['brutal-opts'].up"
                                    label="上行带宽 (up)"
                                    hint="上行带宽, 默认以 Mbps 为单位"
                                    clearable
                                    variant="outlined"
                                  ></v-text-field>
                                </v-col>
                                <v-col cols="12" md="6">
                                  <v-text-field
                                    v-model.number="proxy.smux['brutal-opts'].down"
                                    label="下行带宽 (down)"
                                    hint="下行带宽, 默认以 Mbps 为单位"
                                    clearable
                                    variant="outlined"
                                  ></v-text-field>
                                </v-col>
                              </v-row>
                            </v-expand-transition>
                          </div>
                        </v-expand-transition>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
              </v-container>
            </v-window-item>
          </v-window>
        </v-form>
        <v-alert type="info" variant="tonal">
          参考<a
            href="https://wiki.metacubex.one/config/proxies/"
            target="_blank"
            style="text-decoration: underline"
            >Docs</a
          >, 覆写某些选项可能导致代理不可用。
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="emit('close')">取消</v-btn>
        <v-btn color="primary" :loading="loading" :disabled="loading" @click="handleSave"
          >保存</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
