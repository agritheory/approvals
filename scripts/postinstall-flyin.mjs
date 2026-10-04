import { execSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const approvalsRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const flyinRoot = join(approvalsRoot, 'node_modules/@agritheory/flyin')

const flyinInstallEnv = {
	...process.env,
	// Flyin prepare (vite-plus) must not set core.hooksPath on the host repo.
	VP_GIT_HOOKS: '0',
	VITE_GIT_HOOKS: '0',
	HUSKY: '0',
}

function run(command, cwd, inherit = true) {
	execSync(command, {
		cwd,
		stdio: inherit ? 'inherit' : 'pipe',
		encoding: inherit ? undefined : 'utf8',
		env: flyinInstallEnv,
	})
}

function gitConfigGet(key) {
	try {
		return run(`git config --get ${key}`, approvalsRoot, false).trim()
	} catch {
		return ''
	}
}

function gitConfigUnsetAll(key) {
	try {
		execSync(`git config --unset-all ${key}`, { cwd: approvalsRoot, stdio: 'pipe' })
	} catch {
		// already unset
	}
}

/** Fallback if an older @agritheory/flyin prepare already pointed hooks at vite-plus shims. */
function restoreApprovalsGitHooks() {
	const hooksPath = gitConfigGet('core.hooksPath')
	if (!hooksPath) return

	const isFlyinViteHooks = hooksPath.includes('@agritheory/flyin') && hooksPath.includes('.vite-hooks')
	if (!isFlyinViteHooks) return

	console.warn('[approvals] Removing @agritheory/flyin vite-plus git hooks from this repo (core.hooksPath).')
	console.warn('[approvals] Run `pre-commit install` if `.git/hooks/pre-commit` is missing.')

	gitConfigUnsetAll('core.hooksPath')
	gitConfigUnsetAll('vp.hooks.dir')
	gitConfigUnsetAll('vp.hooks.prefix')
}

if (!existsSync(join(flyinRoot, 'package.json'))) {
	console.log('[approvals] @agritheory/flyin not present; skipping flyin postinstall')
	process.exit(0)
}

restoreApprovalsGitHooks()

console.log('[approvals] Installing @agritheory/flyin dependencies…')
run('yarn install --cwd node_modules/@agritheory/flyin', approvalsRoot)

restoreApprovalsGitHooks()

console.log('[approvals] Flyin is pinned from git; run yarn build to compile desk bundles.')
