import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('retired vibe-reviewer product', () => {
  it('keeps only a home redirect for the retired route', () => {
    const routerSource = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf8')

    expect(routerSource).toContain("path: '/reviewer'")
    expect(routerSource).toContain("redirect: '/'")
    expect(routerSource).not.toContain("import('../views/Reviewer.vue')")
  })

  it('removes the page and navigation entry', () => {
    const navbarSource = readFileSync(
      resolve(process.cwd(), 'src/components/home/AppNavbar.vue'),
      'utf8',
    )

    expect(existsSync(resolve(process.cwd(), 'src/views/Reviewer.vue'))).toBe(false)
    expect(navbarSource).not.toContain('教程评估')
    expect(navbarSource).not.toContain('features?.reviewer')
  })
})
