import { readdirSync, readFileSync } from 'node:fs'
import { dirname, extname, resolve } from 'node:path'

function walkFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name)
    return entry.isDirectory() ? walkFiles(path) : [path]
  })
}

describe('top-level component reachability', () => {
  it('does not introduce unreviewed orphan root components', () => {
    const frontendRoot = process.cwd()
    const sourceRoot = resolve(frontendRoot, 'src')
    const componentRoot = resolve(sourceRoot, 'components')
    const orphanCandidatesAwaitingAudit = new Set(['ProgressPanel.vue'])
    const productionFiles = walkFiles(sourceRoot).filter((path) =>
      ['.ts', '.vue'].includes(extname(path)),
    )
    const rootComponents = readdirSync(componentRoot)
      .filter((filename) => filename.endsWith('.vue'))
      .sort()
    const importedComponents = new Set<string>()

    for (const sourcePath of productionFiles) {
      const source = readFileSync(sourcePath, 'utf8')
      const imports = source.matchAll(/(?:from\s+|import\s*\(\s*)['"]([^'"]+\.vue)['"]/g)

      for (const [, specifier] of imports) {
        if (specifier.startsWith('@/')) {
          importedComponents.add(resolve(sourceRoot, specifier.slice(2)))
        } else if (specifier.startsWith('.')) {
          importedComponents.add(resolve(dirname(sourcePath), specifier))
        }
      }
    }

    const orphanComponents = rootComponents.filter(
      (filename) =>
        !orphanCandidatesAwaitingAudit.has(filename) &&
        !importedComponents.has(resolve(componentRoot, filename)),
    )

    expect(orphanComponents).toEqual([])
  })
})
