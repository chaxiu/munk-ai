import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import openapiTS, { astToString } from 'openapi-typescript'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const schemaPath = path.join(projectRoot, 'openapi', 'local-api.json')
const outputPath = path.join(projectRoot, 'src', 'shared', 'contracts', 'generated', 'local-api.ts')

async function generateTypes(): Promise<string> {
  const ast = await openapiTS(new URL(`file://${schemaPath}`))
  return `${astToString(ast)}\n`
}

async function writeMode(content: string): Promise<number> {
  await mkdir(path.dirname(outputPath), { recursive: true })
  await writeFile(outputPath, content, 'utf-8')
  console.log(`wrote ${outputPath}`)
  return 0
}

async function checkMode(content: string): Promise<number> {
  try {
    const current = await readFile(outputPath, 'utf-8')
    if (current === content) {
      console.log(`types are up to date: ${outputPath}`)
      return 0
    }
    console.error(`outdated generated types: ${outputPath}`)
    return 1
  } catch {
    console.error(`missing generated types: ${outputPath}`)
    return 1
  }
}

async function main(): Promise<number> {
  const mode = process.argv[2]
  if (mode !== 'write' && mode !== 'check') {
    console.error('usage: generate-local-api-types.mts <write|check>')
    return 1
  }

  const content = await generateTypes()
  return mode === 'write' ? writeMode(content) : checkMode(content)
}

process.exitCode = await main()
