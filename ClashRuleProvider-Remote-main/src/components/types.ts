export type RuleSetType = 'top' | 'ruleset'
export type ProxyType =
  | 'ss'
  | 'ssr'
  | 'vmess'
  | 'vless'
  | 'trojan'
  | 'http'
  | 'snell'
  | 'tuic'
  | 'hysteria'
  | 'hysteria2'
  | 'direct'
  | 'dns'
  | 'mieru'
  | 'anytls'
  | 'wireguard'
  | 'ssh'
  | 'socks5'

export interface Metadata {
  source: string
  disabled: boolean
  invisible_to: string[]
  remark: string
  time_modified: number
  patched?: boolean
}

// 基础接口，包含所有代理组类型共有的通用字段
interface ProxyGroupBase {
  /** The name of the proxy group. */
  name: string

  /** References to outbound proxies or other proxy groups. */
  proxies?: string[]

  /** References to proxy provider sets. */
  use?: string[]

  // Health check fields
  /** Health check test address. */
  url?: string

  /** Health check interval in seconds. */
  interval?: number

  /** If not selected, no health checks are performed. */
  lazy?: boolean

  /** Health check timeout in milliseconds. */
  timeout?: number

  /** Maximum number of failures before a forced health check. */
  'max-failed-times'?: number

  /** Expected HTTP response status code for health checks. */
  'expected-status'?: string

  // Network and routing fields
  /** Disables UDP for this proxy group. */
  'disable-udp'?: boolean

  /** DEPRECATED. Specifies the outbound interface. */
  'interface-name'?: string

  /** DEPRECATED. The routing mark for outbound connections. */
  'routing-mark'?: number

  // Dynamic proxy inclusion
  /** Includes all outbound proxies and proxy sets. */
  'include-all'?: boolean

  /** Includes all outbound proxies. */
  'include-all-proxies'?: boolean

  /** Includes all proxy provider sets. */
  'include-all-providers'?: boolean

  // Filtering
  /** Regex to filter nodes from providers. */
  filter?: string

  /** Regex to exclude nodes. */
  'exclude-filter'?: string

  /** Exclude nodes by adapter type, separated by '|'. */
  'exclude-type'?: string

  // UI fields
  /** Hides the proxy group in the API. */
  hidden?: boolean

  /** Icon string for the proxy group, for UI use. */
  icon?: string
}

// 选择组
interface SelectGroup extends ProxyGroupBase {
  type: 'select'
}

// 中继组
interface RelayGroup extends ProxyGroupBase {
  type: 'relay'
}

// 故障转移组
interface FallbackGroup extends ProxyGroupBase {
  type: 'fallback'
}

// URL测试组
interface UrlTestGroup extends ProxyGroupBase {
  type: 'url-test'

  /** proxies switch tolerance, measured in milliseconds (ms). */
  tolerance?: number
}

// 负载均衡组
interface LoadBalanceGroup extends ProxyGroupBase {
  type: 'load-balance'

  /** Load balancing strategy. */
  strategy?: 'round-robin' | 'consistent-hashing' | 'sticky-sessions'
}

// 智能组
interface SmartGroup extends ProxyGroupBase {
  type: 'smart'

  /** Use LightGBM model predict weight. */
  uselightgbm: boolean

  /** Collect datas for model training. */
  collectdata: boolean

  /** <1 means lower priority, >1 means higher priority, the default is 1, pattern support regex and string. */
  'policy-priority'?: string

  /** Load balancing strategy. */
  strategy?: 'round-robin' | 'sticky-sessions'

  /** Data acquisition rate. */
  'sample-rate'?: number
}

// 联合类型：所有代理组类型的联合
export type ProxyGroup =
  | SelectGroup
  | RelayGroup
  | FallbackGroup
  | UrlTestGroup
  | LoadBalanceGroup
  | SmartGroup

export interface RuleProvider {
  type: 'http' | 'inline' | 'file'
  url?: string
  path?: string
  interval?: number
  proxy?: string
  behavior?: 'domain' | 'ipcidr' | 'classical'
  format: 'yaml' | 'text' | 'mrs'
  'size-limit': number
  payload?: string[]
}

export interface RuleProviderData {
  name: string
  data: RuleProvider
  meta: Metadata
}

export interface HealthCheck {
  enable: boolean
  url: string
  interval?: number
  timeout?: number
  lazy?: boolean
  'expected-status'?: string
}

export interface OverrideProxyName {
  pattern?: string
  target: string
}

export interface Override {
  tfo?: boolean
  mptcp?: boolean
  udp?: boolean
  'udp-over-tcp'?: boolean
  up?: string
  'dialer-proxy'?: string
  'skip-cert-verify'?: boolean
  'interface-name'?: string
  'routing-mark'?: number
  'ip-version'?: string
  'additional-prefix'?: string
  'additional-suffix'?: string
  'proxy-name'?: OverrideProxyName[]
}

export interface ProxyProvider {
  type: 'http' | 'file' | 'inline'
  path?: string
  url?: string
  proxy?: string
  interval?: number
  filter?: string
  'exclude-filter'?: string
  'exclude-type'?: string
  'dialer-proxy'?: string
  'size-limit'?: number
  payload?: any[]
  'health-check'?: HealthCheck
  override?: Override
  header?: Record<string, string[]>
}

export interface ProxyProviderData {
  name: string
  data: ProxyProvider
  meta: Metadata
}

export interface RuleData {
  priority: number
  rule_string: string
  type: string
  payload?: string
  action: string
  additional_params?: 'no-resolve' | 'src'
  conditions?: string[]
  condition?: string
  meta: Metadata
}

export interface Smux {
  enabled: boolean
  protocol: 'smux' | 'yamux' | 'h2mux'
  'max-connections'?: number
  'min-streams'?: number
  'max-streams'?: number
  statistic?: boolean
  'only-tcp'?: boolean
  padding?: boolean
  'brutal-opts'?: {
    enabled: boolean
    up?: number
    down?: number
  }
}

export interface WsOpts {
  path: string
  headers?: Record<string, string>
  'max-early-data'?: number
  'early-data-header-name'?: string
  'v2ray-http-upgrade'?: boolean
  'v2ray-http-upgrade-fast-open'?: boolean
}

export interface HttpOpts {
  method?: string
  path: string[]
  headers?: Record<string, string | string[]>
}

export interface H2Opts {
  host: string[]
  path: string
}

export interface GrpcOpts {
  'grpc-service-name': string
}

export interface Proxy {
  name: string
  type: ProxyType
  server: string
  port: number
  uuid?: string
  password?: string
  cipher?: string
  alterId?: number
  udp?: boolean
  tfo?: boolean
  mptcp?: boolean
  tls?: boolean
  sni?: string
  servername?: string
  alpn?: string[]
  fingerprint?: string
  'skip-cert-verify'?: boolean
  'client-fingerprint'?: string
  network?: 'tcp' | 'http' | 'h2' | 'grpc' | 'ws' | 'kcp'
  'ws-opts'?: WsOpts
  'http-opts'?: HttpOpts
  'h2-opts'?: H2Opts
  'grpc-opts'?: GrpcOpts
  'ip-version'?: 'dual' | 'ipv4' | 'ipv6' | 'ipv4-prefer' | 'ipv6-prefer'
  'interface-name'?: string
  'routing-mark'?: number
  'dialer-proxy'?: string
  smux?: Smux
  [key: string]: any // To support other proxy-specific fields without defining each one
}

export interface ProxyData {
  data: Proxy
  name: string
  raw?: string | Record<string, any> | null
  v2ray_link?: string | null
  meta: Metadata
}

export interface ProxyGroupData {
  data: ProxyGroup
  meta: Metadata
  name: string
}

interface DataUsage {
  upload: number
  download: number
  total: number
  expire: number
}

export interface SubscriptionInfo extends DataUsage {
  last_update: number
  proxy_num: number
  enabled: boolean
}

export interface HostData {
  domain: string
  value: string[]
  using_cloudflare: boolean
  meta: Metadata
}

export interface GeoRules {
  geoip: string[]
  geosite: string[]
}

export interface ClashApi {
  url: string
  secret: string
}

export interface SubscriptionConfig {
  url: string
  rules?: boolean
  'rule-providers'?: boolean
  proxies?: boolean
  'proxy-groups'?: boolean
  'proxy-providers'?: boolean
}

export interface PluginConfig {
  enabled: boolean
  proxy: boolean
  notify: boolean
  subscriptions_config: SubscriptionConfig[]
  movie_pilot_url: string
  cron_string: string
  timeout: number
  retry_times: number
  filter_keywords: string[]
  auto_update_subscriptions: boolean
  ruleset_prefix: string
  acl4ssr_prefix: string
  group_by_region: boolean
  group_by_country: boolean
  refresh_delay: number
  enable_acl4ssr: boolean
  dashboard_components: string[]
  clash_template: string
  hint_geo_dat: boolean
  best_cf_ip: string[]
  apikey?: string | null
  clash_dashboards: ClashApi[]
  active_dashboard?: number | null
  identifiers: string[]
  cache_ttl: number
}
