<script setup lang="ts">
import { reactive, onMounted, onUnmounted, ref } from 'vue'
import Chart from 'chart.js/auto'
import { formatBytes } from '@/components/utils'

const props = defineProps({
  config: {
    type: Object,
    default: () => ({})
  },
  allowRefresh: {
    type: Boolean,
    default: true
  }
})

const uploadSpeed = ref(0)
const downloadSpeed = ref(0)
const uploaded = ref(0)
const downloaded = ref(0)
const activeConnections = ref(0)
const coreUsage = ref(0)

const maxPoints = 150
const uploadHistory = ref(Array(maxPoints).fill(0))
const downloadHistory = ref(Array(maxPoints).fill(0))
const memoryHistory = ref(Array(maxPoints).fill(0))
const speedLabels = ref<string[]>([])
const memoryLabels = ref<string[]>([])

const speedChartCanvas = ref<HTMLCanvasElement | null>(null)
const memoryChartCanvas = ref<HTMLCanvasElement | null>(null)

let chartInstance: Chart | null = null
let memChartInstance: Chart | null = null
let evtSource: EventSource | null = null
let connectionsEvtSource: EventSource | null = null

const defaultConfig = {
  title: 'Clash Info',
  clash_available: false,
  secret: ''
}

const componentConfig: any = reactive({ ...defaultConfig })

function formatTime(date: Date) {
  return date.toTimeString().split(' ')[0] // 只取 HH:mm:ss 部分
}

// 初始化 labels，从 maxPoints 秒前开始
function initializeTimeLabels() {
  const now = new Date()
  const labels = []
  for (let i = maxPoints - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 1000)
    labels.push(formatTime(time))
  }
  return labels
}

function updateChart() {
  if (!chartInstance) return
  if (uploadHistory.value.length > maxPoints) {
    uploadHistory.value.shift()
    downloadHistory.value.shift()
    speedLabels.value.shift()
  }
  // chartInstance.data.labels = uploadHistory.value.map((_, i) => i)
  chartInstance.data.datasets[0].data = [...uploadHistory.value]
  chartInstance.data.datasets[1].data = [...downloadHistory.value]
  chartInstance.data.labels = [...speedLabels.value]
  chartInstance.update()
}

function updateMemoryChart() {
  if (!memChartInstance) return
  if (memoryHistory.value.length > maxPoints) {
    memoryHistory.value.shift()
    memoryLabels.value.shift()
  }
  // memChartInstance.data.labels = memoryHistory.value.map((_, i) => i)
  memChartInstance.data.datasets[0].data = [...memoryHistory.value]
  memChartInstance.data.labels = [...memoryLabels.value]
  memChartInstance.update()
}

function getCurrentTimeLabel() {
  const now = new Date()
  // return now.toLocaleTimeString()
  return formatTime(now)
}

onMounted(() => {
  if (props.config?.attrs) {
    Object.keys(props.config.attrs).forEach((key) => {
      if (key in componentConfig) {
        componentConfig[key] = props.config.attrs[key]
      }
    })
  }

  const ctx = speedChartCanvas.value?.getContext('2d')
  const memCtx = memoryChartCanvas.value?.getContext('2d')
  if (!ctx || !memCtx) {
    return
  }
  speedLabels.value = initializeTimeLabels()
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array(maxPoints).fill(''),
      datasets: [
        {
          label: '上传速度',
          data: [...uploadHistory.value],
          borderColor: 'rgba(255, 206, 86, 1)',
          borderWidth: 0.75,
          backgroundColor: 'rgba(255, 206, 86, 0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 0
        },
        {
          label: '下载速度',
          data: [...downloadHistory.value],
          borderWidth: 0.75,
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: {
          display: true,
          grid: {
            display: false
          },
          ticks: {
            maxRotation: 0,
            minRotation: 0,
            autoSkip: false,
            callback: function (value) {
              const label = this.getLabelForValue(Number(value))
              const [hh, mm, ss] = label.split(':')
              if (ss === '00') {
                return `${hh}:${mm}`
              } else {
                return ''
              }
            }
          }
        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(121, 114, 235, 0.1)'
          },
          ticks: {
            callback: function (value) {
              return formatBytes(Number(value)) + '/s'
            }
          }
        }
      }
    }
  })
  memoryLabels.value = initializeTimeLabels()
  memChartInstance = new Chart(memCtx, {
    type: 'line',
    data: {
      labels: Array(maxPoints).fill(''),
      datasets: [
        {
          label: '内核占用',
          data: [...memoryHistory.value],
          borderWidth: 0.75,
          borderColor: 'rgba(85, 206, 86, 1)',
          backgroundColor: 'rgba(85, 206, 86, 0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: {
          display: true,
          grid: {
            display: false
          },
          ticks: {
            maxRotation: 0,
            minRotation: 0,
            autoSkip: false,
            callback: function (value) {
              const label = this.getLabelForValue(Number(value)) // 获取时间字符串，比如 '14:23:30'
              const [hh, mm, ss] = label.split(':') // 拆分时间
              if (ss === '00') {
                return `${hh}:${mm}` // 只显示到分钟
              } else {
                return '' // 其他秒数不显示
              }
            }
          }
        },
        y: {
          grid: {
            color: 'rgba(121, 114, 235, 0.1)'
          },
          beginAtZero: true,
          ticks: {
            callback: function (value) {
              return formatBytes(Number(value))
            }
          }
        }
      }
    }
  })
  if (props.allowRefresh && componentConfig.clash_available) {
    evtSource = new EventSource(
      'api/v1/plugin/ClashRuleProvider/clash/ws/traffic?secret=' + componentConfig.secret
    )
    evtSource.addEventListener('traffic', (event) => {
      const data = JSON.parse(event.data)
      if (!data?.error) {
        uploadSpeed.value = data.up
        downloadSpeed.value = data.down
        uploadHistory.value.push(data.up)
        downloadHistory.value.push(data.down)
        speedLabels.value.push(getCurrentTimeLabel())
        updateChart()
      }
    })

    connectionsEvtSource = new EventSource(
      'api/v1/plugin/ClashRuleProvider/clash/ws/connections?secret=' + componentConfig.secret
    )
    connectionsEvtSource.addEventListener('connections', (event) => {
      const data = JSON.parse(event.data)
      if (!data?.error) {
        uploaded.value = data.uploadTotal
        downloaded.value = data.downloadTotal
        activeConnections.value = data.connections.length
        coreUsage.value = data.memory
        memoryHistory.value.push(data.memory)
        memoryLabels.value.push(getCurrentTimeLabel())
        updateMemoryChart()
      }
    })
  }
})
// 清理
onUnmounted(() => {
  if (connectionsEvtSource) connectionsEvtSource.close()
  if (evtSource) evtSource.close()
  if (chartInstance) chartInstance.destroy()
  if (memChartInstance) memChartInstance.destroy()
})
</script>

<template>
  <v-card class="h-100">
    <v-card-item>
      <v-card-title>{{ config?.attrs?.title || 'Clash Info' }}</v-card-title>
    </v-card-item>
    <v-card-text class="pa-0 h-100 d-flex flex-column">
      <v-container fluid class="fill-height pa-0">
        <v-row dense class="fill-height">
          <!-- 左侧内容 -->
          <v-col cols="12" md="6" class="d-flex flex-column gap-2">
            <v-sheet class="pa-2 rounded elevation-6 d-flex flex-column flex-grow-1">
              <canvas ref="speedChartCanvas" style="max-height: 200px" class="flex-grow-1" />
            </v-sheet>
            <v-row dense justify="space-between">
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">{{ formatBytes(uploadSpeed) }}/s</div>
                  <div>上传速度</div>
                </v-sheet>
              </v-col>
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">
                    {{ formatBytes(downloadSpeed) }}/s
                  </div>
                  <div>下载速度</div>
                </v-sheet>
              </v-col>
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">{{ activeConnections }}</div>
                  <div>活跃连接</div>
                </v-sheet>
              </v-col>
            </v-row>
          </v-col>

          <!-- 右侧内容 -->
          <v-col cols="12" md="6" class="d-flex flex-column gap-2">
            <v-sheet class="pa-2 rounded elevation-6 flex-grow-1">
              <canvas ref="memoryChartCanvas" style="max-height: 200px" class="flex-grow-1" />
            </v-sheet>
            <v-row dense justify="space-between">
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">{{ formatBytes(uploaded) }}</div>
                  <div>上传量</div>
                </v-sheet>
              </v-col>
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">{{ formatBytes(downloaded) }}</div>
                  <div>下载量</div>
                </v-sheet>
              </v-col>
              <v-col cols="4">
                <v-sheet class="pa-3 rounded text-center">
                  <div class="font-weight-bold text-caption">{{ formatBytes(coreUsage) }}</div>
                  <div>内核占用</div>
                </v-sheet>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>
