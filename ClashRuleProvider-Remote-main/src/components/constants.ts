import { Proxy, ProxyGroup, RuleData, HostData, RuleProvider, Metadata } from '@/components/types'

export const itemsPerPageOptions = [
  { title: '5', value: 5 },
  { title: '10', value: 10 },
  { title: '20', value: 20 },
  { title: '50', value: 50 },
  { title: 'All', value: -1 }
]
export const defaultMetadata: Metadata = {
  source: 'Manual',
  disabled: false,
  invisible_to: [],
  remark: '',
  time_modified: 0,
  patched: false
}

export const defaultRule: RuleData = {
  type: 'DOMAIN-SUFFIX',
  payload: '',
  action: 'DIRECT',
  priority: 0,
  meta: { ...defaultMetadata },
  rule_string: 'DOMAIN-SUFFIX,,DIRECT'
}

export const defaultProxy: Proxy = {
  name: '',
  type: 'ss',
  server: '',
  port: 443,
  udp: false,
  tfo: false,
  mptcp: false,
  tls: false,
  'skip-cert-verify': false,
  alpn: [],
  'ws-opts': {
    path: '/',
    headers: {},
    'v2ray-http-upgrade': false,
    'v2ray-http-upgrade-fast-open': false
  },
  'http-opts': { method: 'GET', path: ['/'], headers: {} },
  'h2-opts': { host: [], path: '/' },
  'grpc-opts': { 'grpc-service-name': '' },
  smux: {
    enabled: false,
    protocol: 'h2mux',
    padding: false,
    statistic: false,
    'only-tcp': false,
    'brutal-opts': {
      enabled: false
    }
  },
  rescind: false
}

export const defaultProxyGroup: ProxyGroup = {
  name: '',
  type: 'select',
  url: 'https://www.gstatic.com/generate_204',
  lazy: true,
  'disable-udp': false,
  'include-all': false,
  'include-all-proxies': false,
  'include-all-providers': false,
  'expected-status': '*',
  hidden: false,
  'max-failed-times': 5
}

export const defaultHost: HostData = {
  domain: '',
  value: [],
  using_cloudflare: false,
  meta: { ...defaultMetadata }
}

export const defaultRuleProvider: RuleProvider = {
  type: 'http',
  interval: 600,
  behavior: 'classical',
  format: 'yaml',
  'size-limit': 0,
  payload: []
}
