/**
 * jspdf mock — 未安装的可选依赖，供 vitest 测试使用
 */
export class jsPDF {
  setFont() {}
  setFontSize() {}
  splitTextToSize(_text: string, _maxWidth: number) { return ['mock line'] }
  text() {}
  addPage() {}
  save() {}
}
