/**
 * html2canvas mock — 未安装的可选依赖，供 vitest 测试使用
 */
export default function html2canvas() {
  return Promise.resolve({
    toBlob(cb: (blob: Blob | null) => void) {
      cb(new Blob(['mock-image'], { type: 'image/png' }))
    },
  })
}
