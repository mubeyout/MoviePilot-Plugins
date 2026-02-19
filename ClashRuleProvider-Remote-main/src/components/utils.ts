import { RuleData, SubscriptionInfo } from '@/components/types'

export const isValidUrl = (urlString: string) => {
  if (!urlString) return false
  try {
    const url = new URL(urlString)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch (e) {
    return false
  }
}

function isValidIP(ip: string) {
  const ipv4Regex = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/
  const ipv6Regex =
    /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(([0-9a-fA-F]{1,4}:){1,7}|:):([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})$/
  return ipv4Regex.test(ip) || ipv6Regex.test(ip)
}

export function validateIPs(ips: string[]) {
  if (ips.length === 0) {
    return `至少需要一个 IP 地址`
  }
  for (const ip of ips) {
    if (!isValidIP(ip)) {
      return `无效的 IP 地址: ${ip}`
    }
  }
  return true
}

// 根据流量百分比获取颜色
export function getUsageColor(percentage: number) {
  return percentage > 90 ? 'error' : percentage > 70 ? 'warning' : 'success'
}

export function getBehaviorColor(action: string) {
  const colors: Record<string, string> = {
    classical: 'success',
    domain: 'error',
    ipcidr: 'error'
  }
  return colors[action] || 'primary'
}

export function getFormatColor(action: string) {
  const colors: Record<string, string> = {
    yaml: 'success',
    text: 'warning',
    mrs: 'info'
  }
  return colors[action] || 'secondary'
}

export function getRuleTypeColor(type: string) {
  const colors: Record<string, string> = {
    DOMAIN: 'primary',
    'DOMAIN-SUFFIX': 'primary',
    'DOMAIN-KEYWORD': 'primary',
    'DOMAIN-REGEX': 'primary',
    'DOMAIN-WILDCARD': 'primary',
    GEOSITE: 'info',
    GEOIP: 'info',
    'IP-CIDR': 'warning',
    'IP-CIDR6': 'warning',
    'IP-SUFFIX': 'warning',
    'IP-ASN': 'warning',
    'SRC-GEOIP': 'info',
    'SRC-IP-ASN': 'warning',
    'SRC-IP-CIDR': 'warning',
    'SRC-IP-SUFFIX': 'warning',
    'DST-PORT': 'success',
    'SRC-PORT': 'success',
    'IN-PORT': 'success',
    'IN-TYPE': 'success',
    'IN-USER': 'success',
    'IN-NAME': 'success',
    'PROCESS-PATH': 'error',
    'PROCESS-PATH-REGEX': 'error',
    'PROCESS-NAME': 'error',
    'PROCESS-NAME-REGEX': 'error',
    UID: 'secondary',
    NETWORK: 'secondary',
    DSCP: 'secondary',
    'RULE-SET': 'deep-purple',
    AND: 'deep-orange',
    OR: 'deep-orange',
    NOT: 'deep-orange',
    'SUB-RULE': 'deep-orange',
    MATCH: 'teal'
  }
  return colors[type] || 'grey'
}

export function getSourceColor(source: string) {
  const colors: Record<string, string> = {
    Auto: 'success',
    Manual: 'info'
  }
  return colors[source] || 'primary'
}

export function getActionColor(action: string) {
  const colors: Record<string, string> = {
    DIRECT: 'success',
    REJECT: 'error',
    'REJECT-DROP': 'error',
    PASS: 'warning',
    COMPATIBLE: 'info'
  }
  return colors[action] || 'primary'
}

export function getProxyGroupTypeColor(action: string) {
  const colors: Record<string, string> = {
    'url-test': 'success',
    fallback: 'error',
    'load-balance': 'primary',
    select: 'info'
  }
  return colors[action] || 'warning'
}

export function getProxyColor(action: string) {
  const colors: Record<string, string> = {
    ss: 'success',
    ssr: 'success',
    trojan: 'error',
    vmess: 'primary',
    vless: 'primary',
    hysteria: 'info',
    hysteria2: 'info',
    anytls: 'warning'
  }
  return colors[action] || 'secondary'
}

export function getBoolColor(value: boolean) {
  if (value) {
    return 'primary'
  }
  return 'success'
}

export function isSystemRule(rule: RuleData) {
  return rule.meta.source?.startsWith('Auto')
}

export function isManual(source: string) {
  return source === 'Manual'
}

export function isInvalid(source: string) {
  return source === 'Invalid'
}

export function isRegion(source: string) {
  return source === 'Auto'
}

export function isTemplate(source: string) {
  return source === 'Template'
}

export function pageTitle(itemPerPageValue: number) {
  if (itemPerPageValue < 0) {
    return '♾️'
  }
  return `${itemPerPageValue}`
}

// 格式化字节为易读单位（如 1.5 GB）
export function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 在工具函数中添加时间戳转换
export function formatTimestamp(timestamp: number | null | undefined) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp * 1000) // 注意：JS时间戳是毫秒，需乘以1000
  return date.toLocaleDateString('zh-CN') // 或使用其他格式如 date.toISOString().split('T')[0]
}

export function timestampToDate(timestamp: number | null | undefined) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp * 1000) // 注意：JS时间戳是毫秒，需乘以1000
  return date.toLocaleString('zh-CN', {
    // 'en-GB' 表示使用英国格式（YYYY-MM-DD HH:mm:ss）
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false // 24小时制
  })
}

// 更新过期时间颜色判断（基于时间戳）
export function getExpireColor(timestamp: number | null | undefined) {
  if (!timestamp) return 'grey'
  const secondsLeft = timestamp - Math.floor(Date.now() / 1000)
  const daysLeft = secondsLeft / 86400
  return daysLeft < 7 ? 'error' : daysLeft < 30 ? 'warning' : 'success'
}

export function extractDomain(url: string) {
  try {
    const hostname = new URL(url).hostname
    // 按点分割
    const parts = hostname.split('.')
    // 如果是 IPv4/IPv6，直接返回
    if (/^\d+\.\d+\.\d+\.\d+$/.test(hostname) || hostname.includes(':')) {
      return hostname
    }
    // 只有一段的直接返回
    if (parts.length <= 2) {
      return hostname
    }
    // 返回最后两段（example.com）
    return parts.slice(-2).join('.')
  } catch {
    return url
  }
}

// 计算使用百分比
export function getUsedPercentageFloor(data: SubscriptionInfo): number {
  const used = data.upload + data.download
  return data.total > 0 ? Math.floor((used / data.total) * 100) : 0
}
