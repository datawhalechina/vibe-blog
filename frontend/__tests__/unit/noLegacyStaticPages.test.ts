import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

describe('legacy static frontend pages', () => {
  it('does not keep the retired static frontend tree', () => {
    expect(existsSync(resolve(process.cwd(), 'src/deprecated'))).toBe(false)
  })
})
