export async function resolve(specifier, context, nextResolve) {
	const relative = specifier.startsWith('./') || specifier.startsWith('../')
	if (!relative) return nextResolve(specifier, context)

	const candidates = []
	if (specifier.endsWith('.js')) candidates.push(`${specifier.slice(0, -3)}.ts`)
	else if (!/\.[a-z]+$/i.test(specifier)) {
		candidates.push(`${specifier}.ts`, `${specifier}/index.ts`)
	}

	for (const candidate of candidates) {
		try {
			return await nextResolve(candidate, context)
		} catch {
			// Try the next candidate.
		}
	}
	return nextResolve(specifier, context)
}
